# File: harvest/utils/html_parser.py

import json
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from ..errors import ParseError # Import your custom ParseError

logger = logging.getLogger(__name__)

# --- Job Detail Page Parsing (Adapted from your old extract.py) ---

def _parse_job_details_from_embedded_json(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to extract detailed job data by finding and parsing JSON 
    embedded in <code> tags within a job detail page.
    Includes resolving company name from 'included' array.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data_tag_ids = re.compile(r'^(bpr-guid-|datalet-bpr-guid-).*')
    code_tags = soup.find_all('code', id=data_tag_ids)

    logger.debug(f"Found {len(code_tags)} potential JSON data containers in job detail HTML.")
    
    job_posting_data = None
    full_json_data = None

    for tag in code_tags:
        if not tag.string or not tag.string.strip():
            continue
        try:
            potential_full_json = json.loads(tag.string)
            # Logic to find the 'com.linkedin.voyager.jobs.JobPosting' data
            # (This part is copied directly from your old extract.py and seems robust)
            if isinstance(potential_full_json.get('data'), dict) and \
               potential_full_json['data'].get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                 job_posting_data = potential_full_json['data']
                 full_json_data = potential_full_json
                 break
            if isinstance(potential_full_json.get('elements'), list):
                for element in potential_full_json['elements']:
                     if isinstance(element.get('data'), dict) and \
                        element['data'].get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                           job_posting_data = element['data']
                           full_json_data = potential_full_json
                           break
                     elif isinstance(element, dict) and \
                          element.get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                            job_posting_data = element
                            full_json_data = potential_full_json
                            break
            if job_posting_data:
                 break
        except json.JSONDecodeError:
            logger.debug(f"Tag {tag.get('id')} in job detail page is not valid JSON.")
            continue
        except Exception as e:
            logger.warning(f"Error processing tag {tag.get('id')} in job detail page: {e}") # Changed to warning
            continue

    if not job_posting_data or not full_json_data:
        return None # Signal that structured JSON was not found

    # --- Extract specific fields from the found JSON ---
    extracted_details = {}
    extracted_details['title'] = job_posting_data.get('title')
    
    description_obj = job_posting_data.get('description')
    if isinstance(description_obj, dict):
        extracted_details['description_raw'] = description_obj.get('text', '')
        if extracted_details['description_raw']:
            desc_soup = BeautifulSoup(extracted_details['description_raw'], 'html.parser')
            extracted_details['description'] = desc_soup.get_text(separator='\n', strip=True) # Use 'description' as final key
    else:
        extracted_details['description_raw'] = str(description_obj) if description_obj else ''
        extracted_details['description'] = extracted_details['description_raw']
    
    extracted_details['location'] = job_posting_data.get('formattedLocation')
    
    # Company Name Extraction
    company_name = "Unknown Company" # Default
    company_details_obj = job_posting_data.get('companyDetails', {})
    company_urn = None
    if isinstance(company_details_obj, dict):
        company_urn = company_details_obj.get('company') or company_details_obj.get('*companyResolutionResult')
        
    if company_urn and isinstance(full_json_data.get('included'), list):
        for included_item in full_json_data['included']:
            if isinstance(included_item, dict) and included_item.get('entityUrn') == company_urn:
                company_name = included_item.get('name', company_name)
                # extracted_details['company_universal_name'] = included_item.get('universalName')
                # logo_data = included_item.get('logo', {})
                # if isinstance(logo_data, dict) and isinstance(logo_data.get('image'), dict):
                #     extracted_details['company_logo_url'] = logo_data['image'].get('rootUrl')
                break
    extracted_details['company'] = company_name # Use 'company' as final key

    if 'listedAt' in job_posting_data:
        try:
            timestamp_ms = job_posting_data.get('listedAt')
            if isinstance(timestamp_ms, (int, float)):
                post_date = datetime.fromtimestamp(timestamp_ms / 1000.0)
                extracted_details['posted_date_str'] = post_date.strftime('%Y-%m-%d') # Keep as string
        except Exception as e:
            logger.debug(f"Error parsing job post date from details: {e}")
            extracted_details['posted_date_str'] = str(job_posting_data.get('listedAt'))

    employment_type_obj = job_posting_data.get('employmentStatus', {})
    if isinstance(employment_type_obj, dict):
        extracted_details['employment_type'] = employment_type_obj.get('text')
    
    # Salary (simplified - your old code had more complex parsing)
    compensation = job_posting_data.get('compensation', {})
    if isinstance(compensation, dict) and 'compensationRange' in compensation:
        ranges = compensation.get('compensationRange', {})
        if isinstance(ranges, dict) and 'min' in ranges and 'max' in ranges:
            min_val = ranges.get('min', {}).get('value')
            max_val = ranges.get('max', {}).get('value')
            currency = ranges.get('min', {}).get('currencyCode', 'USD')
            if min_val and max_val:
                 extracted_details['salary_range'] = f"{currency} {min_val}-{max_val}"

    if 'entityUrn' in job_posting_data:
        urn = job_posting_data['entityUrn']
        job_id_match = re.search(r'jobPosting:(\d+)', urn)
        if job_id_match:
            extracted_details['job_id'] = job_id_match.group(1)
    
    # Add other fields if present and needed
    # extracted_details['applies'] = job_posting_data.get('applies')
    # extracted_details['views'] = job_posting_data.get('views')

    return {k: v for k, v in extracted_details.items() if v is not None} # Clean out None values


def _fallback_parse_job_details_from_html(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Extracts basic text content from a job detail page HTML as a fallback.
    """
    logger.info("Falling back to basic HTML content extraction for job details.")
    soup = BeautifulSoup(html_content, 'html.parser')
    job_info: Dict[str, Any] = {}

    # Simplified selectors from your old fallback
    title_tag = soup.find('h1', class_=re.compile(r'(job-title|top-card-layout__title)'))
    if title_tag: job_info['title'] = title_tag.text.strip()

    company_tag = soup.find(['a', 'span'], class_=re.compile(r'(topcard__org-name-link|jobs-company__name|topcard__flavor)'))
    if company_tag: job_info['company'] = company_tag.text.strip()
    
    location_tag = soup.find('span', class_=re.compile(r'(topcard__flavor--bullet|jobs-unified-top-card__bullet)'))
    if location_tag: job_info['location'] = location_tag.text.strip()

    desc_selectors = ['div.jobs-description__content', 'section.jobs-description', '#job-details', '.job-description', 'article', 'main']
    description_tag = None
    for selector in desc_selectors:
        description_tag = soup.select_one(selector)
        if description_tag: break
    if description_tag:
        job_info['description'] = description_tag.get_text(separator='\n', strip=True)
    
    if not job_info.get('title') and not job_info.get('description'): # If nothing useful found
        return None
        
    return {k: v for k, v in job_info.items() if v is not None and v != ''}


def parse_job_detail_page(html_content: str) -> Optional[Dict[str, Any]]:
    """
    High-level function to parse a job detail page.
    Tries structured JSON extraction first, then falls back to basic HTML parsing.
    """
    if not html_content:
        return None
    try:
        details = _parse_job_details_from_embedded_json(html_content)
        if details:
            logger.info(f"Successfully extracted job details via embedded JSON for job ID: {details.get('job_id', 'N/A')}")
            return details
        
        logger.info("Embedded JSON for job details not found or incomplete, trying fallback HTML parsing.")
        details = _fallback_parse_job_details_from_html(html_content)
        if details:
            logger.info(f"Successfully extracted job details via fallback HTML parsing for title: {details.get('title', 'N/A')}")
            return details
            
        logger.warning("Could not extract significant job details from the page.")
        return None
    except Exception as e:
        logger.error(f"Exception during job detail page parsing: {e}", exc_info=True)
        raise ParseError(f"Failed to parse job detail page: {e}") from e


# --- Search Results Page Parsing (Adapted from your old tools/fetch/search.py) ---

def _extract_job_card_from_search_html_node(card_node: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Helper to extract data from a single job card HTML node from search results."""
    try:
        job_data: Dict[str, Any] = {}
        
        entity_urn = card_node.get('data-entity-urn')
        if entity_urn:
            job_id_match = re.search(r'jobPosting:(\d+)', entity_urn)
            if job_id_match: job_data['job_id'] = job_id_match.group(1)

        title_elem = card_node.select_one('.base-search-card__title, .job-card-list__title') # Added another common title selector
        if title_elem: job_data['title'] = title_elem.get_text(strip=True)

        company_elem = card_node.select_one('.base-search-card__subtitle a, .job-card-container__company-name') # Added another
        if company_elem: 
            job_data['company'] = company_elem.get_text(strip=True)
        else: # Fallback for company if not in a link
            company_elem_span = card_node.select_one('.base-search-card__subtitle span, span.job-card-container__primary-description')
            if company_elem_span: job_data['company'] = company_elem_span.get_text(strip=True)


        location_elem = card_node.select_one('.job-search-card__location, .job-card-container__metadata-item') # Added another
        if location_elem: job_data['location'] = location_elem.get_text(strip=True)

        date_elem = card_node.select_one('time.job-search-card__listdate, time.job-card-list__listed-date') # Added another
        if date_elem:
            job_data['posted_date_str'] = date_elem.get('datetime', date_elem.get_text(strip=True))

        url_elem = card_node.select_one('a.base-card__full-link, a.job-card-list__title') # Added another
        if url_elem and url_elem.get('href'):
            job_data['url'] = url_elem['href']
            # Try to extract job_id from URL if not found from entity_urn
            if not job_data.get('job_id'):
                job_id_match = re.search(r'(?:view/|currentJobId=)(\d+)', job_data['url'])
                if job_id_match: job_data['job_id'] = job_id_match.group(1)
        
        # If we don't have at least a title or a URL, it's probably not a valid job card
        if not job_data.get('title') and not job_data.get('url'):
            return None
            
        job_data['source_page'] = "LinkedIn Search HTML"
        return {k: v for k, v in job_data.items() if v is not None and v != ''} # Clean Nones/empty
        
    except Exception as e:
        logger.debug(f"Error extracting individual job card from search HTML: {e}")
        return None


def parse_search_results_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Extracts job listings from LinkedIn search results HTML.
    """
    if not html_content:
        return []
        
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        logger.debug("Parsing HTML search results for job listings.")

        # Common selectors for job cards/list items
        card_selectors = [
            '.jobs-search__results-list li', # Newer UI often uses this
            'li.jobs-search-results__list-item', 
            '.base-search-card--job',            # More specific card
            '.job-search-card',
            '.base-search-card',                 # Generic card
            'li[data-entity-urn^="urn:li:fs_normalized_jobPosting"]' # URN based
        ]
        
        job_card_nodes = []
        for selector in card_selectors:
            job_card_nodes = soup.select(selector)
            if job_card_nodes:
                logger.info(f"Found {len(job_card_nodes)} potential job cards using selector: '{selector}'")
                break
        
        if not job_card_nodes:
            logger.warning("No job card elements found using primary selectors. Might be an empty page or page structure changed.")
            # Could try a very broad 'li' as a last resort, but it's risky
            # job_card_nodes = soup.select('li') 
            # if job_card_nodes: logger.info(f"Found {len(job_card_nodes)} <li> elements as final fallback.")

        for card_node in job_card_nodes:
            job_data = _extract_job_card_from_search_html_node(card_node)
            if job_data:
                jobs.append(job_data)
        
        logger.info(f"Extracted {len(jobs)} job entries from HTML search results.")
    except Exception as e:
        logger.error(f"Error during HTML search results parsing: {e}", exc_info=True)
        raise ParseError(f"Failed to parse HTML search results: {e}") from e
    return jobs


def _extract_job_from_search_api_json_item(item_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Helper to extract data from a single job item from search API JSON response."""
    if not isinstance(item_json, dict):
        return None
    
    job_data: Dict[str, Any] = {'source_page': "LinkedIn Search API JSON"}

    # Extract job ID (entityUrn is preferred)
    entity_urn = item_json.get('entityUrn')
    if entity_urn:
        job_id_match = re.search(r'jobPosting:(\d+)', entity_urn)
        if job_id_match: job_data['job_id'] = job_id_match.group(1)
    if not job_data.get('job_id'): # Fallback to other ID fields
        job_data['job_id'] = item_json.get('id') or item_json.get('jobPostingId') or item_json.get('jobId')


    job_data['title'] = item_json.get('title')
    
    # Company info can be nested
    company_info = item_json.get('primaryDescription', {}).get('text') \
                   or item_json.get('companyName')
    if isinstance(item_json.get('company'), dict): # More direct structure
        company_info = item_json['company'].get('name', company_info)
    job_data['company'] = company_info

    job_data['location'] = item_json.get('primarySubtitle', {}).get('text') \
                           or item_json.get('formattedLocation') \
                           or item_json.get('locationName')
    
    # Job URL
    nav_url = item_json.get('navigationUrl') or item_json.get('jobPostingUrl')
    if nav_url:
        job_data['url'] = nav_url
        # Try to extract job_id from URL if not found yet
        if not job_data.get('job_id'):
            job_id_match = re.search(r'(?:view/|currentJobId=)(\d+)', nav_url)
            if job_id_match: job_data['job_id'] = job_id_match.group(1)
            
    # If no URL but we have an ID, construct one
    if not job_data.get('url') and job_data.get('job_id'):
        job_data['url'] = f"https://www.linkedin.com/jobs/view/{job_data['job_id']}/"

    # Posting date (listedAt is often a timestamp in ms)
    listed_at = item_json.get('listedAt')
    if listed_at:
        try:
            if isinstance(listed_at, (int, float)):
                job_data['posted_date_str'] = datetime.fromtimestamp(listed_at / 1000.0).strftime('%Y-%m-%d')
            else: # Assume it's already a string
                job_data['posted_date_str'] = str(listed_at)
        except:
            job_data['posted_date_str'] = str(listed_at) # Fallback
    elif item_json.get('primary Zusatzinformationen', {}).get('text'): # German "additional information"
         job_data['posted_date_str'] = item_json.get('primary Zusatzinformationen', {}).get('text')


    # If we don't have at least a title or a URL or a job_id, it's probably not a valid job
    if not job_data.get('title') and not job_data.get('url') and not job_data.get('job_id'):
        logger.debug(f"Skipping JSON item, missing critical fields: {item_json.get('entityUrn', 'No URN')}")
        return None
        
    return {k: v for k, v in job_data.items() if v is not None and v != ''}


def parse_search_results_api_json(json_content: str | Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts job listings from LinkedIn search results API JSON response.
    """
    if not json_content:
        return []

    jobs: List[Dict[str, Any]] = []
    try:
        if isinstance(json_content, str):
            api_data = json.loads(json_content)
        elif isinstance(json_content, dict):
            api_data = json_content
        else:
            logger.error("Invalid JSON content type for search results API parsing.")
            raise ParseError("Invalid JSON content type for search results API parsing.")

        logger.debug("Parsing JSON search results for job listings.")
        
        # LinkedIn API responses can vary. Common structure is a root dict with an 'elements' list.
        # Sometimes 'included' also contains job postings.
        elements_to_check: List[Dict[str, Any]] = []
        if isinstance(api_data.get('elements'), list):
            elements_to_check.extend(api_data['elements'])
        if isinstance(api_data.get('included'), list): # Check 'included' for job postings too
            for item in api_data['included']:
                if isinstance(item, dict) and "JobPosting" in item.get('$type', ''):
                    elements_to_check.append(item)
        elif isinstance(api_data, list): # If the root itself is a list of jobs
            elements_to_check.extend(api_data)

        if not elements_to_check and isinstance(api_data, dict) and "JobPosting" in api_data.get('$type',''):
            # Case where the root dict is the job posting itself (less common for search results list)
            elements_to_check.append(api_data)

        if not elements_to_check:
            logger.warning("No 'elements' or 'included' list found in JSON, or root is not a list of jobs. Structure might have changed.")
            # Try to see if 'data' field contains the job postings
            if isinstance(api_data.get('data'), list):
                 elements_to_check.extend(api_data['data'])
            elif isinstance(api_data.get('data'), dict) and "JobPosting" in api_data['data'].get('$type',''):
                 elements_to_check.append(api_data['data'])


        for item_json in elements_to_check:
            # Filter out non-job posting elements if $type is present
            item_type = item_json.get('$type', '')
            if item_type and "JobPosting" not in item_type and "SearchJobJserp" not in item_type : # SearchJobJserp is another type for search results
                # logger.debug(f"Skipping element of type '{item_type}'")
                continue

            job_data = _extract_job_from_search_api_json_item(item_json)
            if job_data:
                jobs.append(job_data)
        
        logger.info(f"Extracted {len(jobs)} job entries from JSON API search results.")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from search results API: {e}")
        raise ParseError(f"Invalid JSON from search API: {e}") from e
    except Exception as e:
        logger.error(f"Error during JSON search results API parsing: {e}", exc_info=True)
        raise ParseError(f"Failed to parse JSON search results: {e}") from e
    return jobs