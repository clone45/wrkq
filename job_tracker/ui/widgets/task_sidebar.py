"""Sidebar panel for displaying tasks."""

from __future__ import annotations

from typing import Any, List, Dict, Optional
from datetime import datetime

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Static, Label
from textual.widget import Widget


class TaskItem(Static):
    """Represents a single task in the sidebar."""
    
    task_id = reactive("task_id")
    title = reactive("Task")
    status = reactive("pending")
    priority = reactive("medium")
    created_time = reactive(datetime.now())
    
    def __init__(
        self,
        task_id: str,
        title: str,
        status: str,
        priority: str = "medium",
        created_time: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a task item."""
        super().__init__("", **kwargs)
        self.task_id = task_id
        self.title = title
        self.status = status
        self.priority = priority
        self.created_time = created_time or datetime.now()
    
    def watch_status(self, status: str) -> None:
        """Watch for status changes and update the display."""
        self.refresh()
    
    def watch_title(self, title: str) -> None:
        """Watch for title changes and update the display."""
        self.refresh()
    
    def render(self) -> RenderableType:
        """Render the task item."""
        # Format the status display
        if self.status == "pending":
            status_str = "[yellow]Pending[/yellow]"
        elif self.status == "in_progress":
            status_str = "[blue]In Progress[/blue]"
        elif self.status == "completed":
            status_str = "[green]Completed[/green]"
        else:
            status_str = self.status
            
        # Format the priority
        if self.priority == "high":
            priority_str = "[red]High[/red]"
        elif self.priority == "medium":
            priority_str = "[yellow]Medium[/yellow]"
        elif self.priority == "low":
            priority_str = "[green]Low[/green]"
        else:
            priority_str = self.priority
        
        # Create the title with strikethrough for completed tasks
        title_text = self.title
        if self.status == "completed":
            # Apply strikethrough for completed tasks
            title_text = f"[strike]{self.title}[/strike]"
        
        # Display the task with status and priority
        return f"{title_text}\n{status_str} - Priority: {priority_str}"


class TaskSidebar(Widget):
    """A sidebar for displaying and managing tasks."""
    
    is_expanded = reactive(True)  # Start expanded
    
    # We're using an external CSS file instead of DEFAULT_CSS
    
    def __init__(self) -> None:
        """Initialize the task sidebar."""
        super().__init__()
        self.tasks: Dict[str, Dict[str, Any]] = {}  # Store task data
    
    def compose(self) -> ComposeResult:
        """Compose the task sidebar widget."""
        # Header
        yield Label("Tasks", id="sidebar-header")
        
        # Container for task items
        with Vertical(id="task-list"):
            # Task items will be added dynamically
            pass
        
        # Control buttons
        with Container(id="sidebar-controls"):
            yield Button("Add Task", id="add-task-btn", variant="primary")
            yield Button("Clear Completed", id="clear-completed-btn", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "add-task-btn":
            self.add_dummy_task()
        elif event.button.id == "clear-completed-btn":
            self.clear_completed_tasks()
    
    def on_mount(self) -> None:
        """Add dummy tasks when the widget is mounted."""
        # Start with the sidebar hidden (off-screen to the left)
        # Get the width and set initial offset to be off-screen
        width = self.size.width or 30  # Default to 30 if size not available yet
        self.styles.offset = (-width, 0)
        
        # Add dummy tasks for demonstration
        self.add_task(
            task_id="task_1",
            title="Review job application",
            status="completed",
            priority="high"
        )
        
        self.add_task(
            task_id="task_2",
            title="Update resume",
            status="in_progress",
            priority="medium"
        )
        
        self.add_task(
            task_id="task_3",
            title="Research company",
            status="pending",
            priority="low"
        )
    
    def add_dummy_task(self) -> None:
        """Add a dummy task for testing."""
        import uuid
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.add_task(
            task_id=task_id,
            title=f"New task {len(self.tasks) + 1}",
            status="pending",
            priority="medium"
        )
    
    def add_task(self, 
                task_id: str, 
                title: str, 
                status: str = "pending", 
                priority: str = "medium") -> None:
        """Add a new task to the sidebar."""
        # Store the task data
        task_data = {
            "task_id": task_id,
            "title": title,
            "status": status,
            "priority": priority,
            "created_time": datetime.now()
        }
        self.tasks[task_id] = task_data
        
        # Create and add the task item widget
        task_item = TaskItem(
            task_id=task_id,
            title=title,
            status=status,
            priority=priority,
            id=task_id,
            classes=f"task-item priority-{priority} status-{status}"
        )
        
        # Add to the container
        task_list = self.query_one("#task-list", Vertical)
        task_list.mount(task_item)
    
    def update_task(self, task_id: str, **updates: Any) -> None:
        """Update an existing task."""
        if task_id not in self.tasks:
            return
            
        # Update stored data
        for key, value in updates.items():
            if key in self.tasks[task_id]:
                self.tasks[task_id][key] = value
        
        # Update widget
        try:
            task_item = self.query_one(f"#{task_id}", TaskItem)
            
            # Update reactive attributes
            if "title" in updates:
                task_item.title = updates["title"]
            if "status" in updates:
                task_item.status = updates["status"]
                task_item.remove_class(f"status-{task_item.status}")
                task_item.add_class(f"status-{updates['status']}")
            if "priority" in updates:
                task_item.priority = updates["priority"]
                task_item.remove_class(f"priority-{task_item.priority}")
                task_item.add_class(f"priority-{updates['priority']}")
        except Exception:
            pass
    
    def remove_task(self, task_id: str) -> None:
        """Remove a task from the sidebar."""
        if task_id in self.tasks:
            # Remove from tasks dict
            del self.tasks[task_id]
            
            # Remove the widget
            try:
                task_item = self.query_one(f"#{task_id}", TaskItem)
                task_item.remove()
            except Exception:
                pass
    
    def clear_completed_tasks(self) -> None:
        """Remove all completed tasks."""
        completed_ids = [
            task_id for task_id, task_data in self.tasks.items()
            if task_data["status"] == "completed"
        ]
        
        for task_id in completed_ids:
            self.remove_task(task_id)
            
    def show(self) -> None:
        """Show the sidebar by animating it into view."""
        self.styles.animate("offset", (0, 0), duration=0.3, easing="in_out_cubic")
        
    def hide(self) -> None:
        """Hide the sidebar by animating it out of view."""
        width = self.size.width
        self.styles.animate("offset", (-width, 0), duration=0.3, easing="in_out_cubic")
        
    def toggle(self) -> None:
        """Toggle the sidebar visibility."""
        current_offset = self.styles.offset or (0, 0)
        if current_offset[0] < 0:
            self.show()
        else:
            self.hide()