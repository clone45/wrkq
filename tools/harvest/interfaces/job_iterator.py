from typing import Iterator, Dict, Any, Optional
from dataclasses import dataclass
from .job_state import JobState

@dataclass
class JobIteratorOptions:
    """Configuration options for job iteration"""
    batch_size: int = 50
    max_retries: int = 3
    retry_delay: float = 60.0  # seconds

class JobIteratorInterface:
    """Interface for iterating over jobs from a search result"""
    
    def __iter__(self) -> Iterator[JobState]:
        """Return iterator over jobs"""
        raise NotImplementedError("Subclasses must implement __iter__")
        
    def __next__(self) -> JobState:
        """Get next job state"""
        raise NotImplementedError("Subclasses must implement __next__")
    
    def mark_job_processed(self, job_state: JobState) -> None:
        """Mark a job as processed to avoid reprocessing"""
        raise NotImplementedError("Subclasses must implement mark_job_processed")
    
    def get_progress(self) -> Dict[str, Any]:
        """Get progress information about the iteration"""
        raise NotImplementedError("Subclasses must implement get_progress") 