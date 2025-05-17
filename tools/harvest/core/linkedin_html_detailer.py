# File: harvest/core/linkedin_html_detailer.py

import logging
import time
import random
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from curl_cffi import requests

from ..interfaces.detailer import DetailerInterface
from ..errors import NetworkError, ParseError, AuthenticationError
from ..events import EventType
from ..utils.http_utils import load_cookies_from_json_file as load_cookies_from_file

logger = logging.getLogger(__name__)

class LinkedInHTMLDetailer(DetailerInterface):
    """Component for fetching detailed job information via HTML scraping."""
    
    def __init__(self, event_bus):
        """Initialize the detailer with event bus."""
        self.event_bus = event_bus
        logger.info("LinkedInHTMLDetailer initialized")
    
    def _build_headers(self):
        """Build request headers that mimic a browser."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none"
        }
    
    def fetch_details_batch(self, jobs: List[Dict[str, Any]], options: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Fetch details for a batch of jobs using HTML scraping approach.
        """
        if not jobs:
            logger.info("No jobs provided to fetch_details_batch")
            return []
        
        # Extract options - handle dataclass instead of dict
        if options is None:
            from ..interfaces.detailer import DetailOptions
            options = DetailOptions()
                
        cookie_file = getattr(options, 'cookie_file', None)
        delay_between_requests = getattr(options, 'delay_between_requests', 3)
        
        # Track detailed jobs
        detailed_jobs = []
        cookies = None
        
        # Only load cookies once for the batch
        if cookie_file:
            try:
                # Replace load_cookies_from_file with the correct function
                # Import the function from utils.http_utils
                from ..utils.http_utils import load_cookies_from_json_file
                
                # Convert string to Path object if it's a string
                if isinstance(cookie_file, str):
                    cookie_file_path = Path(cookie_file)
                else:
                    cookie_file_path = cookie_file
                    
                cookies = load_cookies_from_json_file(cookie_file_path)
                logger.info(f"Loaded cookies from {cookie_file}")
            except Exception as e:
                logger.error(f"Failed to load cookies from {cookie_file}: {e}")
                raise AuthenticationError(f"Cookie loading failed: {e}")
            
        # Process each job
        for i, job in enumerate(jobs):
            job_id = job.get('job_id')
            if not job_id:
                logger.warning(f"Job at index {i} has no job_id, trying to extract from URL")
                
                # Try to extract job ID from URL if available
                job_url = job.get('url', '')
                if '/jobs/view/' in job_url:
                    try:
                        job_id = job_url.split('/jobs/view/')[1].split('/')[0]
                        logger.info(f"Extracted job_id {job_id} from URL {job_url}")
                    except (IndexError, ValueError):
                        logger.warning(f"Could not extract job_id from URL {job_url}")
            
            if not job_id:
                logger.warning(f"Skipping job at index {i} - no job_id available")
                # Keep original job data without details
                detailed_jobs.append(job)
                continue
                
            # Publish event for pipeline tracking
            self.event_bus.publish(EventType.JOB_DETAIL_FETCH_STARTED, job_id=job_id)
            
            try:
                # Add delay between requests
                if i > 0:
                    delay = delay_between_requests * random.uniform(0.8, 1.2)  # Add jitter
                    logger.info(f"Waiting {delay:.2f}s before fetching job {job_id}")
                    time.sleep(delay)
                
                # Fetch and extract job details
                detailed_job = self._fetch_job_details(job_id, cookies, job)
                
                if detailed_job:
                    # Successfully fetched details
                    detailed_jobs.append(detailed_job)
                    self.event_bus.publish(EventType.JOB_DETAIL_FETCH_COMPLETE, job_id=job_id)
                else:
                    # Failed to get details, keep original job data
                    logger.warning(f"No details fetched for job {job_id}, keeping original data")
                    detailed_jobs.append(job)
                    self.event_bus.publish(EventType.JOB_DETAIL_FETCH_ERROR, job_id=job_id, error="Failed to extract details")
                    
            except NetworkError as ne:
                logger.error(f"Network error fetching details for job {job_id}: {ne}")
                self.event_bus.publish(EventType.JOB_DETAIL_FETCH_ERROR, job_id=job_id, error=f"Network error: {ne}")
                # Keep original job data
                detailed_jobs.append(job)
                
            except ParseError as pe:
                logger.error(f"Parse error fetching details for job {job_id}: {pe}")
                self.event_bus.publish(EventType.JOB_DETAIL_FETCH_ERROR, job_id=job_id, error=f"Parse error: {pe}")
                # Keep original job data
                detailed_jobs.append(job)
                
            except Exception as e:
                logger.error(f"Unexpected error fetching details for job {job_id}: {e}")
                self.event_bus.publish(EventType.JOB_DETAIL_FETCH_ERROR, job_id=job_id, error=f"Unexpected error: {e}")
                # Keep original job data
                detailed_jobs.append(job)
        
        logger.info(f"Completed fetching details for {len(jobs)} jobs, {len([j for j in detailed_jobs if 'description' in j])} with descriptions")
        return detailed_jobs
    
    def _fetch_job_details(self, job_id: str, cookies: Dict[str, str], original_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and extract details for a single job.
        
        Args:
            job_id: LinkedIn job ID
            cookies: Loaded cookies for authentication
            original_job: Original job data from search
            
        Returns:
            Job dictionary with detailed information
        """
        url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        headers = self._build_headers()
        
        logger.info(f"Fetching job details for ID: {job_id}")
        
        try:
            # Make the HTTP request
            response = requests.get(
                url,
                headers=headers,
                cookies=cookies if cookies else {},
                impersonate="chrome110",  # Browser fingerprinting protection
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                raise NetworkError(f"HTTP error {response.status_code} fetching job {job_id}")
            
            # Parse the HTML content
            job_data = self._extract_job_data_from_html(response.text, job_id)
            
            if not job_data:
                raise ParseError(f"Failed to extract data from HTML for job {job_id}")
            
            # Merge original job data with detailed data (prefer original data for location)
            location = original_job.get('location')  # Save original location
            detailed_job = {**original_job, **job_data}  # Merge data
            if location:  # Restore original location
                detailed_job['location'] = location
            return detailed_job
            
        except requests.RequestsError as re:
            raise NetworkError(f"Request failed: {re}")
            
        except Exception as e:
            logger.error(f"Error in _fetch_job_details for job {job_id}: {e}")
            raise  # Re-raise to be handled by the calling method
    
    def _extract_job_data_from_html(self, html_content: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract job data from LinkedIn job page HTML.
        
        Args:
            html_content: HTML content of the job page
            job_id: LinkedIn job ID
            
        Returns:
            Dictionary with job details or None if extraction fails
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # --- Strategy 1: Find JSON in <code> tags ---
            # LinkedIn often uses code tags with JSON data
            data_tag_ids = soup.find_all('code', id=lambda x: x and x.startswith(('bpr-guid-', 'datalet-bpr-guid-')))
            
            logger.info(f"Found {len(data_tag_ids)} potential data containers in HTML for job {job_id}")
            
            job_posting_data = None
            full_json_data = None
            
            for tag in data_tag_ids:
                try:
                    if not tag.string or not tag.string.strip():
                        continue
                        
                    potential_full_json = json.loads(tag.string)
                    
                    # Check if 'data' contains job posting info
                    if isinstance(potential_full_json.get('data'), dict) and \
                       potential_full_json['data'].get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                         job_posting_data = potential_full_json['data']
                         full_json_data = potential_full_json
                         logger.info(f"Found job data in tag {tag.get('id')}")
                         break
                    
                    # Check for job data in elements array
                    if isinstance(potential_full_json.get('elements'), list):
                        for element in potential_full_json['elements']:
                             if isinstance(element.get('data'), dict) and \
                                element['data'].get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                                   job_posting_data = element['data']
                                   full_json_data = potential_full_json
                                   logger.info(f"Found job data in elements list")
                                   break
                             elif isinstance(element, dict) and \
                                  element.get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                                    job_posting_data = element
                                    full_json_data = potential_full_json
                                    logger.info(f"Found job data as element")
                                    break
                    
                    if job_posting_data:
                         break
                
                except json.JSONDecodeError:
                    logger.debug(f"Tag {tag.get('id')} is not valid JSON")
                    continue
                except Exception as e:
                    logger.error(f"Error processing tag {tag.get('id')}: {e}")
                    continue
            
            # If JSON approach failed, try direct HTML parsing
            if not job_posting_data:
                logger.info(f"JSON extraction failed for job {job_id}, falling back to HTML parsing")
                return self._fallback_to_html_extraction(soup, job_id)
            
            # --- Extract data from found JSON ---
            extracted_data = {}
            
            extracted_data['job_id'] = job_id
            extracted_data['title'] = job_posting_data.get('title', 'No Title')
            
            # Handle description (might be nested)
            description_obj = job_posting_data.get('description')
            if isinstance(description_obj, dict):
                extracted_data['description_html'] = description_obj.get('text', '')
                # Clean the description HTML if it contains markup
                if extracted_data['description_html']:
                    desc_soup = BeautifulSoup(extracted_data['description_html'], 'html.parser')
                    extracted_data['description'] = desc_soup.get_text(separator='\n', strip=True)
            else:
                extracted_data['description_html'] = str(description_obj) if description_obj else ''
                extracted_data['description'] = extracted_data['description_html']
            
            # --- Company Name Extraction ---
            extracted_data['company'] = "Company Name Not Found"
            company_details = job_posting_data.get('companyDetails', {})
            company_urn = None
            
            if isinstance(company_details, dict):
                company_urn = company_details.get('company') or company_details.get('*companyResolutionResult')
                
            if company_urn and isinstance(full_json_data.get('included'), list):
                for included_item in full_json_data['included']:
                    if isinstance(included_item, dict) and included_item.get('entityUrn') == company_urn:
                        extracted_data['company'] = included_item.get('name', "Company Name Not Found")
                        break
            
            # Employment type
            employment_type = job_posting_data.get('employmentStatus', {})
            if isinstance(employment_type, dict):
                extracted_data['employment_type'] = employment_type.get('text', 'Not specified')
            
            # Application stats
            extracted_data['applies'] = job_posting_data.get('applies', 0)
            extracted_data['views'] = job_posting_data.get('views', 0)
            
            # Add URL for reference
            extracted_data['url'] = f"https://www.linkedin.com/jobs/view/{job_id}/"
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting job data from HTML for job {job_id}: {e}")
            raise ParseError(f"HTML parsing error: {e}")
    
    def _fallback_to_html_extraction(self, soup: BeautifulSoup, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract job data directly from HTML structure as fallback.
        
        Args:
            soup: BeautifulSoup object from the job page
            job_id: LinkedIn job ID
            
        Returns:
            Dictionary with job details or None if extraction fails
        """
        logger.info(f"Falling back to direct HTML content extraction for job {job_id}")
        
        try:
            job_info = {'job_id': job_id}
            
            # Try to find title (several possible selectors)
            title_tag = soup.find('h1', class_='job-title') or \
                        soup.find('h1', class_='top-card-layout__title') or \
                        soup.find('h1', class_='topcard__title')
            
            if title_tag:
                job_info['title'] = title_tag.text.strip()
            else:
                job_info['title'] = "Title Not Found"
            
            # Find company
            company_tag = soup.find('a', class_='topcard__org-name-link') or \
                          soup.find('span', class_='topcard__flavor') or \
                          soup.find('span', class_='company-name')
            
            if company_tag:
                job_info['company'] = company_tag.text.strip()
            else:
                job_info['company'] = "Company Not Found"
            
            # Find job description
            description_div = soup.find('div', class_='description__text') or \
                              soup.find('div', class_='show-more-less-html__markup') or \
                              soup.find('div', class_='jobs-description__content')
            
            if description_div:
                job_info['description_html'] = str(description_div)
                job_info['description'] = description_div.get_text(separator='\n', strip=True)
            else:
                job_info['description'] = "Description Not Found"
                job_info['description_html'] = ""
            
            # URL (for reference)
            job_info['url'] = f"https://www.linkedin.com/jobs/view/{job_id}/"
            
            return job_info
            
        except Exception as e:
            logger.error(f"Error during HTML fallback extraction for job {job_id}: {e}")
            raise ParseError(f"HTML fallback extraction error: {e}")