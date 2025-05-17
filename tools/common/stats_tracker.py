"""
Centralized statistics tracking for the job harvesting system.
"""

import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class JobStats:
    """Statistics about job processing"""
    # Job counts
    jobs_found: int = 0
    jobs_filtered_out: int = 0
    jobs_stored: int = 0
    jobs_duplicate: int = 0
    jobs_failed: int = 0
    jobs_remaining: int = 0
    
    # URL tracking
    urls_processed: int = 0
    urls_total: int = 0
    urls_failed: int = 0
    current_url: str = ""
    
    # Current state
    current_job: str = ""
    status_message: str = ""
    
    # Error tracking
    errors: int = 0
    
    # Timing
    start_time: float = 0.0
    
    def calculate_remaining(self) -> None:
        """Calculate jobs remaining after filtering"""
        self.jobs_remaining = self.jobs_found - self.jobs_filtered_out
        logger.debug(f"Recalculated remaining jobs: {self.jobs_remaining} "
                    f"(Found: {self.jobs_found} - Filtered: {self.jobs_filtered_out})")

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary format"""
        return asdict(self)

class StatsTracker:
    """
    Centralized statistics tracking for the job harvesting system.
    Maintains a single source of truth for all job processing statistics.
    """
    
    def __init__(self):
        """Initialize the stats tracker with default values"""
        self._stats = JobStats()
        self._stats.start_time = time.time()
        logger.info("StatsTracker initialized")
        
    @property
    def stats(self) -> JobStats:
        """Get the current stats object"""
        return self._stats
        
    def update(self, **kwargs: Any) -> None:
        """
        Update statistics with new values.
        
        Args:
            **kwargs: Key-value pairs to update in the stats
        """
        for key, value in kwargs.items():
            if hasattr(self._stats, key):
                old_value = getattr(self._stats, key)
                setattr(self._stats, key, value)
                logger.debug(f"Updated stat {key}: {old_value} -> {value}")
            else:
                logger.warning(f"Attempted to update non-existent stat: {key}")
        
        # Recalculate dependent values
        if any(k in kwargs for k in ['jobs_found', 'jobs_filtered_out']):
            self._stats.calculate_remaining()
            
    def increment(self, stat_name: str, amount: int = 1) -> None:
        """
        Increment a numeric statistic.
        
        Args:
            stat_name: Name of the statistic to increment
            amount: Amount to increment by (default: 1)
        """
        if hasattr(self._stats, stat_name):
            old_value = getattr(self._stats, stat_name)
            new_value = old_value + amount
            setattr(self._stats, stat_name, new_value)
            logger.debug(f"Incremented {stat_name}: {old_value} -> {new_value}")
            
            # Recalculate dependent values
            if stat_name in ['jobs_found', 'jobs_filtered_out']:
                self._stats.calculate_remaining()
        else:
            logger.warning(f"Attempted to increment non-existent stat: {stat_name}")
            
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds since tracking started"""
        return time.time() - self._stats.start_time
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a dictionary of current statistics for reporting"""
        return {
            "urls": {
                "processed": self._stats.urls_processed,
                "total": self._stats.urls_total,
                "failed": self._stats.urls_failed
            },
            "jobs": {
                "found": self._stats.jobs_found,
                "filtered": self._stats.jobs_filtered_out,
                "stored": self._stats.jobs_stored,
                "duplicate": self._stats.jobs_duplicate,
                "failed": self._stats.jobs_failed,
                "remaining": self._stats.jobs_remaining
            },
            "errors": self._stats.errors,
            "elapsed_time": self.get_elapsed_time()
        } 