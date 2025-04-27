"""
Screen for adding a new job application to the system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional, List

from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Header, Footer, Input, Label, TextArea, Static, Select
from textual import log

from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.company_repo import CompanyRepo
from job_tracker.models.job import Job
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
        """
        super().__init__(name=name, id=id, classes=classes)
        self.job_repo = job_repo
        self.company_repo = company_repo
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
                    
                    # Job URL/Link
                    yield Label("Job Posting URL", classes="input-label")
                    yield Input(placeholder="https://...", id="job-url")
                
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
                    # Removed placeholder parameter which isn't supported
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
        
        # Footer with key bindings
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        # Focus the first input field
        self.query_one("#company-name").focus()
        
        # Set up the help panel content but hide it initially
        help_panel = self.query_one("#help-panel", Static)
        help_panel.update(self._get_help_text())
        help_panel.display = False
        
        # Add a placeholder instruction to the job description field
        description_area = self.query_one("#job-description", TextArea)
        description_area.text = "Paste the job description here..."
    
    def _get_help_text(self) -> str:
        """Generate the help text content."""
        return """
        # Adding a New Job Application
        
        Fill in the form with details about the job you're applying for.
        
        ## Required Fields
        - Company Name: The name of the company offering the position
        - Job Title: The title or role you're applying for
        
        ## Tips
        - For remote positions, you can specify "Remote" or "Remote - US" etc.
        - Include salary information when available for future reference
        - Paste the full job description to keep all details for reference
        
        Press Escape to cancel or Ctrl+S to save the job.
        """
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "cancel-button":
            self.action_go_back()
        elif button_id == "save-button":
            self.action_submit()
    
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