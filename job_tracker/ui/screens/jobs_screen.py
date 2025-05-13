# job_tracker/ui/screens/jobs_screen.py with simplified details logic
"""
Main Jobs screen – updated with integrated chat and details view
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Grid
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

# Data access
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.company_repo import CompanyRepo

# Business layer
from job_tracker.services.job_service import JobService
from job_tracker.services.application_service import ApplicationService

# Domain models
from job_tracker.models.pagination import Page
from job_tracker.models.job import Job

# UI helpers
from job_tracker.ui.controllers.status_bar import StatusBarController
from job_tracker.utils.formatters import format_date
from simple_logger import Slogger, LogLevel

# Widgets
from job_tracker.ui.widgets.job_table import JobTable
from job_tracker.ui.widgets.pagination import Pagination
from job_tracker.ui.widgets.search_bar import SearchBar
from job_tracker.ui.widgets.job_details import JobDetail
from job_tracker.ui.widgets.chat_panel import ChatPanel
from job_tracker.ui.widgets.confirmation_modal import ConfirmationModal

class JobsScreen(Screen):
    """Main screen for job listings with integrated chat panel."""

    # reactive state
    current_page: int = reactive(1)
    per_page: int = reactive(15)
    show_hidden: bool = reactive(False)
    selected_job_id: Optional[str] = reactive(None, layout=True)

    search_query: str = reactive("")
    total_jobs: int = reactive(0)
    total_pages: int = reactive(1)

    # ------------------------------------------------------------------ #

    def __init__(
        self,
        job_repo: JobRepo,
        company_repo: CompanyRepo,
        config: Dict[str, Any],
        application_service: Optional[ApplicationService] = None,
        *,
        id: str = "jobs_screen",
    ) -> None:
        super().__init__(id=id)

        self.config = config
        self.per_page = config.get("ui", {}).get("per_page", 15)

        # business services
        self.job_service = JobService(
            job_repo,
            company_repo,
            default_page_size=self.per_page,
        )
        self.application_service = application_service

        # in-memory cache of current table rows
        self.jobs_data: List[Job] = []

    # ------------------------------------------------------------------ #
    # Compose & mount
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            with Vertical(id="content-area"):
                yield SearchBar(id="search-bar")
                yield JobTable(id="jobs-table")
                yield Pagination(id="pagination")
                
                # Detail section (chat panel temporarily removed)
                with Grid(id="detail-chat-grid"):
                    yield JobDetail(id="job-detail")
                    # Chat panel removed but code preserved for future reintegration
                    # yield ChatPanel(id="chat-panel")

        yield Static(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        # table setup
        table = self.query_one(JobTable)
        table.add_columns(
            "",
            "Company",
            "Title",
            "Location",
            "Date Posted",
            "Salary",
            "Status",
            "Hidden",
        )
        # Set a smaller fixed width for the Applied column since it only contains a checkmark
        # table.columns[0].width = 8
        table.styles.height = "1fr"

        # Initialize the job detail with null (shows "No Job Selected")
        detail_widget = self.query_one(JobDetail)
        detail_widget.update_job(None)

        # Chat panel initialization code preserved but disabled
        # since the panel is not currently in the UI
        # chat_panel = self.query_one(ChatPanel)
        # chat_panel.add_assistant_message("Welcome to Job Tracker! Select a job to view details.")

        # status-bar controller
        self.status_controller = StatusBarController(self.query_one("#status-bar"))

        self.load_jobs()

    # ------------------------------------------------------------------ #
    # Reactive watchers
    # ------------------------------------------------------------------ #

    def watch_selected_job_id(self, job_id: Optional[str]) -> None:
        detail_widget = self.query_one(JobDetail)

        if job_id:
            # Automatically update job details when a job is selected
            job = self._get_job_data(job_id)

            detail_widget.update_job(job)
            
            # Chat panel update code preserved but disabled
            # since the panel is not currently in the UI
            # Inform the chat panel about the selected job
            # chat_panel = self.query_one(ChatPanel)
            # if job:
            #     chat_panel.add_assistant_message(f"Now viewing: {job.company} - {job.title}")
        else:
            # Clear details if no job is selected
            detail_widget.update_job(None)

        # update status-bar selection text
        current = str(self.query_one("#status-bar").renderable)
        base = current.split(" | Selected:")[0]
        self.status_controller.update_with_selection(
            base, self._get_job_data(job_id) if job_id else None
        )

    # ------------------------------------------------------------------ #
    # Action handlers
    # ------------------------------------------------------------------ #


    def action_focus_search(self) -> None:
        self.query_one(SearchBar).focus_input()

    def action_next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_jobs()

    def action_prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.load_jobs()

    def action_toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        self.current_page = 1
        self.load_jobs()
        status = "showing" if self.show_hidden else "hiding"
        self.notify(f"Now {status} hidden jobs", title="Filter Changed")

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    def on_screen_resume(self, event) -> None:
        self.load_jobs()


    def on_job_table_row_selected(self, event: JobTable.RowSelected) -> None:
        row_index = event.row_key.value
        if row_index is not None and 0 <= row_index < len(self.jobs_data):
            job = self.jobs_data[row_index]
            self.selected_job_id = job.id

    def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
        self.search_query = event.query
        self.current_page = 1
        self.load_jobs()

    def on_pagination_page_changed(self, event: Pagination.PageChanged) -> None:
        if self.current_page != event.page:
            self.current_page = event.page
            self.load_jobs()



    # ------------------------------------------------------------------ #
    # Data helpers
    # ------------------------------------------------------------------ #

    def _get_job_data(self, job_id: str) -> Optional[Job]:
        return next((j for j in self.jobs_data if j.id == job_id), None) \
            or self.job_service.by_id(job_id)
            
    def _create_applied_jobs_cache(self, job_ids: List[str]) -> Dict[str, bool]:
        """
        Create a cache of job ID to application status mappings.
        
        Args:
            job_ids: List of job IDs to check
            
        Returns:
            Dictionary mapping job IDs to boolean application status
        """
        applied_jobs = {}
        
        if not self.application_service:
            # If no application service, assume all jobs are not applied
            Slogger.warning("Application service not available, cannot check applied status", 
                          {"screen": "JobsScreen", "method": "_create_applied_jobs_cache"})
            return {job_id: False for job_id in job_ids}
            
        try:
            # For each job ID, check if an application exists
            applied_count = 0
            for job_id in job_ids:
                application = self.application_service.by_job_id(job_id)
                is_applied = application is not None
                applied_jobs[job_id] = is_applied
                if is_applied:
                    applied_count += 1
            
            Slogger.info(f"Found {applied_count} applied jobs out of {len(job_ids)} total jobs",
                       {"screen": "JobsScreen", "method": "_create_applied_jobs_cache"})
            return applied_jobs
        except Exception as e:
            # Log error but continue with empty cache
            Slogger.exception(e, "Error creating applied jobs cache", 
                            {"screen": "JobsScreen", "method": "_create_applied_jobs_cache"})
            return {job_id: False for job_id in job_ids}
    
    def _check_job_applied_status(self, job_id: str, applied_cache: Optional[Dict[str, bool]] = None) -> bool:
        """
        Check if a job has been applied to.
        
        Args:
            job_id: The ID of the job to check
            applied_cache: Optional cache of job application status
            
        Returns:
            True if the job has been applied to, False otherwise
        """
        # Use cache if provided
        if applied_cache is not None and job_id in applied_cache:
            return applied_cache[job_id]
            
        # Fallback to direct lookup if no cache or job not in cache
        if not self.application_service:
            return False
            
        try:
            application = self.application_service.by_job_id(job_id)
            return application is not None
        except Exception:
            # In case of any error, assume not applied
            return False

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update the status of a job."""
        job = self._get_job_data(job_id)
        
        if not job:
            self.notify("Could not find job to update status", severity="error", timeout=3)
            return
            
        try:
            # Create context for logging
            context = {
                "screen": "JobsScreen",
                "method": "update_job_status",
                "job_id": job_id,
                "company": job.company,
                "title": job.title,
                "new_status": status or "None"
            }
            
            # Log the attempt
            from simple_logger import Slogger
            Slogger.info(f"Updating status for job '{job.title}' at '{job.company}' to '{status or 'None'}'", context)
            
            # Call service to update status
            success = self.job_service.update_status(job_id, status)
            
            if success:
                self.notify(f"Status for '{job.company} - {job.title}' updated to '{status or 'None'}'", 
                        severity="information", timeout=3)
                
                # Refresh job list
                self.load_jobs()
                
                # Update the detail view to reflect the changes
                if self.selected_job_id == job_id:
                    updated_job = self._get_job_data(job_id)
                    self.query_one(JobDetail).update_job(updated_job)
            else:
                self.notify(f"Failed to update status for '{job.company} - {job.title}'", severity="error", timeout=3)
        except Exception as e:
            error_type = type(e).__name__
            self.notify(f"Error updating job status: {error_type} - {str(e)}", severity="error", timeout=5)
    
    def show_job_actions(self) -> None:
        """Show a modal with actions for the selected job."""
        from job_tracker.ui.widgets.job_actions import JobActionsModal
        
        if not self.selected_job_id:
            self.notify("No job selected for actions", severity="warning", timeout=3)
            return

        job = self._get_job_data(self.selected_job_id)
        
        if not job:
            self.notify("Could not find selected job", severity="error", timeout=3)
            return
        
        # Open the modal with job details and callbacks
        self.app.push_screen(
            JobActionsModal(
                job_title=job.title,
                company_name=job.company,
                job_id=self.selected_job_id,
                hide_callback=self._hide_job_callback,
                delete_callback=self.delete_job,
                mark_applied_callback=self._mark_applied_callback,
                update_status_callback=self.update_job_status,
            )
        )

    def load_jobs(self) -> None:

        """Fetch jobs from service and refresh UI widgets."""
        page_obj: Page[Job] = self.job_service.page(
            page=self.current_page,
            per_page=self.per_page,
            search=self.search_query,
            show_hidden=self.show_hidden,
        )

        self.jobs_data = list(page_obj.items)
        self.total_jobs = page_obj.total
        self.total_pages = page_obj.pages

        # -------- Table ----------
        table = self.query_one(JobTable)
        table.clear()

        # Create a cache of applied status for all jobs in the current page for better performance
        job_ids = [job.id for job in self.jobs_data]
        applied_jobs_cache = self._create_applied_jobs_cache(job_ids)
        
        current_selection_key: Optional[int] = None
        for idx, job in enumerate(self.jobs_data):
            job_id = job.id
            fmt = self.config.get("ui", {}).get("date_format", "%Y-%m-%d")
            
            # Check if job has been applied to using the cache
            is_applied = self._check_job_applied_status(job_id, applied_jobs_cache)
            applied_indicator = "✓" if is_applied else ""
            
            table.add_row(
                applied_indicator,
                job.company,
                job.title,
                job.location,
                format_date(job.posting_date, fmt),
                job.salary or "N/A",
                job.status or "N/A", 
                "Yes" if job.hidden else "No",
                key=idx,
            )
            if job_id == self.selected_job_id:
                current_selection_key = idx

        # scroll to selection
        if current_selection_key is not None:
            self.set_timer(
                0.05,
                lambda row=current_selection_key: table.move_cursor(
                    row=row, animate=False
                ),
            )

        # -------- Pagination -------
        self.query_one(Pagination).update_pages(
            self.current_page, self.total_pages
        )

        # -------- Status bar -------
        meta = {
            "total": self.total_jobs,
            "pages": self.total_pages,
            "current_page": self.current_page,
            "search_query": self.search_query,
            "show_hidden": self.show_hidden,
        }
        selected = (
            self._get_job_data(self.selected_job_id)
            if self.selected_job_id
            else None
        )
        self.status_controller.update(meta, self.selected_job_id, selected)

    def hide_selected_job(self) -> None:
        """Hide the currently selected job."""
        if not self.selected_job_id:
            self.notify("No job selected to hide", severity="warning", timeout=3)
            return

        job = self._get_job_data(self.selected_job_id)
        
        if not job:
            self.notify("Could not find selected job", severity="error", timeout=3)
            return
            
        # Don't rehide already hidden jobs
        if job.hidden:
            self.notify(f"Job '{job.company} - {job.title}' is already hidden", 
                    severity="warning", timeout=3)
            return
        
        # Call service to hide the job
        try:
            # Use existing hide method from job_service
            success = self.job_service.hide(self.selected_job_id)
            
            if success:
                self.notify(f"Job '{job.company} - {job.title}' hidden successfully", 
                        severity="information", timeout=3)
                
                # Refresh job list
                self.load_jobs()
                
                # If showing hidden jobs, update the detail view to reflect the changes
                if self.show_hidden and self.selected_job_id:
                    job = self._get_job_data(self.selected_job_id)
                    self.query_one(JobDetail).update_job(job)
                else:
                    # Clear selection if we're not showing hidden jobs
                    self.selected_job_id = None
            else:
                self.notify("Failed to hide job", severity="error", timeout=3)
        except Exception as e:
            self.notify(f"Error hiding job: {str(e)}", severity="error", timeout=3)

    def delete_job(self, job_id: str) -> None:
        """Delete a job from the database."""
        job = self._get_job_data(job_id)
        
        if not job:
            self.notify("Could not find job to delete", severity="error", timeout=3)
            return
        
        # Confirm with the user before deletion
        def handle_delete_yes():
            try:
                # Call service to delete the job
                success = self.job_service.delete(job_id)
                
                if success:
                    self.notify(f"Job '{job.company} - {job.title}' deleted permanently", 
                            severity="information", timeout=3)
                    
                    # Clear selection if this was the selected job
                    if self.selected_job_id == job_id:
                        self.selected_job_id = None
                    
                    # Refresh job list
                    self.load_jobs()
                else:
                    self.notify("Failed to delete job", severity="error", timeout=3)
            except Exception as e:
                self.notify(f"Error deleting job: {str(e)}", severity="error", timeout=3)
        
        # Show confirmation dialog
        self.app.push_screen(
            ConfirmationModal(
                title="Confirm Job Deletion",
                message=f"Are you sure you want to permanently delete the job '{job.company} - {job.title}'?\n\nThis action cannot be undone.",
                on_yes=handle_delete_yes
            )
        )

    def _hide_job_callback(self, job_id: str) -> None:
        """
        Callback function for hiding a job from the actions modal.
        This temporarily sets the selected job ID and then calls the hide method.
        """
        # Save current selection
        current_selection = self.selected_job_id
        
        # Set selection to the job we want to hide
        self.selected_job_id = job_id
        
        # Use the hide method
        self.hide_selected_job()
        
        # If the original selection was different and still exists, restore it
        if current_selection != job_id and current_selection and self.show_hidden:
            # Check if the original job still exists in the data
            if any(job.id == current_selection for job in self.jobs_data):
                self.selected_job_id = current_selection
                
    def _mark_applied_callback(self, job_id: str) -> None:
        """
        Callback function for marking a job as applied from the actions modal.
        Creates an application record and adds an entry to the history table.
        """
        if not self.application_service:
            self.notify("Application service is not available", severity="error", timeout=3)
            return
            
        job = self._get_job_data(job_id)
        
        if not job:
            self.notify("Could not find job to mark as applied", severity="error", timeout=3)
            return
        
        try:
            # Check if an application already exists for this job
            existing_application = self.application_service.by_job_id(job_id)
            
            if existing_application:
                self.notify(f"This job was already marked as applied on {existing_application.application_date.strftime('%Y-%m-%d')}", 
                        severity="warning", timeout=3)
                return
                
            # Create context for logging
            context = {
                "screen": "JobsScreen",
                "method": "_mark_applied_callback",
                "job_id": job_id,
                "company_id": job.company_id,
                "company": job.company,
                "title": job.title
            }
            
            # Log the attempt
            Slogger.info(f"Attempting to mark job '{job.title}' at '{job.company}' as applied", context)
            
            # Create a new application record
            application = self.application_service.add(job_id=job_id, notes="Applied via job actions modal")
            
            if application:
                # Add entry to history table (using SQL directly since there's no specific repo)
                conn = self.job_service._jobs._db
                cursor = conn.cursor()
                
                try:
                    # First check if the history table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
                    if not cursor.fetchone():
                        Slogger.warning("History table does not exist, creating it", context)
                        # Create the history table if it doesn't exist
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS history (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                company_id TEXT NOT NULL,
                                job_id TEXT,
                                application_id TEXT,
                                action TEXT NOT NULL,
                                timestamp TEXT NOT NULL
                            )
                        """)
                        conn.commit()
                    
                    # Verify company_id is not None
                    if not job.company_id:
                        Slogger.warning(f"Missing company_id for job {job_id}, using placeholder", context)
                        company_id = "unknown"
                    else:
                        company_id = job.company_id
                        
                    # Now insert the history entry
                    cursor.execute(
                        "INSERT INTO history (company_id, action, application_id, job_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (
                            company_id,
                            "applied",
                            application.id,
                            job_id,
                            application.application_date.isoformat()
                        )
                    )
                    conn.commit()
                    Slogger.info(f"Added history entry for application ID: {application.id}", context)
                except Exception as e:
                    error_msg = f"Error adding history entry: {str(e)}"
                    Slogger.exception(e, error_msg, context)
                    # Continue even if history entry fails, as the application was created successfully
                
                Slogger.info(f"Successfully marked job '{job.title}' at '{job.company}' as applied", 
                           {**context, "application_id": application.id})
                           
                self.notify(f"Job '{job.company} - {job.title}' marked as applied successfully", 
                        severity="information", timeout=3)
                
                # Refresh the job list to update the applied status column
                self.load_jobs()
                
                # Chat panel update code preserved but disabled
                # since the panel is not currently in the UI
                # Update chat panel with the new status
                # try:
                #     chat_panel = self.query_one("#chat-panel", expect_type=ChatPanel)
                #     chat_panel.add_assistant_message(f"Job marked as applied: {job.company} - {job.title}")
                # except Exception:
                #     pass  # Chat panel not in the UI
            else:
                error_msg = f"Failed to mark job '{job.title}' at '{job.company}' as applied - application service returned None"
                Slogger.error(error_msg, context)
                
                # Provide a more informative error message
                self.notify(
                    "Failed to mark job as applied. Check logs for details.", 
                    severity="error", 
                    timeout=5
                )
        except Exception as e:
            error_context = {
                "screen": "JobsScreen",
                "method": "_mark_applied_callback",
                "job_id": job_id,
                "company": job.company if job else "unknown",
                "title": job.title if job else "unknown"
            }
            
            Slogger.exception(e, f"Exception occurred while marking job as applied", error_context)
            
            # Provide a more detailed error message to the user
            error_type = type(e).__name__
            self.notify(
                f"Error marking job as applied: {error_type} - {str(e)}", 
                severity="error", 
                timeout=5
            )