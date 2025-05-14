# harvest/interfaces/progress.py

from typing import Dict, Any, List, Optional

class ProgressDisplay:
    """Interface for displaying progress information."""
    
    def initialize(self) -> None:
        """Initialize the progress display."""
        raise NotImplementedError("Subclasses must implement this method")
        
    def update(self, **stats: Any) -> None:
        """
        Update the progress display with new statistics.
        
        Args:
            **stats: Key-value pairs of statistics to update
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def add_event(self, event_type: str, message: str) -> None:
        """
        Add an event to the recent events list.
        
        Args:
            event_type: Type of event
            message: Description of the event
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def finalize(self) -> None:
        """Finalize the progress display and show summary statistics."""
        raise NotImplementedError("Subclasses must implement this method")