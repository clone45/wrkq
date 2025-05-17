# File: harvest/core/pipeline.py

import logging
from typing import List, Dict, Any, Optional

from ..interfaces.pipeline import PipelineInterface, PipelineConfig
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..interfaces.searcher import SearcherInterface
from ..interfaces.detailer import DetailerInterface
from ..interfaces.storer import StorerInterface
from ..events import EventType
from ..errors import HarvestError, NetworkError, ParseError, AuthenticationError, DatabaseError, ConfigError
from ..interfaces.job_state import JobStatus
from ..interfaces.job_iterator import JobIteratorInterface, JobIteratorOptions
from ..interfaces.preprocessor import PreProcessorInterface
from ..interfaces.postprocessor import PostProcessorInterface

logger = logging.getLogger(__name__)

class Pipeline(PipelineInterface):
    """
    Core implementation of the job processing pipeline.
    Orchestrates search, detail fetching, filtering, and storage.
    """

    def __init__(self,
                 event_bus: EventBusInterface,
                 searcher: SearcherInterface,
                 job_iterator: JobIteratorInterface,
                 preprocessor: PreProcessorInterface,
                 detailer: DetailerInterface,
                 postprocessor: PostProcessorInterface,
                 storer: StorerInterface,
                 default_config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline.
        """
        self.event_bus = event_bus
        self.searcher = searcher
        self.job_iterator = job_iterator
        self.preprocessor = preprocessor
        self.detailer = detailer
        self.postprocessor = postprocessor
        self.storer = storer
        self.default_config = default_config
        self.stats = {
            "jobs_found": 0,
            "jobs_filtered_pre": 0,
            "jobs_detailed": 0,
            "jobs_filtered_post": 0,
            "jobs_stored": 0,
            "jobs_failed": 0,
            "jobs_duplicate": 0
        }
        logger.info("Core Pipeline initialized.")

    def _get_effective_config(self, config_override: Optional[PipelineConfig]) -> Optional[PipelineConfig]:
        """Helper to determine which config to use."""
        if config_override is not None:
            return config_override
        if self.default_config is not None:
            return self.default_config
        return None

    def _process_jobs_through_pipeline(self, config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """Internal helper to process jobs through the pipeline stages."""
        stats = {
            "jobs_found": 0,
            "jobs_filtered_pre": 0,
            "jobs_detailed": 0,
            "jobs_filtered_post": 0,
            "jobs_stored": 0,
            "jobs_failed": 0,
            "jobs_duplicate": 0,
            "errors": 0
        }

        logger.info(f"Starting to process {self.job_iterator.total_jobs} jobs through pipeline")
        
        for job_state in self.job_iterator:
            stats["jobs_found"] += 1
            job_id = job_state.job_id
            logger.info(f"Processing job {job_id} (Status: {job_state.status})")
            self.event_bus.publish(EventType.JOB_FOUND, job_id=job_id)
            
            try:
                # Preprocessing (includes duplicate check)
                if self.preprocessor.should_process_job(job_state):
                    logger.info(f"Job {job_id}: Starting preprocessing")
                    job_state = self.preprocessor.process(
                        job_state,
                        config.preprocessor_options if config else None
                    )
                    logger.info(f"Job {job_id}: Preprocessing complete, new status: {job_state.status}")
                    
                    if job_state.status == JobStatus.FILTERED_PRE:
                        stats["jobs_filtered_pre"] += 1
                        if "Duplicate" in job_state.filter_reason:
                            stats["jobs_duplicate"] += 1
                            logger.info(f"Job {job_id}: Found duplicate - {job_state.filter_reason}")
                            self.event_bus.publish(
                                EventType.JOB_DUPLICATE_FOUND,
                                job_id=job_id,
                                reason=job_state.filter_reason,
                                title=job_state.data.get("title"),
                                company=job_state.data.get("company")
                            )
                        else:
                            logger.info(f"Job {job_id}: Filtered in preprocessing - {job_state.filter_reason}")
                            # Publish JOB_FILTERED event for UI stats tracking
                            self.event_bus.publish(
                                EventType.JOB_FILTERED,
                                job_id=job_id,
                                reason=job_state.filter_reason,
                                title=job_state.data.get("title"),
                                company=job_state.data.get("company")
                            )
                        self.event_bus.publish(
                            EventType.JOB_FILTERED_PRE,
                            job_id=job_id,
                            reason=job_state.filter_reason
                        )
                        continue
                        
                    if job_state.status == JobStatus.FAILED:
                        stats["jobs_failed"] += 1
                        logger.info(f"Job {job_id}: Failed in preprocessing - {job_state.error_message}")
                        self.event_bus.publish(
                            EventType.JOB_FAILED,
                            job_id=job_id,
                            error=job_state.error_message
                        )
                        continue
                else:
                    logger.info(f"Job {job_id}: Skipping preprocessing, status: {job_state.status}")
                
                # Detail fetching
                if job_state.status == JobStatus.NEW:
                    logger.info(f"Job {job_id}: Starting detail fetch")
                    try:
                        detailed_data = self.detailer.fetch_details_batch(
                            [job_state.data],
                            config.detail_options if config else None
                        )[0]  # Get first result since we're processing one at a time
                        job_state.data.update(detailed_data)
                        job_state.mark_details_fetched()
                        stats["jobs_detailed"] += 1
                        logger.info(f"Job {job_id}: Detail fetch complete")
                    except Exception as e:
                        job_state.mark_failed(str(e), "detail_fetch")
                        stats["jobs_failed"] += 1
                        logger.error(f"Job {job_id}: Failed to fetch details - {str(e)}")
                        self.event_bus.publish(
                            EventType.JOB_FAILED,
                            job_id=job_id,
                            error=str(e)
                        )
                        continue
                else:
                    logger.info(f"Job {job_id}: Skipping detail fetch, status: {job_state.status}")
                
                # Postprocessing
                if self.postprocessor.should_process_job(job_state):
                    logger.info(f"Job {job_id}: Starting postprocessing")
                    job_state = self.postprocessor.process(
                        job_state,
                        config.postprocessor_options if config else None
                    )
                    logger.info(f"Job {job_id}: Postprocessing complete, new status: {job_state.status}")
                    
                    if job_state.status == JobStatus.FILTERED_POST:
                        stats["jobs_filtered_post"] += 1
                        logger.info(f"Job {job_id}: Filtered in postprocessing - {job_state.filter_reason}")
                        self.event_bus.publish(
                            EventType.JOB_FILTERED_POST,
                            job_id=job_id,
                            reason=job_state.filter_reason
                        )
                        continue
                        
                    if job_state.status == JobStatus.FAILED:
                        stats["jobs_failed"] += 1
                        logger.info(f"Job {job_id}: Failed in postprocessing - {job_state.error_message}")
                        self.event_bus.publish(
                            EventType.JOB_FAILED,
                            job_id=job_id,
                            error=job_state.error_message
                        )
                        continue
                else:
                    logger.info(f"Job {job_id}: Skipping postprocessing, status: {job_state.status}")
                
                # Storage
                if job_state.status == JobStatus.DETAILS_PENDING:
                    logger.info(f"Job {job_id}: Starting storage")
                    try:
                        self.storer.store_job_batch(
                            [job_state.data],
                            config.storage_options if config else None
                        )
                        stats["jobs_stored"] += 1
                        logger.info(f"Job {job_id}: Storage complete")
                        self.event_bus.publish(EventType.JOB_STORED, job_id=job_id)
                    except Exception as e:
                        job_state.mark_failed(str(e), "storage")
                        stats["jobs_failed"] += 1
                        logger.error(f"Job {job_id}: Failed to store - {str(e)}")
                        self.event_bus.publish(
                            EventType.STORAGE_ERROR,
                            job_id=job_id,
                            error=str(e)
                        )
                        continue
                else:
                    logger.info(f"Job {job_id}: Skipping storage, status: {job_state.status}")

            except Exception as e:
                stats["jobs_failed"] += 1
                logger.error(f"Job {job_id}: Unexpected error - {str(e)}")
                self.event_bus.publish(
                    EventType.JOB_FAILED,
                    job_id=job_id,
                    error=str(e)
                )

        return stats

    def process_url(self, url: str, config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """Process a single URL through the pipeline."""
        logger.info(f"Starting to process URL: {url}")
        self.event_bus.publish(EventType.URL_PROCESSING_STARTED, url=url)
        
        url_stats = {
            "jobs_found": 0,
            "jobs_filtered_pre": 0,
            "jobs_detailed": 0,
            "jobs_filtered_post": 0,
            "jobs_stored": 0,
            "jobs_failed": 0,
            "jobs_duplicate": 0,
            "errors": 0
        }
        
        try:
            # Search for jobs
            found_jobs = self.searcher.search(url, config.search_options if config else None)
            url_stats["jobs_found"] = len(found_jobs)
            
            # Process found jobs through pipeline
            job_stats = self.process_jobs(found_jobs, config)
            url_stats.update(job_stats)
            
        except AuthenticationError as ae:
            logger.error(f"Authentication error processing URL '{url}': {ae}")
            self.event_bus.publish(EventType.PIPELINE_ERROR, error=str(ae), url=url, stage="url_processing", error_type="AuthenticationError")
            url_stats["errors"] += 1
        except NetworkError as ne:
            logger.error(f"Network error processing URL '{url}': {ne}")
            self.event_bus.publish(EventType.PIPELINE_ERROR, error=str(ne), url=url, stage="url_processing", error_type="NetworkError")
            url_stats["errors"] += 1
        except ParseError as pe:
            logger.error(f"Parse error processing URL '{url}': {pe}")
            self.event_bus.publish(EventType.PIPELINE_ERROR, error=str(pe), url=url, stage="url_processing", error_type="ParseError")
            url_stats["errors"] += 1
        except DatabaseError as dbe:
            logger.error(f"Database error processing URL '{url}': {dbe}")
            self.event_bus.publish(EventType.PIPELINE_ERROR, error=str(dbe), url=url, stage="url_processing", error_type="DatabaseError")
            url_stats["errors"] += 1
        except ConfigError as ce:
            logger.error(f"Configuration error processing URL '{url}': {ce}")
            self.event_bus.publish(EventType.PIPELINE_ERROR, error=str(ce), url=url, stage="url_processing", error_type="ConfigError")
            url_stats["errors"] += 1
        except HarvestError as he:
            logger.error(f"Harvest error processing URL '{url}': {he}")
            self.event_bus.publish(EventType.PIPELINE_ERROR, error=str(he), url=url, stage="url_processing", error_type=type(he).__name__)
            url_stats["errors"] += 1
        except Exception as e:
            logger.error(f"Unexpected error processing URL '{url}': {e}", exc_info=True)
            self.event_bus.publish(EventType.PIPELINE_ERROR, error=f"Unexpected: {str(e)}", url=url, stage="url_processing", error_type="CriticalError")
            url_stats["errors"] += 1
            
        self.event_bus.publish(EventType.URL_PROCESSING_COMPLETED, url=url, **url_stats)
        return url_stats

    def process_urls(self, urls: List[str], config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """Process multiple URLs through the pipeline."""
        logger.info(f"Starting to process {len(urls)} URLs")
        self.event_bus.publish(EventType.PIPELINE_STARTED, url_count=len(urls))
        
        aggregated_stats = {
            "jobs_found": 0,
            "jobs_filtered_pre": 0,
            "jobs_detailed": 0,
            "jobs_filtered_post": 0,
            "jobs_stored": 0,
            "jobs_failed": 0,
            "jobs_duplicate": 0,
            "errors": 0,
            "urls_processed": 0,
            "urls_failed": 0
        }
        
        for url in urls:
            try:
                url_stats = self.process_url(url, config)
                for key in url_stats:
                    if key in aggregated_stats:
                        aggregated_stats[key] += url_stats[key]
                aggregated_stats["urls_processed"] += 1
            except Exception as e:
                logger.error(f"Critical error in URL processing loop for '{url}': {e}", exc_info=True)
                self.event_bus.publish(EventType.PIPELINE_ERROR, error=f"Critical loop error: {str(e)}", url=url, stage="batch_url_processing_loop")
                aggregated_stats["urls_failed"] += 1
                
        self.event_bus.publish(EventType.PIPELINE_COMPLETED, **aggregated_stats)
        return aggregated_stats

    def process_jobs(self, jobs: List[Dict[str, Any]], config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """Process a list of jobs through the pipeline."""
        try:
            # Reset the job iterator with the new jobs
            self.job_iterator.reset(jobs)
            return self._process_jobs_through_pipeline(config)
        except Exception as e:
            logger.error(f"Critical error in job processing: {e}", exc_info=True)
            self.event_bus.publish(EventType.JOB_FAILED, error=str(e))
            return {"jobs_failed": 1, "errors": 1}

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get current pipeline statistics."""
        return self.stats.copy()

