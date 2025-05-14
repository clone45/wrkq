# File: harvest/core/linkedin_detailer.py

import logging
import time
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..interfaces.detailer import DetailerInterface, DetailOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import DETAIL_FETCHING_STARTED, JOB_DETAILS_FETCHED, DETAIL_FETCHING_COMPLETED, DETAIL_ERROR
from ..utils import http_utils, html_parser, file_utils # Assuming file_utils for saving raw pages
from ..errors import NetworkError, AuthenticationError, ParseError # Our custom errors

logger = logging.getLogger(__name__)

class LinkedInDetailer(DetailerInterface):
    """
    Fetches detailed information for LinkedIn job postings.
    """

    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        logger.info("LinkedInDetailer initialized.")

    def fetch_details_batch(self, jobs: List[Dict[str, Any]], options: Optional[DetailOptions] = None) -> List[Dict[str, Any]]:
        if not options:
            options = DetailOptions() # Use defaults if none provided
            logger.warning("LinkedInDetailer: No DetailOptions provided, using defaults.")

        if not jobs:
            logger.info("LinkedInDetailer: No jobs provided to fetch details for.")
            self.event_bus.publish(DETAIL_FETCHING_STARTED, job_count=0)
            self.event_bus.publish(DETAIL_FETCHING_COMPLETED, job_count=0)
            return []

        total_jobs_to_process = len(jobs)
        logger.info(f"LinkedInDetailer: Starting to fetch details for {total_jobs_to_process} jobs.")
        self.event_bus.publish(DETAIL_FETCHING_STARTED, job_count=total_jobs_to_process)

        enriched_jobs: List[Dict[str, Any]] = []
        details_fetched_count = 0

        for i, basic_job_data in enumerate(jobs):
            job_url = basic_job_data.get('url')
            job_id_for_log = basic_job_data.get('job_id', 'N/A')
            job_title_for_log = basic_job_data.get('title', 'Unknown Title')
            
            self.event_bus.publish( # Update UI about current job being processed
                "event_handlers.update_current_job", # Assuming a generic event your UI can pick up
                                                     # Or use existing status message logic in RichProgressDisplay
                current_job_message=f"Detailing: {job_title_for_log[:50]}..."
            )


            if not job_url:
                logger.warning(f"Skipping job {i+1}/{total_jobs_to_process} (Ext.ID: {job_id_for_log}): No URL available.")
                self.event_bus.publish(DETAIL_ERROR, 
                                       error="No URL provided for job", 
                                       job_id=job_id_for_log, 
                                       title=job_title_for_log)
                enriched_jobs.append(basic_job_data) # Keep basic data
                continue

            logger.info(f"Fetching details for job {i+1}/{total_jobs_to_process}: {job_title_for_log} (Ext.ID: {job_id_for_log}) from {job_url}")

            try:
                response = http_utils.fetch_page_content(
                    url=job_url,
                    cookie_file=options.cookie_file,
                    max_retries=3, # Consider making these part of DetailOptions
                    retry_delay=5,
                    verbose_logging=True # Or based on a global debug setting
                )

                if not response:
                    # Error already logged by fetch_page_content, and it raises NetworkError/AuthError
                    # This path might not be hit if fetch_page_content always raises on total failure.
                    logger.error(f"No response received for job detail URL: {job_url}")
                    self.event_bus.publish(DETAIL_ERROR, error="No response from server", job_id=job_id_for_log, title=job_title_for_log, url=job_url)
                    enriched_jobs.append(basic_job_data)
                    continue
                
                # Optionally save raw HTML page
                if options.output_dir:
                    try:
                        # Ensure output_dir is a Path object
                        output_dir_path = Path(options.output_dir)
                        # Create a subdirectory for detail pages to keep things organized
                        detail_pages_dir = output_dir_path / "detail_pages"
                        detail_pages_dir.mkdir(parents=True, exist_ok=True)

                        file_path = file_utils.generate_filename_from_url(
                            url=job_url,
                            output_directory=detail_pages_dir,
                            extension="html",
                            prefix=f"job_detail_{job_id_for_log or ''}"
                        )
                        if file_utils.save_text_to_file(response.text, file_path):
                            logger.debug(f"Saved raw detail page HTML to {file_path}")
                        else:
                            logger.warning(f"Failed to save raw detail page HTML to {file_path}")
                    except Exception as e_save:
                        logger.warning(f"Could not save detail page HTML for {job_url}: {e_save}")


                # Parse the HTML content
                extracted_details = html_parser.parse_job_detail_page(response.text)

                if extracted_details:
                    # Merge extracted details with basic job data.
                    # Extracted details should take precedence for common fields if fresher.
                    # Be careful about overwriting essential IDs like 'job_id' from search if parser doesn't get it.
                    final_job_data = basic_job_data.copy() # Start with basic info
                    final_job_data.update(extracted_details) # Override/add with details
                    
                    # Ensure critical IDs from basic_job_data are not lost if parser missed them
                    if 'job_id' not in final_job_data and basic_job_data.get('job_id'):
                        final_job_data['job_id'] = basic_job_data['job_id']
                    if 'url' not in final_job_data and basic_job_data.get('url'):
                         final_job_data['url'] = basic_job_data['url']


                    enriched_jobs.append(final_job_data)
                    self.event_bus.publish(JOB_DETAILS_FETCHED, 
                                           index=i, 
                                           total=total_jobs_to_process, 
                                           **final_job_data)
                    details_fetched_count += 1
                    logger.info(f"Successfully fetched and parsed details for job Ext.ID: {job_id_for_log}")
                else:
                    logger.warning(f"Could not extract details for job Ext.ID: {job_id_for_log} from {job_url}. Keeping basic data.")
                    self.event_bus.publish(DETAIL_ERROR, error="Failed to parse details from page", job_id=job_id_for_log, title=job_title_for_log, url=job_url)
                    enriched_jobs.append(basic_job_data) # Keep basic data

            except (NetworkError, AuthenticationError) as net_auth_err:
                logger.error(f"Detail fetching for job Ext.ID {job_id_for_log} failed: {net_auth_err}", exc_info=False) # exc_info=False as http_utils logs it
                self.event_bus.publish(DETAIL_ERROR, error=str(net_auth_err), job_id=job_id_for_log, title=job_title_for_log, url=job_url, error_type=type(net_auth_err).__name__)
                enriched_jobs.append(basic_job_data) # Keep basic data
            except ParseError as pe:
                logger.error(f"Parsing error for job Ext.ID {job_id_for_log} details: {pe}", exc_info=False) # html_parser logs it
                self.event_bus.publish(DETAIL_ERROR, error=str(pe), job_id=job_id_for_log, title=job_title_for_log, url=job_url, error_type="ParseError")
                enriched_jobs.append(basic_job_data)
            except Exception as e:
                logger.critical(f"Unexpected error fetching details for job Ext.ID {job_id_for_log} ({job_url}): {e}", exc_info=True)
                self.event_bus.publish(DETAIL_ERROR, error=f"Unexpected: {str(e)}", job_id=job_id_for_log, title=job_title_for_log, url=job_url, error_type="CriticalDetailError")
                enriched_jobs.append(basic_job_data) # Keep basic data
            finally:
                # Respectful delay, only if there are more jobs AND this wasn't the last one
                if i < total_jobs_to_process - 1:
                    time.sleep(options.delay_between_requests * random.uniform(0.8, 1.2))
        
        logger.info(f"LinkedInDetailer: Finished fetching details. Successfully detailed {details_fetched_count} out of {total_jobs_to_process} jobs attempted.")
        self.event_bus.publish(DETAIL_FETCHING_COMPLETED, job_count=total_jobs_to_process, details_successful_count=details_fetched_count)
        return enriched_jobs