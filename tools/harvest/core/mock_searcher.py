# harvest/core/mock_searcher.py

import time
import random
import logging
from typing import List, Dict, Any, Optional

from ..interfaces.searcher import SearcherInterface, SearchOptions
from ..interfaces.event_bus import EventBus as EventBusInterface # Use your interface type
from ..events import SEARCH_STARTED, JOB_FOUND, SEARCH_COMPLETED, SEARCH_ERROR
# from ..errors import NetworkError # Example if you want to simulate errors

logger = logging.getLogger(__name__)

class MockSearcher(SearcherInterface):

    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        logger.info("MockSearcher initialized")

    def _generate_job_title(self) -> str:
        roles = ["Mock Software Engineer", "Mock Data Scientist", "Mock Product Manager"]
        return random.choice(roles)

    def _generate_company_name(self) -> str:
        companies = ["MockTech", "DataMock Inc.", "MockSolutions LLC"]
        return random.choice(companies)

    def search(self, url: str, options: Optional[SearchOptions] = None) -> List[Dict[str, Any]]:
        max_jobs = options.jobs_per_page if options and options.jobs_per_page else 5 # Default mock jobs
        delay = options.delay_between_requests if options and options.delay_between_requests else 0.1

        logger.info(f"MockSearcher: Starting search for URL '{url}' with options: {options}")
        self.event_bus.publish(SEARCH_STARTED, url=url)
        
        time.sleep(delay / 2) # Simulate initial work

        found_jobs: List[Dict[str, Any]] = []
        num_jobs_to_find = random.randint(max_jobs // 2, max_jobs) # Find a variable number of jobs

        for i in range(num_jobs_to_find):
            job_id = f"mock_search_{random.randint(1000, 9999)}_{i}"
            job_data = {
                "job_id": job_id,
                "title": self._generate_job_title(),
                "company": self._generate_company_name(),
                "location": random.choice(["Remote", "Mockville, MS", "Testburg, TS"]),
                "url": f"https://mock.linkedin.com/jobs/view/{job_id}/",
                "description_short": "This is a mock job listing.", # Basic info from search
                "posted_date_str": "2 days ago" # Basic info from search
            }
            found_jobs.append(job_data)
            self.event_bus.publish(JOB_FOUND, **job_data)
            logger.debug(f"MockSearcher: Found job '{job_data['title']}'")
            time.sleep(delay / 5 if num_jobs_to_find > 0 else delay) # Smaller delay between jobs

        # Simulate a random search error occasionally
        if random.random() < 0.05: # 5% chance of error
            error_message = "Simulated random network blip during search"
            logger.warning(f"MockSearcher: Simulating search error: {error_message}")
            self.event_bus.publish(SEARCH_ERROR, error=error_message, url=url)
            # Optionally raise NetworkError(error_message) if pipeline should handle it

        logger.info(f"MockSearcher: Search completed for URL '{url}'. Found {len(found_jobs)} jobs.")
        self.event_bus.publish(SEARCH_COMPLETED, jobs_found=len(found_jobs))
        return found_jobs