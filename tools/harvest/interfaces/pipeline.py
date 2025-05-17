# harvest/interfaces/pipeline.py

from typing import List, Dict, Any, Optional
from .job_state import JobState, JobStatus
from .event_bus import EventBus
from .searcher import SearcherInterface, SearchOptions
from .detailer import DetailerInterface, DetailOptions
from .storer import StorerInterface, StorageOptions
from .preprocessor import PreProcessorInterface, PreProcessorOptions
from .postprocessor import PostProcessorInterface, PostProcessorOptions
from .job_iterator import JobIteratorOptions
from dataclasses import dataclass

@dataclass
class PipelineConfig:
    """Configuration for the job processing pipeline"""
    search_options: Optional[SearchOptions] = None
    detail_options: Optional[DetailOptions] = None
    storage_options: Optional[StorageOptions] = None
    preprocessor_options: Optional[PreProcessorOptions] = None
    postprocessor_options: Optional[PostProcessorOptions] = None
    iterator_options: Optional[JobIteratorOptions] = None

class PipelineInterface:
    """Interface for the job processing pipeline"""
    
    def process_url(self, url: str, config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """
        Process a single search URL
        
        Args:
            url: Search URL to process
            config: Pipeline configuration
            
        Returns:
            Statistics about processed jobs
            
        The pipeline follows these steps for each job:
        1. Get jobs from search URL via JobIterator
        2. For each job:
           a. Preprocess (filter/dedup)
           b. Fetch details if passed preprocessing
           c. Postprocess with full details
           d. Store if passed all stages
        """
        raise NotImplementedError("Subclasses must implement process_url")
    
    def process_jobs(self, jobs: List[Dict[str, Any]], config: Optional[PipelineConfig] = None) -> Dict[str, int]:
        """
        Process a list of jobs directly (bypass search)
        
        Args:
            jobs: List of jobs to process
            config: Pipeline configuration
            
        Returns:
            Statistics about processed jobs
        """
        raise NotImplementedError("Subclasses must implement process_jobs")
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics about pipeline processing"""
        raise NotImplementedError("Subclasses must implement get_pipeline_stats")