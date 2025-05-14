# harvest/core/mock_detailer.py

import time
import random
import logging
from typing import List, Dict, Any, Optional

from ..interfaces.detailer import DetailerInterface, DetailOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import DETAIL_FETCHING_STARTED, JOB_DETAILS_FETCHED, DETAIL_FETCHING_COMPLETED, DETAIL_ERROR
# from ..errors import ParseError # Example

logger = logging.getLogger(__name__)

class MockDetailer(DetailerInterface):

    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        logger.info("MockDetailer initialized")

    def fetch_details_batch(self, jobs: List[Dict[str, Any]], options: Optional[DetailOptions] = None) -> List[Dict[str, Any]]:
        delay = options.delay_between_requests if options and options.delay_between_requests else 0.2

        logger.info(f"MockDetailer: Starting to fetch details for {len(jobs)} jobs with options: {options}")
        self.event_bus.publish(DETAIL_FETCHING_STARTED, job_count=len(jobs))
        
        detailed_jobs: List[Dict[str, Any]] = []
        total_jobs = len(jobs)

        for i, job in enumerate(jobs):
            logger.debug(f"MockDetailer: Fetching details for job ID '{job.get('job_id', 'N/A')}' ({i+1}/{total_jobs})")
            time.sleep(delay)
            
            # Simulate a random detail fetching error occasionally
            if random.random() < 0.03 and job.get('job_id'): # 3% chance of error
                error_message = "Simulated random parsing issue for job details"
                logger.warning(f"MockDetailer: Simulating detail error for job ID {job['job_id']}: {error_message}")
                self.event_bus.publish(DETAIL_ERROR, 
                                       error=error_message, 
                                       job_id=job['job_id'], 
                                       title=job.get('title', 'N/A'))
                # Optionally raise ParseError(error_message)
                detailed_jobs.append(job) # Return original job if details fail
                continue

            # Create a copy to modify
            updated_job = job.copy()
            updated_job.update({
                "description": f"This is a **detailed mock description** for {updated_job.get('title', 'this job')}. "
                               f"It requires skills in mocking and testing. The company, {updated_job.get('company', 'Our Company')}, "
                               "is a leader in simulated experiences.",
                "employment_type": random.choice(["Full-time", "Contract", "Part-time Mock"]),
                "experience_level": random.choice(["Entry Mock", "Mid-Senior Mock", "Lead Mock"]),
                "salary_info": f"${random.randint(50, 150)}k - ${random.randint(150, 250)}k (Simulated)",
                "skills_required": ["Mocking", "Python", "Testing", random.choice(["Rich", "FastAPI", "Django"])]
            })
            
            detailed_jobs.append(updated_job)
            self.event_bus.publish(JOB_DETAILS_FETCHED, index=i, total=total_jobs, **updated_job)
            logger.debug(f"MockDetailer: Fetched details for job ID '{updated_job['job_id']}'")

        logger.info(f"MockDetailer: Detail fetching completed for {len(jobs)} jobs.")
        self.event_bus.publish(DETAIL_FETCHING_COMPLETED, job_count=len(jobs))
        return detailed_jobs