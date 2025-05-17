import logging
from typing import Iterator, Dict, Any, List, Set
from ..interfaces.job_iterator import JobIteratorInterface, JobIteratorOptions
from ..interfaces.job_state import JobState, JobStatus
from ..errors import HarvestError

logger = logging.getLogger(__name__)

class JobIterator(JobIteratorInterface):
    """Concrete implementation of job iterator"""
    
    def __init__(self, jobs: List[Dict[str, Any]], options: JobIteratorOptions = None):
        self.jobs = jobs
        self.options = options or JobIteratorOptions()
        self.current_index = 0
        self.processed_jobs: Set[str] = set()
        self.total_jobs = len(jobs)
        self.progress = {
            "total": self.total_jobs,
            "processed": 0,
            "remaining": self.total_jobs
        }
        logger.info(f"JobIterator initialized with {self.total_jobs} jobs")
        
    def __iter__(self) -> Iterator[JobState]:
        """Return self as iterator"""
        return self
        
    def __next__(self) -> JobState:
        """Get next unprocessed job"""
        while self.current_index < self.total_jobs:
            job_data = self.jobs[self.current_index]
            self.current_index += 1
            
            # Skip if already processed
            job_id = job_data.get("job_id") or str(job_data.get("id")) or str(self.current_index)
            if job_id in self.processed_jobs:
                continue
                
            # Create new job state
            return JobState(
                job_id=job_id,
                status=JobStatus.NEW,
                data=job_data
            )
            
        raise StopIteration()
        
    def mark_job_processed(self, job_state: JobState) -> None:
        """Mark a job as processed"""
        self.processed_jobs.add(job_state.job_id)
        self.progress["processed"] += 1
        self.progress["remaining"] = self.total_jobs - self.progress["processed"]
        logger.debug(f"Marked job {job_state.job_id} as processed. Progress: {self.progress}")
        
    def get_progress(self) -> Dict[str, Any]:
        """Get progress information"""
        return self.progress.copy() 
        
    def reset(self, jobs: List[Dict[str, Any]]) -> None:
        """Reset the iterator with new jobs."""
        self.jobs = jobs
        self.current_index = 0
        self.processed_jobs.clear()
        self.total_jobs = len(jobs)
        self.progress = {
            "total": self.total_jobs,
            "processed": 0,
            "remaining": self.total_jobs
        }
        logger.info(f"JobIterator reset with {self.total_jobs} jobs") 