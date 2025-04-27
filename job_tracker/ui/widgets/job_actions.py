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
        """
        super().__init__(id=id, name=name, classes=classes)
        self.job_title = job_title
        self.company_name = company_name
        self.job_id = job_id
        self.hide_callback = hide_callback
        self.delete_callback = delete_callback

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
                yield Button("Hide Job", variant="warning", id="hide-job-button")
                yield Button("Delete Job", variant="error", id="delete-job-button")  # Add delete button
            
            # Close button
            with Container(id="action-buttons"):
                yield Button("Close", variant="primary", id="close-button")
                
        yield Footer()


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "close-button":
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