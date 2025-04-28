"""
Loading indicator widget for showing progress during async operations.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Static, LoadingIndicator


class LoadingOverlay(Static):
    """A loading indicator overlay that can be shown over content."""
    
    # Reactive state to control visibility
    is_loading = reactive(False)
    message = reactive("Loading...")
    
    def __init__(
        self,
        message: str = "Loading...",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        """
        Initialize the loading overlay.
        
        Args:
            message: Message to display while loading
            name: Optional widget name
            id: Optional widget ID
            classes: Optional CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.message = message
        self.is_loading = False
    
    def compose(self) -> ComposeResult:
        """Compose the loading overlay."""
        with Container(id="loading-container"):
            yield LoadingIndicator()
            yield Static(self.message, id="loading-message")
    
    def watch_is_loading(self, is_loading: bool) -> None:
        """Watch for changes to loading state and update visibility."""
        self.display = is_loading
    
    def watch_message(self, message: str) -> None:
        """Watch for changes to the message and update the text."""
        if self.is_mounted:
            self.query_one("#loading-message", Static).update(message)
    
    def start(self, message: str | None = None) -> None:
        """Start the loading indicator with an optional new message."""
        if message:
            self.message = message
        self.is_loading = True
    
    def stop(self) -> None:
        """Stop the loading indicator."""
        self.is_loading = False