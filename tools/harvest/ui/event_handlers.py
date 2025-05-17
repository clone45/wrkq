# File: harvest/ui/event_handlers.py

from typing import Dict, Any, Callable
import logging
from ..common.stats_tracker import StatsTracker

logger = logging.getLogger(__name__)

class EventHandlers:
    def __init__(self, 
                 stats_tracker: StatsTracker,
                 update_callback: Callable, 
                 begin_phase_callback: Callable, 
                 update_phase_callback: Callable, 
                 add_event_callback: Callable,
                 job_progress=None,
                 current_operation_id_getter=None):
        """Initialize event handlers."""
        self.stats_tracker = stats_tracker
        self.update_stats_display = update_callback
        self.begin_phase = begin_phase_callback
        self.update_phase = update_phase_callback
        self.add_event = add_event_callback
        
        # Store references to progress tracking objects
        self.job_progress = job_progress
        self.current_operation_id_getter = current_operation_id_getter
        
    def handle_pipeline_started(self, event_type: str, **data):
        self.stats_tracker.update(
            urls_total=data.get('url_count', 0),
            status_message="Pipeline started"
        )
        self.update_stats_display()
        self.add_event("Pipeline", f"Started processing {data.get('url_count', 0)} URLs")
        
    def handle_pipeline_completed(self, event_type: str, **data):
        self.stats_tracker.update(status_message="Pipeline completed")
        self.update_stats_display()
        self.add_event("Pipeline", "Processing completed")
        
    def handle_url_started(self, event_type: str, **data):
        url = data.get('url', '')
        self.stats_tracker.update(
            current_url=url,
            status_message=f"Processing URL {self.stats_tracker.stats.urls_processed + 1}/{self.stats_tracker.stats.urls_total}"
        )
        self.update_stats_display()
        self.add_event("URL", f"Started processing: {url[:50]}...")
        
    def handle_url_completed(self, event_type: str, **data):
        self.stats_tracker.increment('urls_processed')
        self.update_stats_display()
        
        url = data.get('url', '')
        jobs_found_for_url = data.get('jobs_found', 0)
        self.add_event("URL", f"Completed URL ({jobs_found_for_url} jobs found)")
        
    def handle_search_started(self, event_type: str, **data):
        self.begin_phase("Searching", data.get('total_pages_for_search', 100))
        self.stats_tracker.update(status_message="Searching for jobs...")
        self.update_stats_display()
        self.add_event("Search", f"Started search for: {data.get('url', 'N/A')[:50]}...")
        
    def handle_search_page(self, event_type: str, **data):
        page = data.get('page', 0)
        total_pages = data.get('total_pages', self.begin_phase_total or 1)
        
        if self.begin_phase_total and total_pages != self.begin_phase_total and self.job_progress and self.current_operation_id:
            self.job_progress.update(self.current_operation_id, total=total_pages)
            self.begin_phase_total = total_pages

        self.update_phase(page, f"Fetched page {page}/{total_pages}")
        self.add_event("Search", f"Fetched page {page}/{total_pages}")
        
    def handle_search_completed(self, event_type: str, **data):
        jobs_found_in_search = data.get('jobs_found', 0)
        self.stats_tracker.increment('jobs_found', jobs_found_in_search)
        self.update_stats_display()
        
        self.update_phase(self.begin_phase_total or 100, "Search completed")
        self.add_event("Search", f"Search op. completed: {jobs_found_in_search} jobs found")
        
    def handle_job_found(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        self.stats_tracker.update(current_job=f"{job_title} at {company}")
        self.update_stats_display()
        
    def handle_job_kept(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        self.add_event("Filter", f"Kept job: {job_title[:30]}...")
        
    def handle_job_filtered(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        job_id = data.get('job_id', 'Unknown')
        reason = data.get('reason', 'N/A')
        company = data.get('company', 'Unknown')
        
        # Log the current state before update
        old_filtered_count = self.stats_tracker.stats.jobs_filtered_out
        total_jobs = self.stats_tracker.stats.jobs_found
        logger.info(f"Filtering job '{job_title}' (ID: {job_id}) at {company} - Current stats: filtered={old_filtered_count}, total={total_jobs}")
        
        # Update filtered count
        self.stats_tracker.increment('jobs_filtered_out')
        new_filtered_count = self.stats_tracker.stats.jobs_filtered_out
        
        # Log the update
        logger.info(f"Updated filtered count: {old_filtered_count} -> {new_filtered_count} (Reason: {reason})")
        
        self.update_stats_display()
        self.add_event("Filter", f"Filtered: {job_title[:30]}.. ({reason[:20]})")
        
    def handle_job_basic_stored(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        
        self.stats_tracker.increment('jobs_stored')
        self.update_stats_display()
        self.add_event("Storage", f"Stored basic: {job_title[:30]}...")
        
    def handle_job_details_stored(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        self.add_event("Storage", f"Stored details: {job_title[:30]}...")
        
    def handle_job_marked_filtered(self, event_type: str, **data):
        job_id = data.get('job_id', 'N/A')
        reason = data.get('reason', 'N/A')
        self.add_event("Storage", f"Marked filtered in DB: {job_id} ({reason[:20]})")
        
    def handle_job_duplicate_found(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        
        self.stats_tracker.increment('jobs_duplicate')
        self.update_stats_display()
        self.add_event("Duplicate", f"Duplicate job: {job_title[:30]} at {company[:20]}")

    def handle_error(self, event_type: str, **data):
        error_source_type = data.get('error_type', event_type.replace('_error', '').capitalize())
        error_msg = data.get('error', 'Unknown error')
        
        self.stats_tracker.increment('errors')
        self.update_stats_display()
        
        log_msg_parts = [f"{error_source_type}: {error_msg[:60]}"]
        if data.get('job_id'): log_msg_parts.append(f"(Job ID: {data.get('job_id')})")
        elif data.get('url'): log_msg_parts.append(f"(URL: {data.get('url')[:30]}..)")
        
        self.add_event("Error", " ".join(log_msg_parts))

    def handle_detail_started(self, event_type: str, **data):
        """Handle the start of detail fetching."""
        total_jobs = data.get('total_jobs', 0)
        self.begin_phase("Fetching Details", total_jobs)
        self.stats_tracker.update(status_message="Fetching job details...")
        self.update_stats_display()
        self.add_event("Details", f"Started fetching details for {total_jobs} jobs")

    def handle_job_details(self, event_type: str, **data):
        """Handle when job details are fetched."""
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        self.stats_tracker.increment('jobs_detailed')
        self.update_stats_display()
        self.add_event("Details", f"Fetched details: {job_title[:30]}...")

    def handle_detail_completed(self, event_type: str, **data):
        """Handle completion of detail fetching."""
        total_detailed = data.get('jobs_detailed', 0)
        self.update_phase(total_detailed, "Detail fetching completed")
        self.add_event("Details", f"Completed fetching details for {total_detailed} jobs")

    @property
    def begin_phase_total(self):
        """Helper property for phases"""
        if self.job_progress and self.current_operation_id is not None and self.current_operation_id in self.job_progress._tasks:
            return self.job_progress._tasks[self.current_operation_id].total
        return None
    
    @property
    def current_operation_id(self):
        """Helper property for getting current operation ID"""
        if self.current_operation_id_getter:
            return self.current_operation_id_getter()
        return None