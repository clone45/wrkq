"""Functions for searching and retrieving job listings from LinkedIn."""

import time
import json
import random
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup

# Import from other modules
from fetch import fetch_page
from utils import load_cookies_from_file, create_filename
from extract import extract_job_data_from_html

# Configure logging
logger = logging.getLogger(__name__)

def extract_query_params(url):
    """Extract query parameters from a URL."""
    parsed_url = urlparse(url)
    return {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

def build_search_url(base_url, params, start=0, count=25):
    """Build a URL with pagination parameters."""
    # Parse the original URL
    parsed_url = urlparse(base_url)
    
    # Get existing query parameters and update them
    query_params = parse_qs(parsed_url.query)
    
    # Add our parameters
    for key, value in params.items():
        query_params[key] = [value]
    
    # Add pagination parameters
    query_params['start'] = [str(start)]
    query_params['count'] = [str(count)]
    
    # Rebuild the query string
    new_query = urlencode(query_params, doseq=True)
    
    # Reconstruct the URL
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    
    return new_url

def extract_jobs_from_search_html(html_content):
    """
    Extract job listings from LinkedIn search results HTML.
    
    Args:
        html_content: HTML string from LinkedIn search results page
        
    Returns:
        List of job dictionaries
    """
    jobs = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    logger.info("Parsing HTML response for job listings")
    
    # Look for job cards with the base-search-card class
    job_cards = soup.select('.base-search-card')
    logger.info(f"Found {len(job_cards)} job cards with .base-search-card class")
    
    if not job_cards:
        # Try alternative selector
        job_cards = soup.select('.job-search-card')
        logger.info(f"Found {len(job_cards)} job cards with .job-search-card class")
    
    if not job_cards:
        # Final fallback for list items containing job cards
        job_cards = soup.select('li')
        logger.info(f"Found {len(job_cards)} list items as fallback")
    
    for card in job_cards:
        try:
            # Extract entity URN/job ID from data attribute
            job_id = None
            entity_urn = card.get('data-entity-urn')
            if entity_urn:
                logger.info(f"Found entity URN: {entity_urn}")
                job_id_match = re.search(r'jobPosting:(\d+)', entity_urn)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    logger.info(f"Extracted job ID from URN: {job_id}")
            
            # If no job ID from entity URN, try the job link
            if not job_id:
                job_link_elem = card.select_one('a.base-card__full-link')
                if job_link_elem and 'href' in job_link_elem.attrs:
                    job_link = job_link_elem['href']
                    job_id_match = re.search(r'view/(\d+)', job_link)
                    if job_id_match:
                        job_id = job_id_match.group(1)
                        logger.info(f"Extracted job ID from link: {job_id}")
            
            # Extract job title
            title_elem = card.select_one('.base-search-card__title')
            title = title_elem.get_text(strip=True) if title_elem else 'No Title'
            
            # Extract company name
            company_elem = card.select_one('.base-search-card__subtitle')
            company = 'No Company'
            if company_elem:
                # The company name is in a nested link
                company_link = company_elem.select_one('a')
                if company_link:
                    company = company_link.get_text(strip=True)
                else:
                    company = company_elem.get_text(strip=True)
            
            # Extract location
            location_elem = card.select_one('.job-search-card__location')
            location = location_elem.get_text(strip=True) if location_elem else 'No Location'
            
            # Extract posting date
            date_elem = card.select_one('time')
            posted_date = date_elem.get('datetime') if date_elem else 'Unknown'
            posted_text = date_elem.get_text(strip=True) if date_elem else 'Unknown'
            
            # Extract job URL
            job_url = None
            job_link_elem = card.select_one('a.base-card__full-link')
            if job_link_elem and 'href' in job_link_elem.attrs:
                job_url = job_link_elem['href']
            
            # Extract whether it's an easy apply job
            easy_apply = False
            easy_apply_elem = card.select_one('.job-search-card__easy-apply-label')
            if easy_apply_elem:
                easy_apply = True
            
            # Create job entry
            job_entry = {
                'job_id': job_id,
                'title': title,
                'company': company,
                'location': location,
                'posted_date': posted_date,
                'posted_text': posted_text,
                'url': job_url,
                'easy_apply': easy_apply,
                'source': 'LinkedIn Search'
            }
            
            logger.info(f"Extracted job: {title} at {company}")
            jobs.append(job_entry)
            
        except Exception as e:
            logger.error(f"Error extracting job card data: {str(e)}")
            continue
    
    return jobs

def extract_jobs_from_json(data):
    """
    Extract job information from LinkedIn JSON response.
    
    Args:
        data: JSON data from LinkedIn API
        
    Returns:
        List of job dictionaries
    """
    jobs = []
    
    # LinkedIn uses different JSON structures depending on the endpoint
    if isinstance(data, list):
        # Some endpoints return a direct list of jobs
        for job in data:
            try:
                extracted_job = extract_job_from_json_item(job)
                if extracted_job:
                    jobs.append(extracted_job)
            except Exception as e:
                logger.error(f"Error extracting job from list item: {e}")
    
    elif isinstance(data, dict):
        # Check for 'elements' structure (common in newer LinkedIn API responses)
        elements = data.get('elements', [])
        for element in elements:
            try:
                extracted_job = extract_job_from_json_item(element)
                if extracted_job:
                    jobs.append(extracted_job)
            except Exception as e:
                logger.error(f"Error extracting job from element: {e}")
        
        # Check for older format with 'included' elements
        included = data.get('included', [])
        for item in included:
            try:
                if isinstance(item, dict) and item.get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                    extracted_job = extract_job_from_json_item(item)
                    if extracted_job:
                        jobs.append(extracted_job)
            except Exception as e:
                logger.error(f"Error extracting job from included item: {e}")
    
    return jobs

def extract_job_from_json_item(item):
    """
    Extract job data from a single JSON item.
    
    Args:
        item: JSON dictionary from LinkedIn API
        
    Returns:
        Job dictionary or None if extraction fails
    """
    # Different JSON structures appear in LinkedIn responses
    if not isinstance(item, dict):
        return None
    
    job = {'source': 'LinkedIn Search'}
    
    # Identify job by type if available
    item_type = item.get('$type', '')
    is_job_posting = 'JobPosting' in item_type or 'jobPosting' in item_type
    
    # Extract job ID
    if 'entityUrn' in item:
        urn = item['entityUrn']
        job_id_match = re.search(r'jobPosting:(\d+)', urn)
        if job_id_match:
            job['job_id'] = job_id_match.group(1)
    elif 'jobId' in item:
        job['job_id'] = item['jobId']
    elif 'id' in item:
        job['job_id'] = item['id']
    
    # Extract basic job info
    if 'title' in item:
        job['title'] = item['title']
    
    # Company could be in different formats
    if 'companyName' in item:
        job['company'] = item['companyName']
    elif 'company' in item and isinstance(item['company'], dict):
        job['company'] = item['company'].get('name', 'Unknown')
    
    # Extract location
    if 'formattedLocation' in item:
        job['location'] = item['formattedLocation']
    elif 'locationName' in item:
        job['location'] = item['locationName']
    elif 'location' in item:
        if isinstance(item['location'], str):
            job['location'] = item['location']
        elif isinstance(item['location'], dict):
            job['location'] = item['location'].get('name', 'Unknown')
    
    # Extract posting date
    if 'listedAt' in item:
        try:
            # LinkedIn timestamps are usually in milliseconds
            from datetime import datetime
            timestamp_ms = item.get('listedAt')
            if isinstance(timestamp_ms, (int, float)):
                post_date = datetime.fromtimestamp(timestamp_ms / 1000.0)
                job['posted_date'] = post_date.strftime('%Y-%m-%d')
            else:
                job['posted_date'] = str(timestamp_ms)
        except Exception as e:
            logger.error(f"Error parsing job post date: {e}")
            job['posted_date'] = 'Unknown'
    
    # Extract job URL
    if 'jobPostingUrl' in item:
        job['url'] = item['jobPostingUrl']
    elif 'viewJobLink' in item:
        job['url'] = item['viewJobLink']
    elif 'navigationUrl' in item:
        job['url'] = item['navigationUrl']
    
    # Make sure we have the minimum required fields
    if not job.get('job_id') or not job.get('title'):
        logger.warning("Skipping job entry with missing critical fields")
        return None
    
    # If no URL but we have a job ID, construct a reasonable LinkedIn job URL
    if not job.get('url') and job.get('job_id'):
        job['url'] = f"https://www.linkedin.com/jobs/view/{job['job_id']}/"
    
    return job

def search_jobs(search_url, cookie_file=None, output_dir=None, max_pages=5, 
                jobs_per_page=25, delay_between_requests=3, verbose=True):
    """
    Search for jobs on LinkedIn using pagination.
    
    Args:
        search_url: LinkedIn job search URL
        cookie_file: Path to cookie file with LinkedIn authentication
        output_dir: Directory to save fetched HTML and JSON (optional)
        max_pages: Maximum number of pages to retrieve
        jobs_per_page: Number of jobs per page (default 25)
        delay_between_requests: Delay between API requests in seconds
        verbose: Whether to print detailed logs
        
    Returns:
        List of job dictionaries with extracted information
    """
    # Parse the search URL
    parsed_url = urlparse(search_url)
    logger.info(f"Parsing search URL: {search_url}")
    
    # Determine which API endpoint to use
    if "/jobs/search" in parsed_url.path:
        # Regular job search URL
        api_endpoint = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        logger.info(f"Using LinkedIn jobs API endpoint: {api_endpoint}")
    else:
        logger.error(f"Unsupported LinkedIn URL path: {parsed_url.path}")
        return []
    
    # Extract important search parameters
    query_params = extract_query_params(search_url)
    logger.info(f"Extracted query parameters: {query_params}")
    
    # Core search parameters that should be preserved
    important_params = [
        'keywords', 'location', 'geoId', 'currentJobId', 
        'f_TPR', 'f_WT', 'f_E', 'distance', 'sortBy'
    ]
    
    # Keep only the important parameters
    api_params = {k: v for k, v in query_params.items() if k in important_params}
    logger.info(f"Using API parameters: {api_params}")
    
    # Make sure we're using guest mode for the API
    api_params['guest'] = 'true'
    
    all_jobs = []
    
    for page in range(max_pages):
        start_index = page * jobs_per_page
        
        # Build the paginated API URL
        paginated_url = build_search_url(
            api_endpoint, 
            api_params, 
            start=start_index, 
            count=jobs_per_page
        )
        
        logger.info(f"Page {page+1}/{max_pages}, jobs {start_index+1}-{start_index+jobs_per_page}")
        logger.info(f"Constructed URL: {paginated_url}")
        
        # Fetch the page using existing fetch_page function
        response = fetch_page(
            url=paginated_url,
            cookie_file=cookie_file,
            max_retries=3,
            retry_delay=5,
            verbose=verbose
        )
        
        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch page {page+1}, status code: {response.status_code if response else 'No response'}")
            break
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response length: {len(response.text)} characters")
        
        # Save the response if output directory provided
        html_path = None
        if output_dir:
            html_path = create_filename(paginated_url, output_dir)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"Saved HTML to {html_path}")
        
        # Process the response - Try JSON first, then fall back to HTML
        try:
            # Try to parse as JSON
            json_data = json.loads(response.text)
            logger.info("Successfully parsed response as JSON")
            
            # Check JSON structure
            if isinstance(json_data, dict):
                logger.info(f"JSON root keys: {list(json_data.keys())}")
            elif isinstance(json_data, list):
                logger.info(f"JSON is a list with {len(json_data)} items")
            
            page_jobs = extract_jobs_from_json(json_data)
            logger.info(f"Extracted {len(page_jobs)} jobs from JSON response")
        except json.JSONDecodeError as e:
            logger.info(f"Response is not JSON, falling back to HTML parsing")
            # Log the first 500 characters of HTML for debugging
            logger.info(f"HTML preview: {response.text[:500]}...")
            
            # Parse HTML response
            page_jobs = extract_jobs_from_search_html(response.text)
            logger.info(f"Extracted {len(page_jobs)} jobs from HTML response")
            
            # Add more detailed logging of HTML structure
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Log available job card selectors
            job_cards_1 = soup.select('li.jobs-search-results__list-item')
            job_cards_2 = soup.select('.job-search-card')
            job_cards_3 = soup.select('.base-search-card')
            job_cards_4 = soup.select('.base-card')
            
            logger.info(f"Job cards by selector 'li.jobs-search-results__list-item': {len(job_cards_1)}")
            logger.info(f"Job cards by selector '.job-search-card': {len(job_cards_2)}")
            logger.info(f"Job cards by selector '.base-search-card': {len(job_cards_3)}")
            logger.info(f"Job cards by selector '.base-card': {len(job_cards_4)}")
            
            # If no jobs found, let's log more potential selectors
            if len(page_jobs) == 0:
                logger.info("No jobs found, checking alternative HTML structures")
                
                # Check for list items
                li_elements = soup.select('li')
                logger.info(f"Found {len(li_elements)} li elements")
                
                # Look for job-related classes
                job_related_elements = soup.select('[class*="job"]')
                logger.info(f"Found {len(job_related_elements)} elements with 'job' in class name")
                
                # Try to find any div that might contain job info
                job_title_elements = soup.select('[class*="title"]')
                logger.info(f"Found {len(job_title_elements)} elements with 'title' in class name")
                
                # Log first few list items for inspection
                if li_elements:
                    for i, li in enumerate(li_elements[:3]):
                        logger.info(f"List item {i+1} classes: {li.get('class', [])}")
                        logger.info(f"List item {i+1} first 100 chars: {str(li)[:100]}...")
                
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            page_jobs = []
        
        all_jobs.extend(page_jobs)
        logger.info(f"Total jobs found so far: {len(all_jobs)}")
        
        # Add delay between requests to avoid rate limiting
        if page < max_pages - 1:
            delay = delay_between_requests * random.uniform(4.8, 5.2)  # Add jitter
            logger.info(f"Waiting {delay:.2f} seconds before next request")
            time.sleep(delay)
    
    return all_jobs

def fetch_job_details(jobs, cookie_file=None, output_dir=None, max_jobs=None, 
                     delay_between_requests=3, verbose=True):
    """
    Fetch detailed information for a list of jobs.
    
    Args:
        jobs: List of job dictionaries with 'url' or 'job_id' fields
        cookie_file: Path to cookie file with LinkedIn authentication
        output_dir: Directory to save fetched HTML and JSON
        max_jobs: Maximum number of jobs to fetch details for (None for all)
        delay_between_requests: Delay between requests in seconds
        verbose: Whether to print detailed logs
        
    Returns:
        List of job dictionaries with detailed information
    """
    detailed_jobs = []
    job_count = len(jobs)
    max_to_fetch = job_count if max_jobs is None else min(max_jobs, job_count)
    
    logger.info(f"Fetching detailed information for {max_to_fetch} out of {job_count} jobs")
    
    for i, job in enumerate(jobs[:max_to_fetch]):
        if verbose:
            logger.info(f"Processing job {i+1}/{max_to_fetch}: {job.get('title', 'Unknown')}")
        
        # Get the job URL
        job_url = job.get('url')
        if not job_url and 'job_id' in job:
            job_url = f"https://www.linkedin.com/jobs/view/{job['job_id']}/"
        
        if not job_url:
            logger.warning(f"Skipping job {i+1}: No URL available")
            continue
        
        # Fetch the job details page
        response = fetch_page(
            url=job_url,
            cookie_file=cookie_file,
            max_retries=3,
            retry_delay=5,
            verbose=verbose
        )
        
        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch job {i+1} details from {job_url}")
            continue
        
        # Save the HTML if output directory provided
        html_path = None
        if output_dir:
            html_path = create_filename(job_url, output_dir)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            if verbose:
                logger.info(f"Saved job HTML to {html_path}")
        
        # Extract job data using existing function
        job_data = extract_job_data_from_html(response.text)
        
        if job_data:
            # Merge the search result data with the detailed data
            # but prefer detailed data where available
            detailed_job = {**job, **job_data}
            
            # Save the JSON if output directory provided
            if output_dir and html_path:
                json_path = html_path.replace('.html', '.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(detailed_job, f, indent=2)
                if verbose:
                    logger.info(f"Saved job JSON to {json_path}")
            
            detailed_jobs.append(detailed_job)
        else:
            logger.warning(f"Failed to extract data for job {i+1}")
            # Keep the original job data from search
            detailed_jobs.append(job)
        
        # Add delay between requests
        if i < max_to_fetch - 1:
            delay = delay_between_requests * random.uniform(5.8, 6.2)  # Add jitter
            if verbose:
                logger.info(f"Waiting {delay:.2f} seconds before next request")
            time.sleep(delay)
    
    return detailed_jobs

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Example usage
    from config import COOKIE_FILE, OUTPUT_DIR
    import argparse
    
    parser = argparse.ArgumentParser(description='LinkedIn Job Search Tool')
    parser.add_argument('--url', required=True, help='LinkedIn job search URL')
    parser.add_argument('--pages', type=int, default=3, help='Maximum number of pages to fetch')
    parser.add_argument('--fetch-details', action='store_true', help='Fetch detailed job information')
    parser.add_argument('--max-details', type=int, default=10, help='Maximum number of job details to fetch')
    parser.add_argument('--output', default=OUTPUT_DIR, help='Output directory for HTML and JSON files')
    parser.add_argument('--output-json', help='Output JSON file for search results')
    args = parser.parse_args()
    
    # Search for jobs
    jobs = search_jobs(
        search_url=args.url,
        cookie_file=COOKIE_FILE,
        output_dir=args.output,
        max_pages=args.pages,
        verbose=True
    )
    
    print(f"\nFound {len(jobs)} jobs in search results")
    
    # Fetch detailed information for a subset of jobs if requested
    if args.fetch_details and jobs:
        print(f"\nFetching detailed information for up to {args.max_details} jobs...")
        detailed_jobs = fetch_job_details(
            jobs=jobs,
            cookie_file=COOKIE_FILE,
            output_dir=args.output,
            max_jobs=args.max_details,
            verbose=True
        )
        
        print(f"\nFetched detailed information for {len(detailed_jobs)} jobs")
        # Use the detailed jobs for the output
        jobs = detailed_jobs
    
    # Output results to JSON file if requested
    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2)
        print(f"\nSaved all jobs to {args.output_json}")
    
    # Print the first few jobs
    print("\n--- First 3 Jobs ---")
    for i, job in enumerate(jobs[:3]):
        print(f"\nJob {i+1}: {job.get('title', 'No Title')}")
        print(f"Company: {job.get('company', 'Unknown')}")
        print(f"Location: {job.get('location', 'Unknown')}")
        print(f"URL: {job.get('url', 'No URL')}")