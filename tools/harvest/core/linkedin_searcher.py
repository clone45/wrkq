# File: harvest/core/linkedin_searcher.py (Updated)

import logging
import time
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

from ..interfaces.searcher import SearcherInterface, SearchOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import EventType
from ..errors import NetworkError, AuthenticationError, ParseError
from ..utils import http_utils # For any utility functions you might want to keep

logger = logging.getLogger(__name__)

class LinkedInSearcher(SearcherInterface):
    """
    Searches LinkedIn for job postings using the Voyager API.
    """

    def __init__(self, event_bus: EventBusInterface, http_client=None):
        self.event_bus = event_bus
        self.http_client = http_client
        logger.info("LinkedInSearcher initialized.")

    def _load_cookies(self, cookie_file_path: Path) -> Dict[str, str]:
        """Load cookies from a JSON file."""
        if not cookie_file_path.exists():
            logger.error(f"Cookie file not found at: {cookie_file_path}")
            return {}

        try:
            with open(cookie_file_path, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
                
            cookies_dict = {}
            if isinstance(cookies_data, list):
                for cookie in cookies_data:
                    if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                        cookies_dict[cookie['name']] = cookie['value']
            elif isinstance(cookies_data, dict):
                cookies_dict = cookies_data
                
            logger.info(f"Loaded {len(cookies_dict)} cookies")
            return cookies_dict
        except Exception as e:
            logger.error(f"Error loading cookies from {cookie_file_path}: {e}")
            return {}

    def _extract_keyword_and_location(self, search_url: str) -> tuple:
        """Extract keywords and location from a LinkedIn search URL."""
        parsed_url = urlparse(search_url)
        query_params = parse_qs(parsed_url.query)
        
        keywords = query_params.get('keywords', [''])[0]
        location = query_params.get('location', [''])[0]
        geo_id = query_params.get('geoId', ['90000084'])[0]  # Default to San Francisco if not found
        
        return keywords, location, geo_id

    def search(self, search_url: str, options: Optional[SearchOptions] = None) -> List[Dict[str, Any]]:
        """
        Search LinkedIn for jobs using the provided search URL.
        
        Args:
            search_url: The LinkedIn search URL to use
            options: Optional search configuration
            
        Returns:
            List of job data dictionaries
        """
        if not options:
            options = SearchOptions()
            logger.warning("LinkedInSearcher: No SearchOptions provided, using defaults.")

        self.event_bus.publish(EventType.SEARCH_STARTED, url=search_url)
        logger.info(f"Starting LinkedIn job search with URL: {search_url}")

        # Validate URL
        try:
            parsed_url = urlparse(search_url)
            if not parsed_url.netloc or "linkedin.com" not in parsed_url.netloc:
                error_msg = f"Invalid LinkedIn URL: {search_url}"
                logger.error(error_msg)
                self.event_bus.publish(EventType.SEARCH_ERROR, error=error_msg, url=search_url)
                return []
        except Exception as e:
            error_msg = f"Failed to parse URL '{search_url}': {e}"
            logger.error(error_msg)
            self.event_bus.publish(EventType.SEARCH_ERROR, error=error_msg, url=search_url)
            return []

        all_found_jobs = []
        
        # Load cookies
        cookie_file = Path(options.cookie_file) if options.cookie_file else None
        cookies = self._load_cookies(cookie_file) if cookie_file else {}
        
        if 'li_at' not in cookies or 'JSESSIONID' not in cookies:
            error_msg = "Missing required LinkedIn cookies (li_at and JSESSIONID)"
            logger.error(error_msg)
            self.event_bus.publish(EventType.SEARCH_ERROR, error=error_msg, url=search_url)
            return []
            
        logger.info(f"Loaded cookies successfully: {', '.join(cookies.keys())}")
        
        # Extract search parameters from URL
        keywords, location, geo_id = self._extract_keyword_and_location(search_url)
        logger.info(f"Extracted search parameters - Keywords: '{keywords}', Location: '{location}', GeoId: '{geo_id}'")

        # Search through pages
        for page_num in range(options.max_pages):
            start_index = page_num * options.jobs_per_page
            
            # Build URL for current page
            url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            
            # Build query parameters
            query_params = {
                "keywords": keywords,
                "location": location,
                "geoId": geo_id,
                "start": start_index,
                "count": options.jobs_per_page,
                "f_TPR": "r86400",  # Last 24 hours
                "f_WT": "2",  # Remote jobs
                "guest": "true"
            }
            
            # Add any additional parameters from the original URL
            original_params = parse_qs(parsed_url.query)
            for key, values in original_params.items():
                if key not in query_params and key not in ['start', 'count']:
                    query_params[key] = values[0]
            
            # Build the URL with parameters
            param_strings = []
            for key, value in query_params.items():
                param_strings.append(f"{key}={value}")
            
            full_url = f"{url}?{'&'.join(param_strings)}"
            
            # Fetch the page
            logger.info(f"Fetching page {page_num + 1}/{options.max_pages} from: {full_url}")
            self.event_bus.publish(EventType.SEARCH_PAGE_FETCHED, page=(page_num + 1), total_pages=options.max_pages, url=full_url)
            
            try:
                # Use curl-cffi for requests
                from curl_cffi import requests
                
                response = requests.get(
                    full_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://www.linkedin.com/',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'TE': 'Trailers'
                    },
                    cookies=cookies,
                    impersonate="chrome110",
                    timeout=30,
                    allow_redirects=True
                )
                
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    error_msg = f"API request failed: Status {response.status_code}"
                    logger.error(error_msg)
                    logger.error(f"Response content: {response.text[:500]}...")  # Log first 500 chars of error response
                    self.event_bus.publish(EventType.SEARCH_ERROR, error=error_msg, url=full_url, page=page_num+1)
                    break
                
                # Parse response as HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all job cards
                job_cards = soup.select('.base-search-card')
                logger.info(f"Found {len(job_cards)} job cards on page {page_num + 1}")
                
                # Process each job card
                for card in job_cards:
                    try:
                        job_data = {}
                        
                        # Get job ID from data-entity-urn attribute
                        entity_urn = card.get('data-entity-urn', '')
                        if entity_urn:
                            job_data['job_id'] = entity_urn.split(':')[-1]
                        
                        # Get job title
                        title_elem = card.select_one('.base-search-card__title')
                        if title_elem:
                            job_data['title'] = title_elem.get_text(strip=True)
                        
                        # Get company name
                        company_elem = card.select_one('.base-search-card__subtitle')
                        if company_elem:
                            job_data['company'] = company_elem.get_text(strip=True)
                        
                        # Get location
                        location_elem = card.select_one('.job-search-card__location')
                        if location_elem:
                            job_data['location'] = location_elem.get_text(strip=True)
                        
                        # Get job URL
                        link_elem = card.select_one('a.base-card__full-link')
                        if link_elem:
                            job_data['url'] = link_elem.get('href', '')
                        
                        # Get listed date
                        time_elem = card.select_one('time')
                        if time_elem:
                            job_data['listed_at'] = time_elem.get('datetime')
                        
                        # Only add jobs that have at least an ID and either a title or URL
                        if job_data.get('job_id') and (job_data.get('title') or job_data.get('url')):
                            job_data['harvested_at'] = datetime.now().isoformat()
                            job_data['source_search_url'] = search_url
                            all_found_jobs.append(job_data)
                            self.event_bus.publish(EventType.JOB_FOUND, **job_data)
                            
                    except Exception as e:
                        logger.warning(f"Error processing job card: {e}")
                        continue
                
                # Stop if no more jobs found
                if len(job_cards) == 0:
                    logger.info(f"No more jobs found on page {page_num + 1}. Stopping search.")
                    break
                
                # Delay before next page
                if page_num < options.max_pages - 1 and len(job_cards) > 0:
                    delay = options.delay_between_requests * random.uniform(0.8, 1.2)
                    logger.info(f"Waiting {delay:.2f} seconds before next request")
                    time.sleep(delay)
                
            except Exception as e:
                error_msg = f"Error during search: {e}"
                logger.error(error_msg, exc_info=True)
                self.event_bus.publish(EventType.SEARCH_ERROR, error=error_msg, url=full_url, page=page_num+1)
                break
        
        logger.info(f"Search completed for {search_url}. Total jobs found: {len(all_found_jobs)}")
        self.event_bus.publish(EventType.SEARCH_COMPLETED, jobs_found=len(all_found_jobs), original_search_url=search_url)
        return all_found_jobs

    def _extract_text(self, text_view):
        """Extract text from LinkedIn's TextView object format."""
        if not text_view:
            return ""
        
        if isinstance(text_view, dict):
            return text_view.get('text', '')
        
        return str(text_view)

    def _extract_timestamp(self, footer_items):
        """Extract timestamp from LinkedIn's JobPostingCardFooterItem objects."""
        if not footer_items:
            logger.warning("No footer items found for timestamp extraction")
            return None
            
        for item in footer_items:
            if not isinstance(item, dict):
                logger.warning(f"Footer item is not a dictionary: {type(item)}")
                continue
                
            if item.get('type') == 'LISTED_DATE':
                if 'timeAt' not in item:
                    logger.warning("Found LISTED_DATE item but missing timeAt field")
                    continue
                    
                timestamp = item.get('timeAt')
                try:
                    date_str = datetime.fromtimestamp(timestamp / 1000.0).strftime('%Y-%m-%d')
                    return date_str
                except Exception as e:
                    logger.error(f"Failed to parse timestamp {timestamp}: {str(e)}")
                    return None
                    
        logger.warning("No LISTED_DATE item found in footer items")
        return None

    def _add_params_to_url(self, base_url: str, params: Dict[str, Any]) -> str:
        """Add query parameters to URL."""
        parsed = urlparse(base_url)
        existing_params = parse_qs(parsed.query)
        
        # Merge existing and new params
        all_params = {**existing_params, **params}
        
        # Rebuild query string
        query_parts = []
        for key, value in all_params.items():
            if isinstance(value, list):
                value = value[0]
            query_parts.append(f"{key}={value}")
            
        new_query = "&".join(query_parts)
        
        # Reconstruct URL
        return parsed._replace(query=new_query).geturl()