# harvest/core/mock_storer.py

import time
import random
import logging
from typing import List, Dict, Any, Optional, Tuple

from ..interfaces.storer import StorerInterface, StorageOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import JOB_BASIC_STORED, JOB_DETAILS_STORED, STORAGE_ERROR, JOB_MARKED_FILTERED
# from ..errors import DatabaseError # Example

logger = logging.getLogger(__name__)

class MockStorer(StorerInterface):

    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        self.stored_job_ids = set()
        logger.info("MockStorer initialized")

    def store_job_batch(self, jobs: List[Dict[str, Any]], options: Optional[StorageOptions] = None) -> None:
        db_path = options.database_path if options and options.database_path else "mock_db.sqlite"
        logger.info(f"MockStorer: Starting to store a batch of {len(jobs)} jobs. Target DB: '{db_path}' Options: {options}")

        for job in jobs:
            job_id = job.get('job_id')
            if not job_id:
                logger.warning("MockStorer: Job missing job_id, cannot store.")
                self.event_bus.publish(STORAGE_ERROR, error="Job missing job_id", job_id=None, title=job.get('title'))
                continue

            time.sleep(0.1) # Simulate DB write

            # Simulate occasional storage error
            if random.random() < 0.02: # 2% chance of error per job
                error_message = f"Simulated DB connection issue for job ID {job_id}"
                logger.warning(f"MockStorer: Simulating storage error: {error_message}")
                self.event_bus.publish(STORAGE_ERROR, error=error_message, job_id=job_id, title=job.get('title'))
                # Optionally raise DatabaseError(error_message)
                continue

            # Simulate basic info stored
            self.event_bus.publish(JOB_BASIC_STORED, **job) # Pass full job data for simplicity
            self.stored_job_ids.add(job_id)
            logger.debug(f"MockStorer: Stored basic info for job ID '{job_id}'")

            # Simulate details stored if description is present (as a proxy for detailed job)
            if job.get('description'):
                time.sleep(0.05)
                self.event_bus.publish(JOB_DETAILS_STORED, **job)
                logger.debug(f"MockStorer: Stored details for job ID '{job_id}'")
        
        logger.info(f"MockStorer: Finished storing batch. Attempted {len(jobs)}, 'successfully' stored {len(self.stored_job_ids)} (mock count).")

    def mark_filtered_jobs_batch(self, filtered_job_info: List[Tuple[str, str]], options: Optional[StorageOptions] = None) -> None:
        logger.info(f"MockStorer: Marking {len(filtered_job_info)} jobs as filtered. Options: {options}")
        for job_id, reason in filtered_job_info:
            time.sleep(0.02)
            logger.debug(f"MockStorer: Marking job ID '{job_id}' as filtered. Reason: '{reason}'")
            self.event_bus.publish(JOB_MARKED_FILTERED, job_id=job_id, reason=reason) # Ensure event matches handler
        logger.info(f"MockStorer: Finished marking filtered jobs.")