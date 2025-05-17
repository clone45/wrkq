from typing import Optional, Dict, Any
from dataclasses import dataclass
from .job_state import JobState, JobStatus

@dataclass
class PostProcessorOptions:
    """Configuration options for job postprocessing"""
    required_fields: list[str] = None  # Fields that must be present in detailed data
    min_description_length: Optional[int] = None
    max_description_length: Optional[int] = None
    validate_urls: bool = True
    clean_html: bool = True

class PostProcessorInterface:
    """Interface for postprocessing jobs after detail fetching"""
    
    def process(self, job_state: JobState, options: Optional[PostProcessorOptions] = None) -> JobState:
        """
        Process a job state after details have been fetched
        
        Args:
            job_state: Current job state
            options: Processing options
            
        Returns:
            Updated job state (may be marked as filtered)
            
        This stage handles:
        - Validation of detailed data
        - Content cleaning (HTML, formatting)
        - Advanced filtering based on full job details
        - Data enrichment/normalization
        """
        raise NotImplementedError("Subclasses must implement process")
    
    def should_process_job(self, job_state: JobState) -> bool:
        """
        Quick check if a job should be processed
        
        Args:
            job_state: Current job state
            
        Returns:
            True if job should be processed, False otherwise
        """
        return job_state.status == JobStatus.DETAILS_PENDING
        
    def clean_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize job data
        
        Args:
            job_data: Raw job data
            
        Returns:
            Cleaned job data
        """
        raise NotImplementedError("Subclasses must implement clean_job_data") 