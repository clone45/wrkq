"""
Pagination widget for navigating through job results
"""

from typing import Optional

from rich.text import Text
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Button, Label
from textual.message import Message


class Pagination(Container):
    """
    Pagination widget with first, prev, next, last buttons
    """
    
    DEFAULT_CSS = """
    Pagination {
        layout: horizontal;
        height: 3;
        content-align: center middle;
        padding: 1 0;
    }
    
    Pagination > Button {
        min-width: 5;
        margin: 0 1;
    }
    
    Pagination > #page-indicator {
        min-width: 15;
        content-align: center middle;
    }
    """
    
    current_page = reactive(1)
    total_pages = reactive(1)
    
    class PageChanged(Message):
        """Page changed message"""
        def __init__(self, page: int) -> None:
            super().__init__()
            self.page = page
    
    def __init__(
        self,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the Pagination widget
        
        Args:
            id: Optional widget ID
            classes: Optional CSS classes
        """
        super().__init__(id=id, classes=classes)
    
    def compose(self):
        """Create child widgets"""
        yield Button("« First", id="first-page", classes="page-button")
        yield Button("< Prev", id="prev-page", classes="page-button")
        yield Label(f"Page [b]1[/b] of [b]1[/b]", id="page-indicator", classes="page-indicator")
        yield Button("Next >", id="next-page", classes="page-button")
        yield Button("Last »", id="last-page", classes="page-button")
    
    def on_mount(self) -> None:
        """Set up watchers when mounted"""
        self.update_pages(self.current_page, self.total_pages)
    
    def update_pages(self, current: int, total: int) -> None:
        """
        Update pagination with new page information
        
        Args:
            current: Current page number
            total: Total pages
        """
        self.current_page = current
        self.total_pages = total
        
        # Update the page indicator
        page_indicator = self.query_one("#page-indicator", Label)
        page_indicator.update(f"Page [b]{current}[/b] of [b]{total}[/b]")
        
        # Update button states
        first_btn = self.query_one("#first-page", Button)
        prev_btn = self.query_one("#prev-page", Button)
        next_btn = self.query_one("#next-page", Button)
        last_btn = self.query_one("#last-page", Button)
        
        # Disable buttons if at first/last page
        first_btn.disabled = prev_btn.disabled = (current <= 1)
        next_btn.disabled = last_btn.disabled = (current >= total)
    
    def watch_current_page(self, current_page: int) -> None:
        """React to changes in current_page reactive"""
        self.update_pages(current_page, self.total_pages)
    
    def watch_total_pages(self, total_pages: int) -> None:
        """React to changes in total_pages reactive"""
        self.update_pages(self.current_page, total_pages)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle pagination button presses"""
        button_id = event.button.id
        new_page = self.current_page
        
        if button_id == "first-page":
            new_page = 1
        elif button_id == "last-page":
            new_page = self.total_pages
        elif button_id == "prev-page" and self.current_page > 1:
            new_page = self.current_page - 1
        elif button_id == "next-page" and self.current_page < self.total_pages:
            new_page = self.current_page + 1
        
        if new_page != self.current_page:
            self.current_page = new_page
            self.post_message(self.PageChanged(new_page))