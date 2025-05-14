# File: harvest/core/linkedin_searcher.py

import logging
import time
import random
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse # For URL manipulation
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..interfaces.searcher import SearcherInterface, SearchOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import SEARCH_STARTED, JOB_FOUND, SEARCH_COMPLETED, SEARCH_ERROR, SEARCH_PAGE_FETCHED
from ..utils import http_utils, html_parser # Use our new utilities
from ..errors import NetworkError, AuthenticationError, ParseError # Our custom errors

logger = logging.getLogger(__name__)

class LinkedInSearcher(SearcherInterface):
    """
    Searches LinkedIn for job postings based on a given URL and options.
    Attempts to use LinkedIn's 'seeMoreJobPostings' API endpoint,
    and can fall back to parsing HTML if necessary (though API is preferred).
    """

    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        logger.info("LinkedInSearcher initialized.")

    def _extract_base_search_params(self, search_url: str) -> Dict[str, str]:
        """
        Extracts key parameters from the initial search URL relevant for API calls.
        Adapted from your old extract_query_params and important_params logic.
        """
        parsed_initial_url = urlparse(search_url)
        query_params = {k: v[0] for k, v in parse_qs(parsed_initial_url.query).items()}
        
        # Parameters LinkedIn search API often uses
        api_relevant_params = [
            'keywords', 'location', 'geoId', 'f_TPR', 'f_WT', 'f_E', 
            'f_JT', 'f_SB2', 'f_LF', 'f_I', 'f_CF', 'f_CP', 'f_CS', # Common filter params
            'distance', 'sortBy', 'currentJobId', 'position', 'pageNum'
        ]
        
        extracted_params: Dict[str, str] = {}
        for param in api_relevant_params:
            if param in query_params:
                extracted_params[param] = query_params[param]
        
        # Ensure 'guestId' or similar session identifiers are NOT carried over
        # if we intend to use a "guest" API or our own cookies.
        # For 'seeMoreJobPostings', it often works without deep session state.
        
        logger.debug(f"Extracted base API parameters from '{search_url}': {extracted_params}")
        return extracted_params

    def _build_api_url(self, base_api_endpoint: str, params: Dict[str, str], start: int, count: int) -> str:
        """
        Builds a paginated URL for LinkedIn's 'seeMoreJobPostings' API.
        Adapted from your old build_search_url.
        """
        api_call_params = params.copy() # Start with base search params
        api_call_params['start'] = str(start)
        api_call_params['count'] = str(count) # LinkedIn typically uses 'count', not 'jobs_per_page' for this API
        # api_call_params['guest'] = 'true' # Often needed for this endpoint

        # The base_api_endpoint should not have query params.
        # We construct a new query string.
        parsed_endpoint = urlparse(base_api_endpoint)
        new_query = urlencode(api_call_params, doseq=True)
        
        api_url = urlunparse((
            parsed_endpoint.scheme,
            parsed_endpoint.netloc,
            parsed_endpoint.path,
            parsed_endpoint.params, # Usually empty
            new_query,
            parsed_endpoint.fragment # Usually empty
        ))
        logger.debug(f"Constructed API URL: {api_url}")
        return api_url

    def search(self, search_url: str, options: Optional[SearchOptions] = None) -> List[Dict[str, Any]]:
        if not options: # Should ideally be provided by PipelineConfig
            options = SearchOptions() 
            logger.warning("LinkedInSearcher: No SearchOptions provided, using defaults.")

        self.event_bus.publish(SEARCH_STARTED, url=search_url)
        logger.info(f"Starting LinkedIn job search for URL: {search_url}")
        logger.info(f"Search options: Max Pages={options.max_pages}, Jobs/Page Attempt={options.jobs_per_page}, Delay={options.delay_between_requests}s")

        all_found_jobs: List[Dict[str, Any]] = []
        
        # LinkedIn's "guest" API endpoint for search results (often HTML containing JSON or just JSON)
        # This might need adjustment based on current LinkedIn structures.
        # The /jobs-guest/ part is key for unauthenticated/less-strict access.
        base_api_endpoint = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        # base_api_endpoint = "https://www.linkedin.com/voyager/api/search/hits" # More complex, needs auth

        base_params = self._extract_base_search_params(search_url)
        if not base_params.get('keywords') and not base_params.get('geoId') and not base_params.get('location'):
             logger.warning(f"Initial URL '{search_url}' lacks common search params (keywords, geoId, location). API calls may be less effective.")


        for page_num in range(options.max_pages):
            start_index = page_num * options.jobs_per_page
            
            api_url = self._build_api_url(base_api_endpoint, base_params, start_index, options.jobs_per_page)

            logger.info(f"Fetching page {page_num + 1}/{options.max_pages} using API URL: {api_url}")
            self.event_bus.publish(SEARCH_PAGE_FETCHED, page=(page_num + 1), total_pages=options.max_pages, url=api_url)

            try:
                response = http_utils.fetch_page_content(
                    url=api_url,
                    cookie_file=options.cookie_file, # Pass cookie file from options
                    max_retries=3, # Could also come from options
                    retry_delay=5, # Could also come from options
                    verbose_logging=True # Or tie to a global debug flag
                )

                if not response:
                    logger.error(f"Failed to fetch content for page {page_num + 1} from {api_url}. Stopping search for this URL.")
                    self.event_bus.publish(SEARCH_ERROR, error="Failed to fetch page content", url=api_url, page=page_num+1)
                    break # Stop processing this search_url

                page_jobs: List[Dict[str, Any]] = []
                content_type = response.headers.get("Content-Type", "").lower()

                if "application/json" in content_type or response.text.strip().startswith(("{", "[")):
                    try:
                        logger.debug(f"Attempting to parse page {page_num + 1} response as JSON.")
                        # The html_parser's parse_search_results_api_json expects dict or str
                        page_jobs = html_parser.parse_search_results_api_json(response.text)
                        logger.info(f"Parsed {len(page_jobs)} jobs from JSON response on page {page_num + 1}.")
                    except ParseError as pe:
                        logger.warning(f"Could not parse JSON from {api_url} (Page {page_num+1}), trying as HTML. Error: {pe}")
                        # Fall through to HTML parsing if JSON parsing fails structurally
                        page_jobs = html_parser.parse_search_results_html(response.text)
                        logger.info(f"Parsed {len(page_jobs)} jobs from HTML (after JSON parse attempt failed) on page {page_num + 1}.")
                    except Exception as e_json: # Catch other JSON processing errors
                        logger.error(f"Unexpected error processing JSON from {api_url}: {e_json}", exc_info=True)
                        self.event_bus.publish(SEARCH_ERROR, error=f"JSON processing error: {e_json}", url=api_url, page=page_num+1)
                        continue # Skip to next page or break
                else: # Assume HTML
                    logger.debug(f"Parsing page {page_num + 1} response as HTML (Content-Type: {content_type}).")
                    page_jobs = html_parser.parse_search_results_html(response.text)
                    logger.info(f"Parsed {len(page_jobs)} jobs from HTML response on page {page_num + 1}.")

                if not page_jobs and page_num > 0 : # If a subsequent page returns no jobs, we might be done.
                    logger.info(f"No jobs found on page {page_num + 1}. Assuming end of results for this search query.")
                    break 
                
                for job_data in page_jobs:
                    # Ensure essential fields like job_id, title, company, url are present or defaulted
                    # The parser should ideally handle this, but a check here is good.
                    # Add a timestamp for when it was found by this harvester
                    job_data['harvested_at'] = datetime.now().isoformat()
                    job_data['source_search_url'] = search_url # Keep track of original user-provided search URL
                    
                    self.event_bus.publish(JOB_FOUND, **job_data)
                    all_found_jobs.append(job_data)

                # Respectful delay
                if page_num < options.max_pages - 1 and page_jobs: # Only delay if there are more pages to fetch and current page had jobs
                    time.sleep(options.delay_between_requests * random.uniform(0.8, 1.2))

            except (NetworkError, AuthenticationError) as net_auth_err:
                logger.error(f"Search for {search_url} failed due to: {net_auth_err}", exc_info=True)
                self.event_bus.publish(SEARCH_ERROR, error=str(net_auth_err), url=api_url, page=page_num+1, error_type=type(net_auth_err).__name__)
                break # Stop processing this search_url on critical network/auth errors
            except ParseError as pe: # Catch ParseErrors from html_parser
                logger.error(f"Search for {search_url} failed due to parsing error on page {page_num+1}: {pe}", exc_info=True)
                self.event_bus.publish(SEARCH_ERROR, error=str(pe), url=api_url, page=page_num+1, error_type="ParseError")
                # Decide whether to break or continue to next page. Let's continue for now.
            except Exception as e:
                logger.critical(f"An unexpected error occurred during search for {search_url} on page {page_num + 1}: {e}", exc_info=True)
                self.event_bus.publish(SEARCH_ERROR, error=f"Unexpected: {str(e)}", url=api_url, page=page_num+1, error_type="CriticalSearchError")
                break # Stop on truly unexpected errors

        logger.info(f"Search completed for {search_url}. Total jobs found: {len(all_found_jobs)} across processed pages.")
        self.event_bus.publish(SEARCH_COMPLETED, jobs_found=len(all_found_jobs), original_search_url=search_url)
        return all_found_jobs