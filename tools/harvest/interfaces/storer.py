      
# harvest/interfaces/storer.py

from typing import Dict, Any, List, Tuple, Optional # Tuple not used in this version
from dataclasses import dataclass

@dataclass
class StorageOptions:
    """Configuration options for job storage."""
    database_path: str # Made mandatory for this example, adjust if it can be optional
    update_existing: bool = True
    batch_size: int = 50 # Could be used by implementation for batch DB operations
    
class StorerInterface:
    """Interface for storing jobs in a database."""

    def store_job_batch(self, jobs: List[Dict[str, Any]], options: StorageOptions = None) -> None:
        """
        Store a batch of jobs (basic and detailed information).
        The implementation should iterate through jobs, store them, and publish
        JOB_BASIC_STORED, JOB_DETAILS_STORED, or STORAGE_ERROR events accordingly.

        Args:
            jobs: List of job dictionaries to store. These jobs are expected
                  to be the final "kept" jobs, potentially with details.
            options: Storage configuration options.
            
        Returns:
            None. Success/failure per job is indicated via events.
            
        Raises:
            DatabaseError: For critical database issues affecting the batch (e.g., connection).
                           Individual job storage errors should publish STORAGE_ERROR.
            ConfigError: If storage configuration (like database_path) is missing or invalid.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def mark_filtered_jobs_batch(self, filtered_job_info: List[Tuple[str, str]], options: StorageOptions = None) -> None:
        """
        Mark a batch of jobs as filtered out in the database.
        This is useful if the pipeline first identifies jobs to filter, then tells the storer.

        Args:
            filtered_job_info: A list of tuples, where each tuple is (job_id, reason).
            options: Storage configuration options.

        Returns:
            None.

        Raises:
            DatabaseError: For critical database issues.
        """
        raise NotImplementedError("Subclasses must implement this method")


    # The more granular methods can remain as internal helpers or for specific use cases,
    # but the pipeline would primarily call store_job_batch and potentially mark_filtered_jobs_batch.
    # def store_basic_job_internal(self, job: Dict[str, Any], options: StorageOptions = None) -> Optional[str]:
    #     raise NotImplementedError
        
    # def update_job_details_internal(self, job_id: str, job: Dict[str, Any], options: StorageOptions = None) -> bool:
    #     raise NotImplementedError
        
    # def mark_single_job_filtered_internal(self, job_id: str, reason: str, options: StorageOptions = None) -> bool:
    #     raise NotImplementedError

    