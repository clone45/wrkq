# job_tracker/ui/screens/add_job_screen.py

from typing import Dict, Any, Optional
from datetime import datetime

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import VerticalScroll, Container, Vertical
from textual.widgets import (
    Label,
    Input,
    Button,
    Static,
    TextArea,
    Switch # Consider for 'Hidden' flag? Maybe later.
)
from textual import events
from textual import log # For debugging

from job_tracker.db.connection import MongoDBConnection
from bson import ObjectId # Import ObjectId

class AddJobScreen(ModalScreen[Optional[Dict[str, Any]]]): # Return the added job dict or None
    """Modal screen for adding a new job."""

    CSS_PATH = "../css/add_job_screen.tcss"

    def __init__(
        self,
        mongodb: MongoDBConnection,
        user_id: ObjectId, # Pass the current user's ID
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.mongodb = mongodb
        self.user_id = user_id
        if not user_id:
             # This should not happen if called correctly from app
             log.error("AddJobScreen initialized without a user_id!")


    def compose(self) -> ComposeResult:
        with Vertical(id="add-job-dialog"):
            yield Label("Add New Job Application", id="add-job-title")
            with VerticalScroll(id="add-job-form"):
                yield Label("Company Name *")
                yield Input(placeholder="e.g., Acme Corp", id="add-job-company")

                yield Label("Job Title *")
                yield Input(placeholder="e.g., Software Engineer", id="add-job-title-input") # Renamed ID

                yield Label("Location")
                yield Input(placeholder="e.g., San Francisco, CA or Remote", id="add-job-location")

                yield Label("Salary")
                yield Input(placeholder="e.g., $100k-$120k or $50/hr", id="add-job-salary")

                yield Label("Job Posting Link")
                yield Input(placeholder="https://...", id="add-job-link")

                yield Label("Source")
                yield Input(placeholder="e.g., LinkedIn, Indeed, Company Website", id="add-job-source")

                yield Label("Posting Date (YYYY-MM-DD)")
                yield Input(placeholder=datetime.now().strftime('%Y-%m-%d'), id="add-job-date", value=datetime.now().strftime('%Y-%m-%d'))

                yield Label("Notes / Description Snippet")
                yield TextArea(language="markdown", id="add-job-notes", classes="add-job-notes-area")

            with Container(id="add-job-buttons"):
                yield Button("Save Job", variant="success", id="add-job-save")
                yield Button("Cancel", variant="error", id="add-job-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "add-job-save":
            self.action_submit()
        elif event.button.id == "add-job-cancel":
            self.app.pop_screen() # Simple dismiss for cancel

    def action_submit(self) -> None:
        """Process and save the job."""
        log("Submit action triggered") # Debug log

        # --- Get Data from Inputs ---
        company_input = self.query_one("#add-job-company", Input)
        title_input = self.query_one("#add-job-title-input", Input)
        location_input = self.query_one("#add-job-location", Input)
        salary_input = self.query_one("#add-job-salary", Input)
        link_input = self.query_one("#add-job-link", Input)
        source_input = self.query_one("#add-job-source", Input)
        date_input = self.query_one("#add-job-date", Input)
        notes_area = self.query_one("#add-job-notes", TextArea)

        company_name = company_input.value.strip()
        job_title = title_input.value.strip()

        # --- Basic Validation ---
        errors = []
        if not company_name:
            errors.append("Company Name is required.")
            company_input.border_title = "REQUIRED"
            company_input.styles.border = ("heavy", "red")
        else:
            company_input.border_title = None
            company_input.styles.border = None # Reset style

        if not job_title:
            errors.append("Job Title is required.")
            title_input.border_title = "REQUIRED"
            title_input.styles.border = ("heavy", "red")
        else:
            title_input.border_title = None
            title_input.styles.border = None # Reset style

        if errors:
            self.notify(", ".join(errors), title="Validation Error", severity="error", timeout=5)
            log.warning(f"Validation errors: {errors}") # Debug log
            return # Stop submission

        log("Validation passed") # Debug log

        # --- Process Company ---
        if not self.user_id:
             self.notify("User ID is missing. Cannot save job.", title="Internal Error", severity="error")
             log.error("Cannot save job: user_id is missing.")
             return

        log(f"Finding/creating company '{company_name}' for user '{self.user_id}'") # Debug log
        company_id = self.mongodb.find_or_create_company(company_name, self.user_id)

        if not company_id:
            self.notify(f"Failed to find or create company '{company_name}'.", title="Database Error", severity="error")
            log.error(f"Failed to get company_id for '{company_name}'") # Debug log
            return # Stop submission

        log(f"Obtained company_id: {company_id}") # Debug log

        # --- Prepare Job Data ---
        new_job_data = {
            "user_id": self.user_id,
            "company": company_name, # Store original casing for display
            "company_id": company_id,
            "title": job_title,
            "location": location_input.value.strip() or None, # Use None if empty
            "salary": salary_input.value.strip() or None,
            "details_link": link_input.value.strip() or None,
            "site_name": source_input.value.strip() or None,
            "posting_date": date_input.value.strip() or datetime.now().strftime('%Y-%m-%d'),
            "job_description": notes_area.text or None, # Get text from TextArea
            "hidden": False, # Default
            # "job_id": None, # Often comes from scraping, maybe generate one? Optional.
            # "slug": None, # Can be generated later if needed
        }

        log(f"Attempting to add job: {new_job_data}") # Debug log

        # --- Add Job to DB ---
        new_job_id = self.mongodb.add_job(new_job_data)

        if new_job_id:
            self.notify("Job added successfully!", title="Success", severity="information")
            log(f"Job added with ID: {new_job_id}") # Debug log
            # Add the new _id to the dictionary before returning
            new_job_data['_id'] = new_job_id
            self.dismiss(new_job_data) # Dismiss and return the added job data
        else:
            self.notify("Failed to save job to database.", title="Database Error", severity="error")
            log.error("mongodb.add_job returned None") # Debug log