# harvest/core/mock_searcher.py

import time
import random
import logging
from typing import List, Dict, Any, Optional

from ..interfaces.searcher import SearcherInterface, SearchOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import EventType
# from ..errors import NetworkError # Example if you want to simulate errors

logger = logging.getLogger(__name__)

class MockSearcher(SearcherInterface):
    """Mock implementation of SearcherInterface for testing."""
    
    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        self.found_jobs = []
        self.error_urls = []
        logger.info("MockSearcher initialized")

    def _generate_job_title(self) -> str:
        roles = ["Mock Software Engineer", "Mock Data Scientist", "Mock Product Manager"]
        return random.choice(roles)

    def _generate_company_name(self) -> str:
        companies = ["MockTech", "DataMock Inc.", "MockSolutions LLC"]
        return random.choice(companies)

    def search(self, url: str, options: Optional[SearchOptions] = None) -> List[Dict[str, Any]]:
        """Mock searching for jobs."""
        # Simulate search start
        self.event_bus.publish(EventType.SEARCH_STARTED, url=url)
        
        # Simulate finding some jobs
        found_jobs = []
        
        # Simulate error for specific URLs
        if "error" in url.lower():
            error_message = "Simulated search error"
            self.error_urls.append(url)
            self.event_bus.publish(EventType.SEARCH_ERROR, error=error_message, url=url)
            return []
            
        # Generate some mock jobs
        for i in range(3):  # Mock finding 3 jobs
            job_data = {
                'job_id': f'mock_job_{i}',
                'title': f'Mock Job {i}',
                'company': 'Mock Company',
                'url': f'https://example.com/job/{i}',
                'location': 'Remote'
            }
            found_jobs.append(job_data)
            self.found_jobs.append(job_data)
            self.event_bus.publish(EventType.JOB_FOUND, **job_data)
            
        # Simulate search completion
        self.event_bus.publish(EventType.SEARCH_COMPLETED, jobs_found=len(found_jobs))
        
        return found_jobs