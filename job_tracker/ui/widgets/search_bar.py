"""
Search bar widget for job filtering
"""

from typing import Optional

from textual.containers import Container
from textual.widgets import Button, Input
from textual.message import Message


class SearchBar(Container):
    """
    Search bar widget with input and button
    """
    
    class Submitted(Message):
        """Search submitted message"""
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query
    
    def __init__(
        self,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the SearchBar
        
        Args:
            id: Optional widget ID
            classes: Optional CSS classes
        """
        super().__init__(id=id, classes=classes)
        self._query = ""
    
    def compose(self):
        """Create child widgets"""
        yield Input(placeholder="Search jobs by company, title or location...", id="search-input")
        yield Button("Search", id="search-btn")
    
    @property
    def query(self) -> str:
        """Get the current search query"""
        return self._query
    
    def focus_input(self) -> None:
        """Focus the search input"""
        self.query_one("#search-input", Input).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle search button press"""
        if event.button.id == "search-btn":
            self._submit_search()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Enter key)"""
        if event.input.id == "search-input":
            self._submit_search()
    
    def _submit_search(self) -> None:
        """Submit the search query"""
        input_widget = self.query_one("#search-input", Input)
        self._query = input_widget.value
        self.post_message(self.Submitted(self._query))