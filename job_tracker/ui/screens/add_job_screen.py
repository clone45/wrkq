"""
Screen for adding a new job application to the system.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, Optional, List

from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Header, Footer, Input, Label, TextArea, Static, Select
from textual import log
from textual.worker import Worker, WorkerState

from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.company_repo import CompanyRepo
from job_tracker.services.openai_service import OpenAIService
from job_tracker.services.job_extractor_service import JobExtractorService
from job_tracker.models.job import Job
from job_tracker.ui.widgets.loading_indicator import LoadingOverlay
from simple_logger import Slogger

class AddJobScreen(Screen):
    """Full-screen interface for adding a new job application."""

    BINDINGS = [
        ("escape", "go_back", "Back to Jobs"),
        ("ctrl+s", "submit", "Save Job"),
        ("f1", "toggle_help", "Toggle Help"),
    ]

    def __init__(
        self,
        job_repo: JobRepo,
        company_repo: CompanyRepo,
        job_extractor_service,
        openai_service: Optional[Any] = None,  # Keep for backward compatibility
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        """
        Initialize the AddJobScreen with required dependencies.
        
        Args:
            job_repo: Repository for job operations
            company_repo: Repository for company operations
            job_extractor_service: Service for extracting job info from URLs
            openai_service: Legacy service (kept for backward compatibility)
        """
        super().__init__(name=name, id=id, classes=classes)
        self.job_repo = job_repo
        self.company_repo = company_repo
        self.job_extractor_service = job_extractor_service
        self.openai_service = openai_service  # Kept for backward compatibility
        self.show_help = False
        
        # Common sources for job listings
        self.sources = [
            "LinkedIn",
            "Indeed",
            "Company Website",
            "Glassdoor",
            "ZipRecruiter",
            "Referral",
            "Job Fair",
            "Other"
        ]

    def compose(self) -> ComposeResult:
        """Compose the screen widgets."""
        # Header with title
        yield Header(show_clock=True)
        
        # Main content container
        with Container(id="add-job-container"):
            # Title section
            with Container(id="add-job-title-section"):
                yield Label("Add New Job Application", id="page-title", classes="heading")
                yield Label("Enter the details of the job you're applying for", classes="subheading")
            
            # URL input bar with import button at the top
            with Container(id="url-input-container"):
                yield Label("Job Posting URL", classes="input-label")
                with Horizontal(id="url-input-row"):
                    yield Input(placeholder="https://... (paste job posting URL here)", id="job-url")
                    yield Button("Import", variant="primary", id="import-button")
            
            # Main form content in two columns
            with Grid(id="form-grid"):
                # Left column - core job details
                with Container(id="left-column", classes="form-column"):
                    yield Label("Job Details", classes="section-title")
                    
                    # Company info
                    yield Label("Company Name *", classes="input-label")
                    yield Input(placeholder="e.g., Acme Corporation", id="company-name")
                    
                    # Job title
                    yield Label("Job Title *", classes="input-label")
                    yield Input(placeholder="e.g., Software Engineer", id="job-title")
                    
                    # Location
                    yield Label("Location", classes="input-label")
                    yield Input(placeholder="e.g., San Francisco, CA or Remote", id="job-location")
                    
                    # Salary
                    yield Label("Salary", classes="input-label")
                    yield Input(placeholder="e.g., $100,000 - $120,000 or $50/hr", id="job-salary")
                    
                    # Source dropdown
                    yield Label("Source", classes="input-label")
                    yield Select(
                        ((source, source) for source in self.sources),
                        id="job-source",
                        prompt="Select or type a source"
                    )
                
                # Right column - dates, description, notes
                with Container(id="right-column", classes="form-column"):
                    yield Label("Additional Information", classes="section-title")
                    
                    # Posting date
                    yield Label("Posting Date", classes="input-label")
                    yield Input(
                        placeholder=datetime.now().strftime('%Y-%m-%d'), 
                        id="posting-date", 
                        value=datetime.now().strftime('%Y-%m-%d')
                    )
                    
                    # Job description
                    yield Label("Job Description", classes="input-label")
                    yield TextArea(
                        id="job-description",
                        classes="description-area"
                    )
                
            # Help panel (hidden by default)
            yield Static("", id="help-panel")
            
            # Action buttons
            with Horizontal(id="action-buttons"):
                yield Button("Cancel", variant="primary", id="cancel-button")
                yield Button("Save Job", variant="success", id="save-button")
                
            # Loading overlay (hidden by default)
            yield LoadingOverlay(id="loading-overlay", message="Fetching job details...")
        
        # Footer with key bindings
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        # Focus the URL input field first
        self.query_one("#job-url").focus()
        
        # Set up the help panel content but hide it initially
        help_panel = self.query_one("#help-panel", Static)
        help_panel.update(self._get_help_text())
        help_panel.display = False
        
        # Add a placeholder instruction to the job description field
        description_area = self.query_one("#job-description", TextArea)
        description_area.text = "Paste the job description here..."
        
        # Hide the loading overlay initially
        loading_overlay = self.query_one(LoadingOverlay)
        loading_overlay.display = False
    
    def _get_help_text(self) -> str:
        """Generate the help text content."""
        return """
        # Adding a New Job Application
        
        Fill in the form with details about the job you're applying for.
        
        ## Required Fields
        - Company Name: The name of the company offering the position
        - Job Title: The title or role you're applying for
        
        ## Quick Import
        - Paste a LinkedIn job posting URL at the top and click Import to auto-fill fields
        - The app will fetch and extract job details automatically
        
        ## Tips
        - For remote positions, you can specify "Remote" or "Remote - US" etc.
        - Include salary information when available for future reference
        - Paste the full job description to keep all details for reference
        - LinkedIn URLs work best with the automatic import feature
        
        Press Escape to cancel or Ctrl+S to save the job.
        """
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "cancel-button":
            self.action_go_back()
        elif button_id == "save-button":
            self.action_submit()
        elif button_id == "import-button":
            self.import_job_from_url()

    def import_job_from_url(self) -> None:
        """Handle importing job details from URL."""
        url = self.query_one("#job-url").value.strip()
        
        if not url:
            self.notify("Please enter a URL to import", title="Info", severity="warning")
            return
            
        # Show loading overlay
        loading_overlay = self.query_one(LoadingOverlay)
        loading_overlay.start("Fetching job details... This may take a few seconds.")
        
        # Start background worker to handle API call
        worker = self.run_worker(self.extract_job_info(url), group="import_job")
        
    async def extract_job_info(self, url: str) -> Dict[str, Any]:
        """
        Extract job information from URL using the job extractor service.
        
        Args:
            url: The URL to extract job info from
            
        Returns:
            Dictionary containing job details
        """
        try:
            # Call the job extractor service
            job_info = await self.job_extractor_service.extract_job_info(url)
            
            # Handle structured error response
            if "error" in job_info and job_info["error"]:
                # Get error message
                error_msg = job_info.get("message", "Unknown error extracting job information")
                
                # Log the error with method if available
                method = job_info.get("extraction_method", "unknown")
                Slogger.log(f"Error extracting job info via {method}: {error_msg}")
                
                # Hide loading overlay
                loading_overlay = self.query_one(LoadingOverlay)
                loading_overlay.stop()
                
                # Provide a more helpful error message for URL validation issues
                if "Invalid LinkedIn URL" in error_msg:
                    error_msg = "Could not process this URL. Please make sure it's a valid LinkedIn job posting URL."
                
                # Show error to user
                self.notify(
                    error_msg,
                    title="Extraction Failed",
                    severity="warning"
                )
                return {}
            
            if not job_info:
                # No job information extracted
                Slogger.log(f"No job information could be extracted from URL: {url}")
                
                # Hide loading overlay
                loading_overlay = self.query_one(LoadingOverlay)
                loading_overlay.stop()
                
                self.notify(
                    "Could not extract job information from the provided URL.",
                    title="Extraction Failed",
                    severity="warning"
                )
                return {}
            
            # Log extraction method if available
            if "extraction_method" in job_info:
                Slogger.log(f"Job info extracted using: {job_info['extraction_method']}")
            
            # Update form fields with extracted info
            self.populate_form_with_job_info(job_info)
            
            # Hide loading overlay
            loading_overlay = self.query_one(LoadingOverlay)
            loading_overlay.stop()
            
            self.notify("Job information imported successfully!", title="Success", severity="information")
            
            return job_info
            
        except Exception as e:
            # Hide loading overlay
            loading_overlay = self.query_one(LoadingOverlay)
            loading_overlay.stop()
            
            Slogger.log(f"Error importing job: {repr(e)}")
            self.notify(f"Error importing job: {str(e)}", title="Error", severity="error")
            
            return {}
    
    def populate_form_with_job_info(self, job_info: Dict[str, Any]) -> None:
        """
        Populate form fields with extracted job information.
        
        Args:
            job_info: Dictionary containing job details
        """
        # Update company name
        if "company" in job_info and job_info["company"]:
            self.query_one("#company-name", Input).value = job_info["company"]
            
        # Update job title
        if "title" in job_info and job_info["title"]:
            self.query_one("#job-title", Input).value = job_info["title"]
            
        # Update location
        if "location" in job_info and job_info["location"]:
            self.query_one("#job-location", Input).value = job_info["location"]
            
        # Update salary
        if "salary" in job_info and job_info["salary"]:
            self.query_one("#job-salary", Input).value = job_info["salary"]
            
        # Update source
        if "source" in job_info and job_info["source"]:
            source = job_info["source"]
            # Find the closest match in our sources list
            if source in self.sources:
                self.query_one("#job-source", Select).value = source
            else:
                # Default to "Other" if not in our list
                self.query_one("#job-source", Select).value = "Other"
                
        # Update posting date
        if "posting_date" in job_info and job_info["posting_date"]:
            try:
                date_obj = job_info["posting_date"]
                if isinstance(date_obj, datetime):
                    date_str = date_obj.strftime('%Y-%m-%d')
                    self.query_one("#posting-date", Input).value = date_str
            except Exception as e:
                Slogger.log(f"Error formatting posting date: {e}")
                
        # Update job description
        if "description" in job_info and job_info["description"]:
            self.query_one("#job-description", TextArea).text = job_info["description"]
    
    def action_go_back(self) -> None:
        """Return to the jobs screen."""
        self.app.pop_screen()
    
    def action_toggle_help(self) -> None:
        """Toggle the visibility of the help panel."""
        help_panel = self.query_one("#help-panel")
        self.show_help = not self.show_help
        help_panel.display = self.show_help
    
    def action_submit(self) -> None:
        """Validate and save the job application."""
        # Get values from form fields
        company_name = self.query_one("#company-name", Input).value.strip()
        job_title = self.query_one("#job-title", Input).value.strip()
        location = self.query_one("#job-location", Input).value.strip()
        salary = self.query_one("#job-salary", Input).value.strip()
        source = self.query_one("#job-source", Select).value
        job_url = self.query_one("#job-url", Input).value.strip()
        posting_date_str = self.query_one("#posting-date", Input).value.strip()
        job_description = self.query_one("#job-description", TextArea).text
        
        # Clear placeholder text if it's still there
        if job_description == "Paste the job description here...":
            job_description = ""
        
        # Validate required fields
        errors: List[str] = []
        
        if not company_name:
            errors.append("Company Name is required")
            self._mark_field_error("#company-name")
        
        if not job_title:
            errors.append("Job Title is required")
            self._mark_field_error("#job-title")
        
        # Validate date format
        posting_date = None
        try:
            if posting_date_str:
                posting_date = datetime.strptime(posting_date_str, '%Y-%m-%d')
            else:
                posting_date = datetime.now()
        except ValueError:
            errors.append("Invalid date format. Use YYYY-MM-DD")
            self._mark_field_error("#posting-date")
        
        # If validation failed, show error and return
        if errors:
            error_message = ", ".join(errors)
            self.notify(error_message, title="Validation Error", severity="error")
            return
        
        # Find or create company
        try:
            company = self.company_repo.find_or_create(company_name=company_name)
            company_id = str(company.id) if company else None
            
            if not company_id:
                self.notify(
                    f"Failed to create company record for '{company_name}'", 
                    title="Database Error", 
                    severity="error"
                )
                return
                
        except Exception as e:
            log.error(f"Error creating company: {e}")
            self.notify(
                f"Failed to create company: {str(e)}", 
                title="Database Error", 
                severity="error"
            )
            return
        
        # Create new job object
        new_job = Job(
            id="",  # This will be assigned by SQLite
            company_id=company_id,
            company=company_name,
            title=job_title,
            location=location or "",
            posting_date=posting_date,
            salary=salary or None,
            hidden=False,
            hidden_date=None,
            created_at=datetime.now(),
            job_description=job_description or None,
            site_name=source,
            details_link=job_url
        )
        
        # Save to database
        try:
            saved_job = self.job_repo.add(new_job)
            
            if saved_job:
                self.notify(
                    f"Successfully added job: {job_title} at {company_name}",
                    title="Success",
                    severity="information"
                )
                
                # Log the saved job before dismissing
                Slogger.log(f"Dismissing screen with saved job ID: {saved_job.id}")

                self.app.pop_screen()
                

            else:
                self.notify(
                    "Failed to save job to database",
                    title="Database Error", 
                    severity="error"
                )

        except Exception as e:
            Slogger.log(f"Error saving job: {repr(e)}")
            self.notify(
                f"Error saving job: {str(e)}",
                title="Database Error", 
                severity="error"
            )
    
    def _mark_field_error(self, selector: str) -> None:
        """Mark a field as having an error."""
        widget = self.query_one(selector)
        widget.add_class("input-error")
        
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        group = event.worker.group
        state = event.state
        
        if group == "import_job":
            if state == WorkerState.ERROR:
                # Handle worker error
                loading_overlay = self.query_one(LoadingOverlay)
                loading_overlay.stop()
                
                exception = event.worker.error
                error_message = str(exception) if exception else "Unknown error"
                
                self.notify(
                    f"Error importing job: {error_message}",
                    title="Error",
                    severity="error"
                )
                
                Slogger.log(f"Worker error: {repr(exception)}")
            
            elif state == WorkerState.CANCELLED:
                # Handle worker cancellation
                loading_overlay = self.query_one(LoadingOverlay)
                loading_overlay.stop()
                
                self.notify(
                    "Job import cancelled",
                    title="Info",
                    severity="warning"
                )