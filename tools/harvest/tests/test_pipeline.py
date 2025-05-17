import unittest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from ..core.pipeline import Pipeline
from ..core.job_iterator import JobIterator
from ..core.preprocessor import PreProcessor
from ..core.postprocessor import PostProcessor
from ..interfaces.job_state import JobState, JobStatus
from ..interfaces.pipeline import PipelineConfig
from ..interfaces.searcher import SearchOptions
from ..interfaces.job_iterator import JobIteratorOptions
from ..interfaces.preprocessor import PreProcessorOptions
from ..interfaces.postprocessor import PostProcessorOptions
from ..interfaces.detailer import DetailOptions
from ..interfaces.storer import StorageOptions
from ..interfaces.event_bus import EventBus
from ..events import EventType

class TestPipeline(unittest.TestCase):
    def setUp(self):
        # Create mock components
        self.searcher = Mock()
        self.detailer = Mock()
        self.storer = Mock()
        self.event_bus = Mock(spec=EventBus)
        
        # Create mock DB connection
        self.db_connection = MagicMock()
        
        # Create real components that we want to test
        self.sample_jobs = [
            {
                "job_id": "job1",
                "title": "Software Engineer",
                "company": "Tech Corp",
                "url": "https://example.com/job1",
                "posted_date": datetime.now().isoformat()
            },
            {
                "job_id": "job2",
                "title": "Senior Manager",  # Should be filtered by title
                "company": "Tech Corp",
                "url": "https://example.com/job2",
                "posted_date": datetime.now().isoformat()
            },
            {
                "job_id": "job3",
                "title": "Python Developer",
                "company": "Staffing Agency",  # Should be filtered by company
                "url": "https://example.com/job3",
                "posted_date": datetime.now().isoformat()
            }
        ]
        
        self.job_iterator = JobIterator(
            self.sample_jobs,
            JobIteratorOptions(batch_size=1)
        )
        
        self.preprocessor = PreProcessor(self.db_connection)
        self.postprocessor = PostProcessor()
        
        # Create pipeline
        self.pipeline = Pipeline(
            searcher=self.searcher,
            job_iterator=self.job_iterator,
            preprocessor=self.preprocessor,
            detailer=self.detailer,
            postprocessor=self.postprocessor,
            storer=self.storer,
            event_bus=self.event_bus
        )
        
        # Set up mock responses
        self.searcher.search.return_value = self.sample_jobs
        self.detailer.fetch_details_batch.side_effect = lambda jobs, options: [{
            **job,
            "description": "Sample job description",
            "salary": "$100k-$150k",
            "location": "Remote"
        } for job in jobs]
        
    def test_pipeline_processing(self):
        """Test full pipeline processing"""
        # Configure pipeline
        config = PipelineConfig(
            search_options=SearchOptions(max_pages=1),
            iterator_options=JobIteratorOptions(batch_size=1),
            preprocessor_options=PreProcessorOptions(
                title_filters_path="tests/data/title_filters.json",
                company_filters_path="tests/data/company_filters.json",
                check_duplicates=True
            ),
            detail_options=DetailOptions(),
            postprocessor_options=PostProcessorOptions(
                required_fields=["description", "salary"],
                min_description_length=10,
                validate_urls=True
            ),
            storage_options=StorageOptions(database_path=":memory:")
        )
        
        # Process jobs
        stats = self.pipeline.process_jobs(self.sample_jobs, config)
        
        # Verify stats
        self.assertEqual(stats["jobs_found"], 3)
        self.assertEqual(stats["jobs_filtered_pre"], 2)  # Manager and Staffing Agency
        self.assertEqual(stats["jobs_detailed"], 1)  # Software Engineer
        self.assertEqual(stats["jobs_stored"], 1)
        
        # Verify event bus calls
        self.event_bus.publish.assert_any_call("job_found", job_id="job1")
        self.event_bus.publish.assert_any_call("job_details_started", job_id="job1")
        self.event_bus.publish.assert_any_call("job_details_completed", job_id="job1")
        self.event_bus.publish.assert_any_call("job_stored", job_id="job1")
        
    def test_duplicate_detection(self):
        """Test duplicate job detection"""
        # Set up mock DB to simulate existing job
        cursor_mock = self.db_connection.cursor.return_value
        cursor_mock.fetchone.return_value = (1,)  # Simulate found record
        
        # Process jobs
        config = PipelineConfig(
            search_options=SearchOptions(),
            iterator_options=JobIteratorOptions(),
            preprocessor_options=PreProcessorOptions(check_duplicates=True),
            detail_options=DetailOptions(),
            postprocessor_options=PostProcessorOptions(),
            storage_options=StorageOptions(database_path=":memory:")
        )
        
        stats = self.pipeline.process_jobs([self.sample_jobs[0]], config)
        
        # Verify job was marked as duplicate
        self.assertEqual(stats["jobs_found"], 1)
        self.assertEqual(stats["jobs_filtered_pre"], 1)
        self.assertEqual(stats["jobs_duplicate"], 1)
        
    def test_postprocessing_filters(self):
        """Test postprocessing filters"""
        # Create job with invalid description
        job_with_short_desc = {
            "job_id": "job4",
            "title": "Developer",
            "company": "Good Corp",
            "url": "https://example.com/job4",
            "description": "Too short",
            "posted_date": datetime.now().isoformat()
        }
        
        # Configure pipeline with strict post-processing
        config = PipelineConfig(
            search_options=SearchOptions(),
            iterator_options=JobIteratorOptions(),
            preprocessor_options=PreProcessorOptions(check_duplicates=False),
            detail_options=DetailOptions(),
            postprocessor_options=PostProcessorOptions(
                min_description_length=20,
                validate_urls=True
            ),
            storage_options=StorageOptions(database_path=":memory:")
        )
        
        # Process job
        stats = self.pipeline.process_jobs([job_with_short_desc], config)
        
        # Verify job was filtered in post-processing
        self.assertEqual(stats["jobs_found"], 1)
        self.assertEqual(stats["jobs_filtered_post"], 1)
        
    def test_process_jobs_through_pipeline(self):
        # Setup mock data
        mock_jobs = [
            {'job_id': 'job1', 'title': 'Job 1'},
            {'job_id': 'job2', 'title': 'Job 2'}
        ]
        
        # Configure mocks
        self.searcher.search_jobs.return_value = mock_jobs
        self.detailer.fetch_job_details.return_value = mock_jobs
        self.event_bus.publish.return_value = None
        
        # Run pipeline
        self.pipeline.process_jobs_through_pipeline(['http://example.com'])
        
        # Verify event bus calls
        self.event_bus.publish.assert_any_call(EventType.PIPELINE_STARTED, url_count=1)
        self.event_bus.publish.assert_any_call(EventType.URL_PROCESSING_STARTED, url='http://example.com')
        self.event_bus.publish.assert_any_call(EventType.JOB_FOUND, job_id='job1')
        self.event_bus.publish.assert_any_call(EventType.JOB_FOUND, job_id='job2')
        self.event_bus.publish.assert_any_call(EventType.URL_PROCESSING_COMPLETED, url='http://example.com')
        self.event_bus.publish.assert_any_call(EventType.PIPELINE_COMPLETED)
        
    def test_error_handling(self):
        # Setup mock data to simulate error
        self.searcher.search_jobs.side_effect = Exception("Search failed")
        
        # Run pipeline
        self.pipeline.process_jobs_through_pipeline(['http://example.com'])
        
        # Verify error event was published
        self.event_bus.publish.assert_any_call(
            EventType.PIPELINE_ERROR,
            error="Search failed",
            url='http://example.com',
            stage="search",
            error_type="Exception"
        )

if __name__ == "__main__":
    unittest.main() 