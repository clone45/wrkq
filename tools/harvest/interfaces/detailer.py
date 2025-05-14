      
# harvest/interfaces/detailer.py

from typing import Dict, Any, Optional, List # Added List
from dataclasses import dataclass

@dataclass
class DetailOptions:
    """Configuration options for job detail fetching."""
    cookie_file: str = None
    output_dir: str = None # Similar note as SearchOptions.output_dir
    delay_between_requests: float = 3.0
    
class DetailerInterface:
    """Interface for fetching detailed job information."""
    
    def fetch_details_batch(self, jobs: List[Dict[str, Any]], options: DetailOptions = None) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for a batch of jobs.
        The implementation should handle publishing DETAIL_FETCHING_STARTED, 
        JOB_DETAILS_FETCHED (for each job with index/total), and DETAIL_FETCHING_COMPLETED events.
        
        Args:
            jobs: List of job dictionaries, each requiring at least 'url' or 'job_id'.
            options: Detail fetching configuration options
            
        Returns:
            List of job dictionaries, updated with detailed information where fetched.
            Jobs that failed fetching might be returned without new details or omitted,
            depending on implementation strategy.
            
        Raises:
            NetworkError: If there's a general network issue for many jobs (ensure this is from harvest.errors)
            AuthenticationError: If cookies are invalid or expired (ensure this is from harvest.errors)
            # Individual job fetch errors should ideally be handled internally, 
            # publishing DETAIL_ERROR, and the job returned with original data or marked.
        """
        raise NotImplementedError("Subclasses must implement this method")

    # You might keep a single-job fetch method for other purposes or testing,
    # but the pipeline will primarily use the batch method.
    # def get_details_for_single_job(self, job: Dict[str, Any], options: DetailOptions = None) -> Dict[str, Any]:
    #     """
    #     Fetch detailed information for a single job.
    #     (This would typically be called by fetch_details_batch or used independently)
    #     """
    #     raise NotImplementedError("Subclasses must implement this method")

    