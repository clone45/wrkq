# File: harvest/ui/event_handlers.py

from typing import Dict, Any, Callable

class EventHandlers:
    def __init__(self, 
                 stats_dict: Dict[str, Any], # << NEW: Pass the stats dictionary
                 update_callback: Callable, 
                 begin_phase_callback: Callable, 
                 update_phase_callback: Callable, 
                 add_event_callback: Callable):
        self.stats = stats_dict # << NEW: Store reference to stats
        self.update_stats_display = update_callback # Renamed for clarity
        self.begin_phase = begin_phase_callback
        self.update_phase = update_phase_callback
        self.add_event = add_event_callback
        
    def handle_pipeline_started(self, event_type: str, **data): # Add event_type for consistency
        # start_time should be set by the pipeline when it starts, or here by RichProgressDisplay
        self.update_stats_display(
            urls_total=data.get('url_count', 0),
            # start_time=time.time(), # RichProgressDisplay sets its own start_time
            status_message="Pipeline started"
        )
        self.add_event("Pipeline", f"Started processing {data.get('url_count', 0)} URLs")
        
    def handle_pipeline_completed(self, event_type: str, **data):
        self.update_stats_display(status_message="Pipeline completed")
        self.add_event("Pipeline", "Processing completed")
        
    def handle_url_started(self, event_type: str, **data):
        url = data.get('url', '')
        # The stats 'urls_processed' and 'urls_total' are already in self.stats
        # This handler updates 'current_url' and 'status_message'
        # 'urls_processed' is incremented in handle_url_completed
        self.update_stats_display(
            current_url=url,
            status_message=f"Processing URL {self.stats['urls_processed'] + 1}/{self.stats['urls_total']}"
        )
        self.add_event("URL", f"Started processing: {url[:50]}...") # Increased length
        
    def handle_url_completed(self, event_type: str, **data):
        # Increment based on current stats, then update display
        self.stats['urls_processed'] += 1
        self.update_stats_display(urls_processed=self.stats['urls_processed']) # Trigger UI update
        
        url = data.get('url', '')
        jobs_found_for_url = data.get('jobs_found', 0) # Jobs found for *this* URL
        # The overall 'jobs_found' stat is updated by handle_search_completed
        self.add_event("URL", f"Completed URL ({jobs_found_for_url} jobs found)")
        
    def handle_search_started(self, event_type: str, **data):
        # Assuming search phase 'total' is number of pages or 100 for percentage
        # Let's make total for phases more dynamic based on component if possible
        # For now, 100 for percentage is fine for search phase.
        self.begin_phase("Searching", data.get('total_pages_for_search', 100)) 
        self.update_stats_display(status_message="Searching for jobs...")
        self.add_event("Search", f"Started search for: {data.get('url', 'N/A')[:50]}...")
        
    def handle_search_page(self, event_type: str, **data):
        page = data.get('page', 0)
        total_pages = data.get('total_pages', self.begin_phase_total or 1) # Use total from begin_phase if available
        if self.begin_phase_total and total_pages != self.begin_phase_total: # Update if component sends different total
            self.job_progress.update(self.current_operation_id, total=total_pages)
            self.begin_phase_total = total_pages

        # progress = int((page / total_pages) * 100) if total_pages > 0 else 0
        # update_phase expects completed count, not percentage
        self.update_phase(page, f"Fetched page {page}/{total_pages}")
        self.add_event("Search", f"Fetched page {page}/{total_pages}")
        
    def handle_search_completed(self, event_type: str, **data):
        jobs_found_in_search = data.get('jobs_found', 0) # Jobs found in *this* search operation
        
        self.stats['jobs_found'] += jobs_found_in_search # Accumulate
        self.update_stats_display(jobs_found=self.stats['jobs_found']) # Trigger UI update
        
        self.update_phase(self.begin_phase_total or 100, "Search completed") # Mark phase as complete
        self.add_event("Search", f"Search op. completed: {jobs_found_in_search} jobs found")
        
    def handle_job_found(self, event_type: str, **data): # This event is mostly for 'current_job' display
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        # 'jobs_found' is incremented by handle_search_completed which gets total for a search op
        self.update_stats_display(current_job=f"{job_title} at {company}")
        # Optionally add an event here, but might be too noisy if 'Search op. completed' is also there.
        # self.add_event("Job", f"Found: {job_title[:30]}...")
        
    def handle_detail_started(self, event_type: str, **data):
        job_count = data.get('job_count', 0)
        self.begin_phase("Fetching Details", job_count)
        self.update_stats_display(status_message=f"Fetching details for {job_count} jobs...")
        self.add_event("Details", f"Started fetching details for {job_count} jobs")
        
    def handle_job_details(self, event_type: str, **data): # data is the job dict
        index = data.get('index', 0) # 0-based index from the detailer component
        total_being_detailed = data.get('total', 1) # Total jobs in current detail batch
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        
        self.stats['jobs_detailed'] += 1 # Increment based on event occurrence
        self.update_stats_display(
            jobs_detailed=self.stats['jobs_detailed'],
            current_job=f"{job_title} at {company}"
        )
        # update_phase expects number completed, so index + 1
        self.update_phase(index + 1, f"Detailed {index + 1}/{total_being_detailed}")
        
    def handle_detail_completed(self, event_type: str, **data):
        # Mark phase as complete
        if self.current_operation_id is not None and self.current_operation_id in self.job_progress._tasks:
             total_for_phase = self.job_progress._tasks[self.current_operation_id].total
             self.update_phase(total_for_phase or data.get('details_successful_count',0) , "Detailing completed")

        self.add_event("Details", f"Detailing phase completed ({data.get('details_successful_count',0)} successful).")
        
    def handle_job_kept(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        self.add_event("Filter", f"Kept job: {job_title[:30]}...")
        
    def handle_job_filtered(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        reason = data.get('reason', 'N/A')
        
        self.stats['jobs_filtered'] += 1 # Increment based on event occurrence
        self.update_stats_display(jobs_filtered=self.stats['jobs_filtered'])
        self.add_event("Filter", f"Filtered: {job_title[:30]}.. ({reason[:20]})")
        
    def handle_job_basic_stored(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        
        self.stats['jobs_stored'] += 1 # Increment based on event occurrence
        self.update_stats_display(jobs_stored=self.stats['jobs_stored'])
        self.add_event("Storage", f"Stored basic: {job_title[:30]}...")
        
    def handle_job_details_stored(self, event_type: str, **data):
        # This event signifies that details for an *already counted* stored job were updated.
        # So, we don't increment 'jobs_stored' again here.
        job_title = data.get('title', 'Unknown')
        self.add_event("Storage", f"Stored details: {job_title[:30]}...")
        
    def handle_job_marked_filtered(self, event_type: str, **data):
        job_id = data.get('job_id', 'N/A')
        reason = data.get('reason', 'N/A')
        self.add_event("Storage", f"Marked filtered in DB: {job_id} ({reason[:20]})")
        
    def handle_job_duplicate_found(self, event_type: str, **data):
        job_title = data.get('title', 'Unknown')
        company = data.get('company', 'Unknown')
        
        self.stats['jobs_duplicate'] += 1  # Increment based on event occurrence
        self.update_stats_display(jobs_duplicate=self.stats['jobs_duplicate'])
        self.add_event("Duplicate", f"Duplicate job: {job_title[:30]} at {company[:20]}")

    def handle_error(self, event_type: str, **data): # event_type will be e.g., SEARCH_ERROR
        error_source_type = data.get('error_type', event_type.replace('_error', '').capitalize()) # Use provided type or derive
        error_msg = data.get('error', 'Unknown error')
        
        self.stats['errors'] += 1 # Increment based on event occurrence
        self.update_stats_display(errors=self.stats['errors'])
        
        log_msg_parts = [f"{error_source_type}: {error_msg[:60]}"] # Truncate long messages for event log
        if data.get('job_id'): log_msg_parts.append(f"(Job ID: {data.get('job_id')})")
        elif data.get('url'): log_msg_parts.append(f"(URL: {data.get('url')[:30]}..)")
        
        self.add_event("Error", " ".join(log_msg_parts))

    # Helper property for phases
    @property
    def begin_phase_total(self):
        if self.current_operation_id is not None and self.current_operation_id in self.job_progress._tasks:
            return self.job_progress._tasks[self.current_operation_id].total
        return None