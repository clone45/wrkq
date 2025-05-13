"""
Modal widget for job actions.
"""

from __future__ import annotations

from typing import Callable, Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Header, Label, Footer


class JobActionsModal(ModalScreen):
    """Modal screen for displaying and selecting job actions."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
    ]

    def __init__(
        self, 
        job_title: str,
        company_name: str,
        job_id: str,
        hide_callback: Callable[[str], None],
        delete_callback: Callable[[str], None],
        mark_applied_callback: Callable[[str], None],
        update_status_callback: Optional[Callable[[str, str], None]] = None,
        *,
        id: str | None = None,
        name: str | None = None,
        classes: str | None = None,
    ):
        """
        Initialize the modal with job details.
        
        Args:
            job_title: Title of the selected job
            company_name: Name of the company for the selected job
            job_id: ID of the selected job
            hide_callback: Callback function to hide a job
            delete_callback: Callback function to delete a job
            mark_applied_callback: Callback function to mark a job as applied
        """
        super().__init__(id=id, name=name, classes=classes)
        self.job_title = job_title
        self.company_name = company_name
        self.job_id = job_id
        self.hide_callback = hide_callback
        self.delete_callback = delete_callback
        self.mark_applied_callback = mark_applied_callback
        self.update_status_callback = update_status_callback

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        # Header
        yield Header()
        
        # Main content
        with Container(id="job-actions-container"):
            yield Label(f"Actions for: {self.company_name} - {self.job_title}", 
                    id="job-actions-title")
            
            # Actions list
            with Vertical(id="actions-list"):
                yield Button("Mark Applied", variant="success", id="mark-applied-button")
                
                # Status update buttons
                with Vertical(id="status-buttons"):
                    yield Label("Update Status:", id="status-label")
                    yield Button("Interested", variant="primary", id="status-interested-button")
                    yield Button("Applied", variant="primary", id="status-applied-button")
                    yield Button("Interviewing", variant="primary", id="status-interviewing-button")
                    yield Button("Offered", variant="primary", id="status-offered-button")
                    yield Button("Rejected", variant="primary", id="status-rejected-button")
                    yield Button("Clear Status", variant="primary", id="status-clear-button")
                
                yield Button("Hide Job", variant="warning", id="hide-job-button")
                yield Button("Delete Job", variant="error", id="delete-job-button")
            
            # Close button
            with Container(id="action-buttons"):
                yield Button("Close", variant="primary", id="close-button")
                
        yield Footer()


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "close-button":
            self.dismiss()
        elif button_id == "mark-applied-button":
            # Call the mark applied callback
            self.mark_applied_callback(self.job_id)
            # Close the modal after action
            self.dismiss()
        elif button_id == "hide-job-button":
            # Call the hide job callback
            self.hide_callback(self.job_id)
            # Close the modal after action
            self.dismiss()
        elif button_id == "delete-job-button":
            # Call the delete job callback
            self.delete_callback(self.job_id)
            # Close the modal after action
            self.dismiss()
        # Handle status update buttons
        elif button_id.startswith("status-") and self.update_status_callback:
            # Extract status value from button ID
            status_value = button_id.replace("status-", "").replace("-button", "")
            
            # For "clear" status, set to None
            if status_value == "clear":
                status_value = None
                
            # Call the status update callback
            self.update_status_callback(self.job_id, status_value)
            # Close the modal after action
            self.dismiss()