# Create a new file: job_tracker/ui/widgets/confirmation_modal.py
"""
Modal widget for confirmations.
"""

from __future__ import annotations

from typing import Callable, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmationModal(ModalScreen):
    """Modal screen for confirming actions."""

    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    def __init__(
        self, 
        title: str,
        message: str,
        on_yes: Callable[[], None],
        on_no: Optional[Callable[[], None]] = None,
        *,
        id: str | None = None,
        name: str | None = None,
        classes: str | None = None,
    ):
        """
        Initialize the confirmation modal.
        
        Args:
            title: Title of the confirmation dialog
            message: Message to display
            on_yes: Callback function when Yes is clicked
            on_no: Optional callback function when No is clicked
        """
        super().__init__(id=id, name=name, classes=classes)
        self.title_text = title
        self.message = message
        self.on_yes = on_yes
        self.on_no = on_no

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        # Main content
        with Container(id="confirmation-container"):
            yield Label(self.title_text, id="confirmation-title")
            yield Label(self.message, id="confirmation-message")
            
            # Buttons
            with Horizontal(id="confirmation-buttons"):
                yield Button("Cancel", variant="primary", id="no-button")
                yield Button("Delete", variant="error", id="yes-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "no-button":
            if self.on_no:
                self.on_no()
            self.dismiss()
        elif button_id == "yes-button":
            self.on_yes()
            self.dismiss()
    
    def action_confirm(self) -> None:
        """Handle Enter key press."""
        self.on_yes()
        self.dismiss()