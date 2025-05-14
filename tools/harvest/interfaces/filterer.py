      
# harvest/interfaces/filterer.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class FilterOptions:
    """Configuration options for job filtering."""
    title_filters_path: str = None
    company_filters_path: str = None
    max_age_hours: Optional[int] = None # Example: filter out jobs older than X hours
    
class FiltererInterface:
    """Interface for filtering job listings."""

    def filter_job_batch(self, jobs: List[Dict[str, Any]], options: FilterOptions = None) -> List[Dict[str, Any]]:
        """
        Filters a batch of jobs.
        The implementation should iterate through jobs, use its internal logic
        (potentially calling internal should_keep/get_filter_reason), publish
        JOB_KEPT or JOB_FILTERED (with reason) events for each job, and
        return the list of jobs that should be kept.

        Args:
            jobs: List of job dictionaries to evaluate.
            options: Filtering configuration options.

        Returns:
            List of job dictionaries that should be kept.

        Raises:
            ConfigError: If filter configuration is invalid (ensure this is from harvest.errors)
            # Individual job processing errors (e.g., missing key) should be handled gracefully,
            # possibly by filtering out the problematic job and logging/publishing an event.
        """
        raise NotImplementedError("Subclasses must implement this method")

    # Internal helper methods, not directly called by pipeline but used by filter_job_batch
    # def should_keep(self, job: Dict[str, Any], options: FilterOptions = None) -> bool:
    #     """
    #     Determine if a job should be kept or filtered out. (Internal use)
    #     """
    #     raise NotImplementedError("Subclasses must implement this method")
        
    # def get_filter_reason(self, job: Dict[str, Any], options: FilterOptions = None) -> Optional[str]:
    #     """
    #     Get the reason a job was filtered out. (Internal use)
    #     """
    #     raise NotImplementedError("Subclasses must implement this method")

    