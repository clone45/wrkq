"""Functions for extracting job data from LinkedIn HTML content."""

import json
import re
import logging
from datetime import datetime
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

def extract_job_data_from_html(html_content):
    """
    Attempts to extract job data by finding and parsing JSON embedded in <code> tags.
    Includes resolving company name from 'included' array.

    Args:
        html_content: The raw HTML string.

    Returns:
        A dictionary containing extracted job data (e.g., title, description),
        or None if relevant JSON could not be found or parsed.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # --- Strategy 1: Find JSON in <code> tags ---
    # LinkedIn often uses code tags with specific ID patterns for data islands
    data_tag_ids = re.compile(r'^(bpr-guid-|datalet-bpr-guid-).*')
    code_tags = soup.find_all('code', id=data_tag_ids)

    logger.info(f"Found {len(code_tags)} potential data containers in HTML")
    
    job_posting_data = None
    full_json_data = None  # Store the full JSON blob where the job posting was found

    for tag in code_tags:
        try:
            logger.debug(f"Checking code tag with id: {tag.get('id')}")
            
            # Skip empty tags
            if not tag.string or not tag.string.strip():
                continue
                
            potential_full_json = json.loads(tag.string)

            # Check if 'data' contains job posting info
            if isinstance(potential_full_json.get('data'), dict) and \
               potential_full_json['data'].get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                 job_posting_data = potential_full_json['data']
                 full_json_data = potential_full_json  # Keep the whole blob
                 logger.info(f"Found job data in tag {tag.get('id')} (direct data)")
                 break

            # Check within 'elements' if it's a collection
            if isinstance(potential_full_json.get('elements'), list):
                for element in potential_full_json['elements']:
                     # Check within element's 'data' if it exists
                     if isinstance(element.get('data'), dict) and \
                        element['data'].get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                           job_posting_data = element['data']
                           full_json_data = potential_full_json  # Keep the whole blob
                           logger.info(f"Found job data in tag {tag.get('id')} (within elements list)")
                           break
                     # Sometimes the element itself is the job data
                     elif isinstance(element, dict) and \
                          element.get('$type') == 'com.linkedin.voyager.jobs.JobPosting':
                            job_posting_data = element
                            full_json_data = potential_full_json  # Keep the whole blob
                            logger.info(f"Found job data in tag {tag.get('id')} (as element)")
                            break

            if job_posting_data:
                 break # Exit outer loop if found in inner loop

        except json.JSONDecodeError:
            logger.debug(f"Tag {tag.get('id')} is not valid JSON.")
            continue
        except Exception as e:
            logger.error(f"Error processing tag {tag.get('id')}: {e}")
            continue

    if not job_posting_data or not full_json_data:
        logger.warning("Could not find structured job JSON in <code> tags")
        return fallback_to_html_extraction(html_content)

    # --- Extract specific fields from the found JSON ---
    extracted_data = {}
    
    extracted_data['title'] = job_posting_data.get('title', 'N/A')
    
    # The description might be nested within another object
    description_obj = job_posting_data.get('description')
    if isinstance(description_obj, dict):
        extracted_data['description_raw'] = description_obj.get('text', '')
        # Clean the description HTML if it contains markup
        if extracted_data['description_raw']:
            desc_soup = BeautifulSoup(extracted_data['description_raw'], 'html.parser')
            extracted_data['description_cleaned'] = desc_soup.get_text(separator='\n', strip=True)
    else:
        extracted_data['description_raw'] = str(description_obj) if description_obj else ''
        extracted_data['description_cleaned'] = extracted_data['description_raw']
    
    # Extract location
    extracted_data['location'] = job_posting_data.get('formattedLocation', 'N/A')
    
    # --- Company Name Extraction (improved) ---
    extracted_data['company_name'] = "Company Name Not Found"  # Default
    company_details = job_posting_data.get('companyDetails', {})
    company_urn = None
    
    if isinstance(company_details, dict):
        # Get the URN that points to the company object in the 'included' array
        # Sometimes it's 'company', sometimes '*companyResolutionResult'
        company_urn = company_details.get('company') or company_details.get('*companyResolutionResult')
        extracted_data['company_urn'] = company_urn
        
    if company_urn and isinstance(full_json_data.get('included'), list):
        logger.info(f"Looking for company URN: {company_urn} in included data")
        for included_item in full_json_data['included']:
            if isinstance(included_item, dict) and included_item.get('entityUrn') == company_urn:
                # Found the matching company object
                extracted_data['company_name'] = included_item.get('name', "Company Name Not Found in Included")
                logger.info(f"Found company name: {extracted_data['company_name']}")
                
                # Additional company details if needed
                extracted_data['company_universal_name'] = included_item.get('universalName', '')
                
                # Company logo URL if available
                logo_data = included_item.get('logo', {})
                if isinstance(logo_data, dict) and isinstance(logo_data.get('image'), dict):
                    extracted_data['company_logo_url'] = logo_data['image'].get('rootUrl', '')
                
                break  # Stop searching included items
    else:
        logger.warning("Could not find company URN or 'included' array in JSON")
    
    # Extract job posting date if available
    if 'listedAt' in job_posting_data:
        try:
            # LinkedIn timestamps are usually in milliseconds
            from datetime import datetime
            timestamp_ms = job_posting_data.get('listedAt')
            if isinstance(timestamp_ms, (int, float)):
                post_date = datetime.fromtimestamp(timestamp_ms / 1000.0)
                extracted_data['posted_date'] = post_date.strftime('%Y-%m-%d')
                # Add posting_date for job tracker compatibility
                extracted_data['posting_date'] = post_date.strftime('%Y-%m-%d')
            else:
                extracted_data['posted_date'] = str(timestamp_ms)
                extracted_data['posting_date'] = str(timestamp_ms)
        except Exception as e:
            logger.error(f"Error parsing job post date: {e}")
            extracted_data['posted_date'] = 'Unknown'
            extracted_data['posting_date'] = 'Unknown'
    
    # Extract employment type if available
    employment_type = job_posting_data.get('employmentStatus', {})
    if isinstance(employment_type, dict):
        extracted_data['employment_type'] = employment_type.get('text', 'Not specified')
    
    # Extract salary information if available
    try:
        compensation = job_posting_data.get('compensation', {})
        if isinstance(compensation, dict):
            # LinkedIn has different formats for salary info
            if 'compensationRange' in compensation:
                ranges = compensation.get('compensationRange', {})
                if isinstance(ranges, dict) and 'min' in ranges and 'max' in ranges:
                    min_value = ranges['min'].get('value')
                    max_value = ranges['max'].get('value')
                    currency = ranges['min'].get('currencyCode', 'USD')
                    extracted_data['salary'] = f"{currency} {min_value}-{max_value}"
            # Alternative field: directly available in the compensation object
            elif 'baseSalary' in compensation:
                base_salary = compensation.get('baseSalary', {})
                if isinstance(base_salary, dict):
                    value = base_salary.get('value')
                    if value:
                        extracted_data['salary'] = str(value)
    except Exception as e:
        logger.error(f"Error extracting salary information: {e}")
        
    # Add source field for job tracker compatibility
    extracted_data['source'] = 'LinkedIn'
    
    # Add company field for compatibility (while keeping company_name)
    if 'company_name' in extracted_data:
        extracted_data['company'] = extracted_data['company_name']
    
    # Extract other fields that might be useful
    extracted_data['applies'] = job_posting_data.get('applies', 0)
    extracted_data['views'] = job_posting_data.get('views', 0)
    
    # Keep the job ID for reference
    if 'entityUrn' in job_posting_data:
        try:
            # Extract just the numeric ID from the URN
            urn = job_posting_data['entityUrn']
            job_id_match = re.search(r'jobPosting:(\d+)', urn)
            if job_id_match:
                extracted_data['job_id'] = job_id_match.group(1)
            else:
                extracted_data['job_id'] = urn
        except:
            extracted_data['job_id'] = job_posting_data.get('entityUrn', 'Unknown')
    
    return extracted_data

def fallback_to_html_extraction(html_content):
    """
    Extracts text content from HTML as fallback if JSON extraction fails.
    
    Args:
        html_content: The raw HTML string.
        
    Returns:
        Dictionary with basic extracted information or None.
    """
    logger.info("Falling back to HTML content extraction")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find the main content area
    possible_selectors = [
        'div.jobs-description__content',
        '#job-details',
        '.job-description',
        'article',
        'main'
    ]
    
    main_content_tag = None
    for selector in possible_selectors:
        main_content_tag = soup.select_one(selector)
        if main_content_tag:
            logger.info(f"Found content using selector: {selector}")
            break
    
    if not main_content_tag:
        logger.warning("Could not find main content area in HTML")
        return None
    
    # Try to extract title, company, etc.
    job_info = {}
    
    # Look for job title
    title_tag = soup.find('h1', class_='job-title') or soup.find('h1', class_='top-card-layout__title')
    if title_tag:
        job_info['title'] = title_tag.text.strip()
    
    # Look for company name
    company_tag = soup.find('a', class_='topcard__org-name-link') or soup.find('span', class_='topcard__flavor')
    if company_tag:
        job_info['company_name'] = company_tag.text.strip()
    
    # Look for location
    location_tag = soup.find('span', class_='topcard__flavor--bullet')
    if location_tag:
        job_info['location'] = location_tag.text.strip()
    
    # Extract the full content as fallback
    job_info['description_raw'] = main_content_tag.get_text(separator='\n', strip=True)
    job_info['description_cleaned'] = job_info['description_raw']
    
    # Add job tracker compatible field names
    job_info['description'] = job_info['description_cleaned']
    if 'company_name' in job_info:
        job_info['company'] = job_info['company_name']
    job_info['source'] = 'LinkedIn'
    job_info['posting_date'] = datetime.now().strftime('%Y-%m-%d')
    
    return job_info