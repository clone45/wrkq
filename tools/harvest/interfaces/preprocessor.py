from typing import Optional, Dict, Any
from dataclasses import dataclass
from .job_state import JobState, JobStatus

@dataclass
class PreProcessorOptions:
    """Configuration options for job preprocessing"""
    title_filters_path: Optional[str] = None
    company_filters_path: Optional[str] = None
    max_age_hours: Optional[int] = None
    check_duplicates: bool = True

class PreProcessorInterface:
    """Interface for preprocessing jobs before detail fetching"""
    
    def process(self, job_state: JobState, options: Optional[PreProcessorOptions] = None) -> JobState:
        """
        Process a job state, potentially filtering it based on basic criteria
        
        Args:
            job_state: Current job state
            options: Processing options
            
        Returns:
            Updated job state (may be marked as filtered)
            
        This stage handles:
        - Basic validation of required fields
        - Title/company filtering
        - Age filtering
        - Deduplication checks
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
        return job_state.status == JobStatus.NEW
        
    def get_duplicate_status(self, job_data: Dict[str, Any]) -> Optional[str]:
        """
        Check if job already exists in database
        
        Args:
            job_data: Job data to check
            
        Returns:
            None if not duplicate, reason string if duplicate
        """
        raise NotImplementedError("Subclasses must implement get_duplicate_status") 