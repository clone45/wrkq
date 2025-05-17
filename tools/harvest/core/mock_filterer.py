# harvest/core/mock_filterer.py

import time
import random
import logging
from typing import List, Dict, Any, Optional, Tuple

from ..interfaces.filterer import FiltererInterface, FilterOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import EventType
# from ..errors import ConfigError

logger = logging.getLogger(__name__)

class MockFilterer(FiltererInterface):
    """Mock implementation of FiltererInterface for testing."""
    
    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        self.filtered_jobs = []
        self.kept_jobs = []
        logger.info("MockFilterer initialized")

    def filter_jobs(self, jobs: List[Dict[str, Any]], options: FilterOptions = None) -> List[Tuple[Dict[str, Any], str]]:
        """Mock filtering jobs."""
        filtered_results = []
        
        for job in jobs:
            # Mock filtering logic - filter jobs with 'filter' in title
            title = job.get('title', '').lower()
            if 'filter' in title:
                reason = "Title contains 'filter'"
                self.filtered_jobs.append((job, reason))
                filtered_results.append((job, reason))
                self.event_bus.publish(EventType.JOB_FILTERED, reason=reason, **job)
            else:
                self.kept_jobs.append(job)
                self.event_bus.publish(EventType.JOB_KEPT, **job)
                
        return filtered_results

    def filter_job_batch(self, jobs: List[Dict[str, Any]], options: Optional[FilterOptions] = None) -> List[Dict[str, Any]]:
        logger.info(f"MockFilterer: Starting to filter {len(jobs)} jobs with options: {options}")
        
        kept_jobs: List[Dict[str, Any]] = []
        
        # Example: simple title filter from options (if options were more complex)
        # title_blacklist = []
        # if options and options.title_filters_path:
        #     logger.debug(f"MockFilterer: Would load title filters from {options.title_filters_path}")
            # title_blacklist = ["Intern", "Junior"] # Simulate loading

        for job in jobs:
            time.sleep(0.05) # Simulate quick processing
            job_title = job.get('title', '').lower()
            reason = None

            # Simple mock filtering logic
            if "junior" in job_title or "intern" in job_title:
                reason = "Title contains 'junior' or 'intern' (mock filter)"
            elif random.random() < 0.15: # 15% chance of being randomly filtered
                reason = "Randomly filtered by mock logic"
            
            if reason:
                logger.debug(f"MockFilterer: Filtering out job ID '{job.get('job_id', 'N/A')}' - Reason: {reason}")
                self.event_bus.publish(EventType.JOB_FILTERED, reason=reason, **job)
            else:
                logger.debug(f"MockFilterer: Keeping job ID '{job.get('job_id', 'N/A')}'")
                self.event_bus.publish(EventType.JOB_KEPT, **job)
                kept_jobs.append(job)
        
        logger.info(f"MockFilterer: Filtering completed. Kept {len(kept_jobs)} out of {len(jobs)} jobs.")
        return kept_jobs