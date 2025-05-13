# job_tracker/ui/widgets/task_tray.py
"""Collapsible tray for monitoring background tasks."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime

from rich.console import RenderableType
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Static, Label
from textual.widget import Widget


class TaskItem(Static):
    """Represents a single background task with progress information."""
    
    task_id = reactive("task_id")
    task_type = reactive("task_type")
    status = reactive("status")
    progress_value = reactive(0)
    progress_total = reactive(100)
    message = reactive("")
    created_time = reactive(datetime.now())
    
    def __init__(
        self,
        task_id: str,
        task_type: str,
        status: str,
        *,
        progress_value: int = 0,
        progress_total: int = 100,
        message: str = "",
        created_time: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a task item widget."""
        super().__init__("", **kwargs)
        self.task_id = task_id
        self.task_type = task_type
        self.status = status
        self.progress_value = progress_value
        self.progress_total = progress_total
        self.message = message
        self.created_time = created_time or datetime.now()
    
    def watch_status(self, status: str) -> None:
        """Watch for status changes and update the display."""
        self.refresh()
    
    def watch_progress_value(self, progress_value: int) -> None:
        """Watch for progress changes and update the display."""
        self.refresh()
    
    def watch_message(self, message: str) -> None:
        """Watch for message changes and update the display."""
        self.refresh()
    
    def render(self) -> RenderableType:
        """Render the task item with a progress bar."""
        # Simplified rendering to avoid rich.panel issues
        task_type_display = "URL Import" if self.task_type == "job_fetch" else "Job Search"
        
        # Format the status display
        if self.status == "pending":
            status_str = "[yellow]Pending[/yellow]"
        elif self.status == "in_progress":
            status_str = "[blue]In Progress[/blue]"
        elif self.status == "completed":
            status_str = "[green]Completed[/green]"
        elif self.status == "failed":
            status_str = "[red]Failed[/red]"
        elif self.status == "canceled":
            status_str = "[grey]Canceled[/grey]"
        else:
            status_str = self.status
            
        # Calculate percentage
        percentage = int((self.progress_value / self.progress_total) * 100) if self.progress_total else 0
        
        # Create a simple text representation
        message = self.message or "Processing..."
        return f"{task_type_display}: {status_str} - {percentage}% - {message}"


class TaskTrayToggle(Button):
    """Button to toggle the visibility of the task tray."""
    
    def __init__(self, 
                 pending: int = 0, 
                 in_progress: int = 0, 
                 completed: int = 0, 
                 error: int = 0,
                 **kwargs: Any) -> None:  # Add **kwargs to accept additional parameters
        """Initialize with task counts."""
        super().__init__("Tasks", **kwargs)  # Pass **kwargs to parent class
        self.pending = pending
        self.in_progress = in_progress
        self.completed = completed
        self.error = error
        self.update_label()
    
    def update_counts(self, 
                     pending: int = 0, 
                     in_progress: int = 0, 
                     completed: int = 0, 
                     error: int = 0) -> None:
        """Update the task counts and refresh the button."""
        self.pending = pending
        self.in_progress = in_progress
        self.completed = completed
        self.error = error
        self.update_label()
    
    def update_label(self) -> None:
        """Update the button label based on task counts."""
        total = self.pending + self.in_progress + self.completed + self.error
        
        if total == 0:
            self.label = "Tasks"
            return
        
        if self.error > 0:
            status_indicator = "[red]![/red]"
        elif self.in_progress > 0:
            status_indicator = "[blue]⟳[/blue]"
        elif self.pending > 0:
            status_indicator = "[yellow]⏳[/yellow]"
        elif self.completed > 0:
            status_indicator = "[green]✓[/green]"
        else:
            status_indicator = ""
        
        self.label = f"Tasks ({total}) {status_indicator}"


class TaskTray(Widget):
    """A collapsible tray for displaying and managing background tasks."""
    
    is_expanded = reactive(True)  # Changed to True for debugging
    
    def __init__(self) -> None:
        """Initialize the task tray."""
        super().__init__()
        self.tasks: Dict[str, Dict[str, Any]] = {}  # Store task data
    
    def compose(self) -> ComposeResult:
        """Compose the task tray widget."""
        # Toggle button to expand/collapse
        yield TaskTrayToggle(id="task-tray-toggle")
        
        # Container for tasks (always visible for debugging)
        with Container(id="task-tray-container"):
            # yield Label("Background Tasks (DEBUGGING)", id="task-tray-header")
            
            # Container for task items
            with Vertical(id="task-items-container"):
                # Task items will be added dynamically
                pass
            
            # Control buttons
            with Container(id="task-tray-controls"):
                yield Button("Clear Completed", id="clear-completed-btn", variant="primary")
                yield Button("Cancel All", id="cancel-all-btn", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "task-tray-toggle":
            self.is_expanded = not self.is_expanded
            self.refresh_container_visibility()
        elif event.button.id == "clear-completed-btn":
            self.clear_completed_tasks()
        elif event.button.id == "cancel-all-btn":
            self.cancel_all_tasks()
    
    def on_mount(self) -> None:
        """Add a debug task when the widget is mounted."""
        # Add a debug task to make it visible
        self.update_task(
            task_id="debug_task",  # Changed dash to underscore
            task_type="job_fetch",
            status="in_progress",
            progress_value=50,
            progress_total=100,
            message="Debug task for visibility testing"
        )
    
    def watch_is_expanded(self, is_expanded: bool) -> None:
        """React to changes in the expanded state."""
        self.refresh_container_visibility()
    
    def refresh_container_visibility(self) -> None:
        """Update the visibility of the task container based on expanded state."""
        if self.is_mounted:
            try:
                container = self.query_one("#task-tray-container", Container)
                if self.is_expanded:
                    container.remove_class("hidden")
                else:
                    container.add_class("hidden")
            except Exception:
                # Handle case where container might not exist yet
                pass
    
    def update_task(self, 
                   task_id: str, 
                   task_type: str, 
                   status: str, 
                   progress_value: int = 0, 
                   progress_total: int = 100, 
                   message: str = "") -> None:
        """Update or add a task to the tray."""
        # Check if the task already exists
        if task_id in self.tasks:
            # Update existing task
            task_item = self.query_one(f"#{task_id}", TaskItem)
            task_item.status = status
            task_item.progress_value = progress_value
            task_item.progress_total = progress_total
            task_item.message = message
        else:
            # Add new task
            task_data = {
                "task_id": task_id,
                "task_type": task_type,
                "status": status,
                "progress_value": progress_value,
                "progress_total": progress_total,
                "message": message,
                "created_time": datetime.now()
            }
            self.tasks[task_id] = task_data
            
            # Create and add the task item widget
            task_item = TaskItem(
                task_id=task_id,
                task_type=task_type,
                status=status,
                progress_value=progress_value,
                progress_total=progress_total,
                message=message,
                id=task_id
            )
            
            # Add to the container
            task_container = self.query_one("#task-items-container", Vertical)
            task_container.mount(task_item)
        
        # Update the toggle button counts
        self.update_toggle_counts()
    
    def remove_task(self, task_id: str) -> None:
        """Remove a task from the tray."""
        if task_id in self.tasks:
            # Remove from tasks dict
            del self.tasks[task_id]
            
            # Remove the widget
            try:
                task_item = self.query_one(f"#{task_id}", TaskItem)
                task_item.remove()
            except Exception:
                pass
            
            # Update counts
            self.update_toggle_counts()
    
    def clear_completed_tasks(self) -> None:
        """Remove all completed tasks."""
        completed_ids = [
            task_id for task_id, task_data in self.tasks.items()
            if task_data["status"] in ["completed", "failed", "canceled"]
        ]
        
        for task_id in completed_ids:
            self.remove_task(task_id)
    
    def cancel_all_tasks(self) -> None:
        """Request cancellation for all pending and in-progress tasks."""
        # In a real implementation, this would signal the background service
        # For now, just mark tasks as canceled
        active_tasks = [
            task_id for task_id, task_data in self.tasks.items()
            if task_data["status"] in ["pending", "in_progress"]
        ]
        
        for task_id in active_tasks:
            self.update_task(
                task_id=task_id,
                task_type=self.tasks[task_id]["task_type"],
                status="canceled",
                progress_value=self.tasks[task_id]["progress_value"],
                progress_total=self.tasks[task_id]["progress_total"],
                message="Canceled by user"
            )
    
    def update_toggle_counts(self) -> None:
        """Update the toggle button with current task counts."""
        # Count tasks by status
        pending = sum(1 for task in self.tasks.values() if task["status"] == "pending")
        in_progress = sum(1 for task in self.tasks.values() if task["status"] == "in_progress")
        completed = sum(1 for task in self.tasks.values() if task["status"] == "completed")
        error = sum(1 for task in self.tasks.values() if task["status"] in ["failed", "canceled"])
        
        # Update the toggle button
        toggle = self.query_one("#task-tray-toggle", TaskTrayToggle)
        toggle.update_counts(pending, in_progress, completed, error)