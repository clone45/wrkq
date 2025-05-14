# File: harvest/core/pipeline.py

import logging
from typing import List, Dict, Any, Optional

from ..interfaces.pipeline import JobPipeline as JobPipelineInterface, PipelineConfig
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..interfaces.searcher import SearcherInterface
from ..interfaces.detailer import DetailerInterface
from ..interfaces.filterer import FiltererInterface
from ..interfaces.storer import StorerInterface
from ..events import *  # Import all your event constants (ensure PIPELINE_ERROR is here)
from ..errors import HarvestError, NetworkError, ParseError, AuthenticationError, DatabaseError, ConfigError # Import your custom errors

logger = logging.getLogger(__name__)

class Pipeline(JobPipelineInterface):
    """
    Core implementation of the job processing pipeline.
    Orchestrates search, detail fetching, filtering, and storage.
    """

    def __init__(self,
                 event_bus: EventBusInterface,
                 searcher: SearcherInterface,
                 detailer: DetailerInterface,
                 filterer: FiltererInterface,
                 storer: StorerInterface,
                 default_config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline.
        (Constructor remains the same as previously discussed)
        """
        self.event_bus = event_bus
        self.searcher = searcher
        self.detailer = detailer
        self.filterer = filterer
        self.storer = storer
        self.default_config = default_config
        logger.info("Core Pipeline initialized.")

    def _get_effective_config(self, config_override: Optional[PipelineConfig]) -> Optional[PipelineConfig]:
        """Helper to determine which config to use."""
        if config_override is not None:
            return config_override
        if self.default_config is not None:
            return self.default_config
        # Potentially raise ConfigError if no configuration is available and it's required
        # logger.warning("No pipeline configuration provided or defaulted. Components might use their own defaults or fail.")
        return None # Or an empty PipelineConfig if components expect the structure

    def process_url(self, url: str, config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """
        Process a single LinkedIn search URL.
        """
        effective_config = self._get_effective_config(config)
        
        logger.info(f"Processing URL: {url}")
        self.event_bus.publish(URL_PROCESSING_STARTED, url=url)

        url_stats: Dict[str, int] = {
            "jobs_found": 0,
            "jobs_duplicate": 0,  # New stat for duplicate jobs
            "jobs_detailed": 0,
            "jobs_filtered_out": 0,
            "jobs_kept": 0,
            "jobs_stored_attempts": 0, 
            "errors": 0
        }

        try:
            # 1. Search
            search_opts = effective_config.search_options if effective_config else None
            found_jobs: List[Dict[str, Any]] = self.searcher.search(url, options=search_opts)
            url_stats["jobs_found"] = len(found_jobs)

            if not found_jobs:
                logger.info(f"No jobs found for URL: {url}")
                return url_stats  # Exit early for this URL if no jobs

            # Get storage options for duplicate checking
            storage_opts = effective_config.storage_options if effective_config else None
            
            # 2. Check for duplicates
            unique_jobs: List[Dict[str, Any]] = []
            duplicate_jobs: List[Dict[str, Any]] = []
            
            for job in found_jobs:
                # Pass storage options to is_duplicate_job
                if self.storer.is_duplicate_job(job, options=storage_opts):
                    duplicate_jobs.append(job)
                    job_title = job.get('title', 'Unknown Title')
                    job_company = job.get('company', 'Unknown Company')
                    logger.info(f"Found duplicate job: '{job_title}' at '{job_company}'")
                    self.event_bus.publish(JOB_DUPLICATE_FOUND, **job)
                else:
                    unique_jobs.append(job)
            
            url_stats["jobs_duplicate"] = len(duplicate_jobs)
            logger.info(f"Found {len(duplicate_jobs)} duplicate jobs and {len(unique_jobs)} unique jobs")

            # 3. Detail Fetching (only for unique jobs)
            detail_opts = effective_config.detail_options if effective_config else None
            
            if unique_jobs:
                # Only fetch details for non-duplicate jobs
                detailed_jobs: List[Dict[str, Any]] = self.detailer.fetch_details_batch(unique_jobs, options=detail_opts)
                
                # Count how many jobs actually got details
                url_stats["jobs_detailed"] = sum(1 for job in detailed_jobs if job.get('description'))
            else:
                detailed_jobs = []
                url_stats["jobs_detailed"] = 0
                logger.info(f"No unique jobs to fetch details for in URL: {url}")

            # Rest of the method remains the same...
            # 4. Filtering
            filter_opts = effective_config.filter_options if effective_config else None
            kept_jobs: List[Dict[str, Any]] = self.filterer.filter_job_batch(detailed_jobs, options=filter_opts)
            url_stats["jobs_kept"] = len(kept_jobs)
            url_stats["jobs_filtered_out"] = len(detailed_jobs) - len(kept_jobs)

            if not kept_jobs:
                logger.info(f"No jobs kept after filtering for URL: {url}")
                return url_stats  # Exit early if no jobs to store

            # 5. Storage
            self.storer.store_job_batch(kept_jobs, options=storage_opts)
            url_stats["jobs_stored_attempts"] = len(kept_jobs)

            logger.info(f"Successfully completed processing stages for URL: {url}")
        # Specific Harvest Errors - these are "known" error types from our application
        except AuthenticationError as ae:
            logger.error(f"Authentication error during processing of {url}: {ae}")
            self.event_bus.publish(PIPELINE_ERROR, error=str(ae), url=url, stage="url_processing", error_type="AuthenticationError")
            url_stats["errors"] += 1
        except NetworkError as ne:
            logger.error(f"Network error during processing of {url}: {ne}")
            self.event_bus.publish(PIPELINE_ERROR, error=str(ne), url=url, stage="url_processing", error_type="NetworkError")
            url_stats["errors"] += 1
        except ParseError as pe:
            logger.error(f"Parse error during processing of {url}: {pe}")
            self.event_bus.publish(PIPELINE_ERROR, error=str(pe), url=url, stage="url_processing", error_type="ParseError")
            url_stats["errors"] += 1
        except DatabaseError as dbe:
            logger.error(f"Database error during processing of {url}: {dbe}")
            self.event_bus.publish(PIPELINE_ERROR, error=str(dbe), url=url, stage="url_processing", error_type="DatabaseError")
            url_stats["errors"] += 1
        except ConfigError as ce: # Should ideally be caught before pipeline runs, but possible if config passed per-url
            logger.error(f"Configuration error during processing of {url}: {ce}")
            self.event_bus.publish(PIPELINE_ERROR, error=str(ce), url=url, stage="url_processing", error_type="ConfigError")
            url_stats["errors"] += 1
        except HarvestError as he: # Catch any other custom HarvestError
            logger.error(f"A harvester-specific error occurred for {url}: {he}", exc_info=True)
            self.event_bus.publish(PIPELINE_ERROR, error=str(he), url=url, stage="url_processing", error_type=type(he).__name__)
            url_stats["errors"] += 1
        
        # Catch-all for unexpected errors
        except Exception as e:
            logger.critical(f"An UNEXPECTED critical error occurred processing URL {url}: {e}", exc_info=True)
            # For truly unexpected errors, publish a distinct event or add more detail
            self.event_bus.publish(PIPELINE_ERROR, error=f"Unexpected: {str(e)}", url=url, stage="url_processing", error_type="CriticalError")
            url_stats["errors"] += 1
            # Depending on your strategy, you might want to re-raise critical errors
            # to halt the entire application, or just this URL's processing.
            # For now, it continues to the finally block.
        
        finally:
            # This ensures URL_PROCESSING_COMPLETED is always published for the URL,
            # regardless of success or failure within the try block.
            # The UI (RichProgressDisplay) uses this event to advance its URL counter.
            self.event_bus.publish(URL_PROCESSING_COMPLETED, url=url, **url_stats)
            logger.info(f"Finished processing URL: {url}. Stats: {url_stats}")

        return url_stats

    def process_urls(self, urls: List[str], config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """
        Process multiple LinkedIn search URLs.
        """
        logger.info(f"Starting processing for {len(urls)} URLs.")
        self.event_bus.publish(PIPELINE_STARTED, url_count=len(urls))

        aggregated_stats: Dict[str, int] = {
            "total_urls_processed": 0,
            "total_jobs_found": 0,
            "total_jobs_duplicate": 0,  # New stat for duplicates
            "total_jobs_detailed": 0,
            "total_jobs_filtered_out": 0,
            "total_jobs_kept": 0,
            "total_jobs_stored_attempts": 0,
            "total_errors": 0
        }

        for i, url in enumerate(urls):
            try:
                url_stats = self.process_url(url, config=config) 
                
                aggregated_stats["total_urls_processed"] += 1
                aggregated_stats["total_jobs_found"] += url_stats.get("jobs_found", 0)
                aggregated_stats["total_jobs_duplicate"] += url_stats.get("jobs_duplicate", 0)  # Add duplicate stats
                aggregated_stats["total_jobs_detailed"] += url_stats.get("jobs_detailed", 0)
                aggregated_stats["total_jobs_filtered_out"] += url_stats.get("jobs_filtered_out", 0)
                aggregated_stats["total_jobs_kept"] += url_stats.get("jobs_kept", 0)
                aggregated_stats["total_jobs_stored_attempts"] += url_stats.get("jobs_stored_attempts", 0)
                aggregated_stats["total_errors"] += url_stats.get("errors", 0)

            except Exception as e:
                logger.critical(f"FATAL: Uncaught exception in process_urls loop for URL {url}: {e}", exc_info=True)
                aggregated_stats["total_errors"] += 1
                self.event_bus.publish(PIPELINE_ERROR, error=f"Critical loop error: {str(e)}", url=url, stage="batch_url_processing_loop")

        logger.info(f"Finished processing all URLs. Aggregated stats: {aggregated_stats}")
        self.event_bus.publish(PIPELINE_COMPLETED, **aggregated_stats)
        return aggregated_stats

