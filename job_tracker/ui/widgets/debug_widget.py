# job_tracker/ui/widgets/debug_widget.py
"""A simple debug widget to test visibility issues."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Label, Button


class DebugWidget(Widget):
    """A very simple widget that should always be visible."""
    
    def __init__(self) -> None:
        """Initialize the debug widget."""
        super().__init__()
    
    def compose(self) -> ComposeResult:
        """Compose the debug widget with a visible label."""
        with Container(id="debug-container"):
            yield Label("===== DEBUG WIDGET =====", id="debug-label")
            yield Button("Debug Button", id="debug-button")