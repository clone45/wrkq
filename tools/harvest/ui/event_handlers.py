# File: harvest/ui/event_handlers.py

"""
Event handlers for the LinkedIn job harvester UI.
"""

from typing import Dict, Any, Callable

class EventHandlers:
    """
    Event handlers for progress display.
    """
    
    def __init__(self, update_callback: Callable, begin_phase_callback: Callable, 
                 update_phase_callback: Callable, add_event_callback: Callable):
        """
        Initialize event handlers.
        
        Args:
            update_callback: Callback to update statistics
            begin_phase_callback: Callback to begin a new phase
            update_phase_callback: Callback to update current phase
            add_event_callback: Callback to add an event
        """
        self.update = update_callback
        self.begin_phase = begin_phase_callback
        self.update_phase = update_phase_callback
        self.add_event = add_event_callback
        
    def handle_pipeline_started(self, **data):
        """Handle pipeline started event."""
        self.update(
            urls_total=data.get('url_count', 0),
            start_time=data.get('start_time', 0),
            status_message="Pipeline started"
        )
        self.add_event("Pipeline", f"Started processing {data.get('url_count', 0)} URLs")
        
    def handle_pipeline_completed(self, **data):
        """Handle pipeline completed event."""
        self.update(status_message="Pipeline completed")
        self.add_event("Pipeline", "Processing completed")
        
    def handle_url_started(self, **data):
        """Handle URL processing started event."""
        url = data.get('url', '')
        urls_processed = data.get('urls_processed', 0)
        urls_total = data.get('urls_total', 0)
        
        self.update(
            current_url=url,
            status_message=f"Processing URL {urls_processed + 1}/{urls_total}"
        )
        self.add_event("URL", f"Started processing: {url[:30]}...")
        
    def handle_url_completed(self, **data):
        """Handle URL processing completed event."""
        self.update(urls_processed=data.get('urls_processed', 0) + 1)
        url = data.get('url', '')
        jobs_found = data.get('jobs_found', 0)
        self.add_event("URL", f"Completed: Found {jobs_found} jobs")
        
    def handle_search_started(self, **data):
        """Handle search started event."""
        self.begin_phase("Searching", 100)  # Use percentage for search
        self.update(status_message="Searching for jobs...")
        self.add_event("Search", "Started searching for jobs")
        
    def handle_search_page(self, **data):
        """Handle search page fetched event."""
        page = data.get('page', 0)
        total_pages = data.get('total_pages', 1)
        progress = int((page / total_pages) * 100) if total_pages > 0 else 0
        self.update_phase(progress, f"Fetched page {page}/{total_pages}")
        self.add_event("Search", f"Fetched page {page}/{total_pages}")
        
    def handle_search_completed(self, **data):
        """Handle search completed event."""
        jobs_found = data.get('jobs_found', 0)
        
        # Update total jobs found
        current_jobs_found = data.get('current_jobs_found', 0)
        self.update(jobs_found=current_jobs_found + jobs_found)
        
        self.update_phase(100, "Search completed")
        self.add_event("Search", f"Completed with {jobs_found} jobs found")
        
    def handle_job_found(self, **data):
        """Handle job found event."""
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        self.update(current_job=f"{job_title} at {company}")
        
    def handle_detail_started(self, **data):
        """Handle detail fetching started event."""
        job_count = data.get('job_count', 0)
        self.begin_phase("Fetching Details", job_count)
        self.update(status_message=f"Fetching details for {job_count} jobs...")
        self.add_event("Details", f"Started fetching details for {job_count} jobs")
        
    def handle_job_details(self, **data):
        """Handle job details fetched event."""
        index = data.get('index', 0)
        total = data.get('total', 1)
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        
        self.update(
            jobs_detailed=data.get('jobs_detailed', 0) + 1,
            current_job=f"{job_title} at {company}"
        )
        self.update_phase(index + 1, f"Fetched details for {index + 1}/{total} jobs")
        
    def handle_detail_completed(self, **data):
        """Handle detail fetching completed event."""
        self.add_event("Details", "Completed fetching all job details")
        
    def handle_job_kept(self, **data):
        """Handle job kept event."""
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        self.add_event("Filter", f"Kept job: {job_title} at {company}")
        
    def handle_job_filtered(self, **data):
        """Handle job filtered event."""
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        reason = data.get('reason', 'Unknown reason')
        
        self.update(jobs_filtered=data.get('jobs_filtered', 0) + 1)
        self.add_event("Filter", f"Filtered out: {job_title} (Reason: {reason})")
        
    def handle_job_basic_stored(self, **data):
        """Handle job basic info stored event."""
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        
        self.update(jobs_stored=data.get('jobs_stored', 0) + 1)
        self.add_event("Storage", f"Stored basic info: {job_title} at {company}")
        
    def handle_job_details_stored(self, **data):
        """Handle job details stored event."""
        job_title = data.get('title', 'Unknown')
        self.add_event("Storage", f"Updated with details: {job_title}")
        
    def handle_job_marked_filtered(self, **data):
        """Handle job marked as filtered event."""
        job_title = data.get('title', 'Unknown')
        reason = data.get('reason', 'Unknown reason')
        self.add_event("Storage", f"Marked as filtered: {job_title} ({reason})")
        
    def handle_error(self, **data):
        """Handle error event."""
        error_type = data.get('event_type', 'Unknown').replace('_error', '')
        error_msg = data.get('error', 'Unknown error')
        job_id = data.get('job_id', None)
        
        self.update(errors=data.get('errors', 0) + 1)
        
        if job_id:
            self.add_event("Error", f"{error_type}: {error_msg} (Job ID: {job_id})")
        else:
            self.add_event("Error", f"{error_type}: {error_msg}")