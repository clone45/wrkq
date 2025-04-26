"""
Custom DataTable widget for displaying jobs
"""

from typing import Any, Optional

from rich.text import Text
from textual.widgets import DataTable
from textual.message import Message


class JobTable(DataTable):
    """
    Enhanced DataTable for job listings with custom row selection
    """
    
    class RowSelected(Message):
        """Row selected message"""
        def __init__(self, row_key) -> None:
            super().__init__()
            self.row_key = row_key
    
    def __init__(
        self,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the JobTable
        
        Args:
            id: Optional widget ID
            classes: Optional CSS classes
        """
        super().__init__(id=id, classes=classes)
        self.cursor_type = "row"
        self.zebra_stripes = True
    
    def on_mount(self) -> None:
        """Set up the widget when mounted"""
        self.add_class("jobs-table")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Handle row selection and emit custom event
        
        Args:
            event: DataTable row selected event
        """
        # Forward the event with our custom message type
        self.post_message(self.RowSelected(event.row_key))