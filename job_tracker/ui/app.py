"""
Main Textual application class for the Job Tracker
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid
from simple_logger import Slogger

from textual import log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static
from textual.message import Message

from job_tracker.di import build_container, Container
from job_tracker.ui.screens.jobs_screen import JobsScreen
from job_tracker.ui.screens.add_job_screen import AddJobScreen
from job_tracker.ui.screens.import_jobs_screen import ImportJobsScreen
from job_tracker.ui.controllers.status_bar import StatusBarController
from job_tracker.ui.widgets.task_tray import TaskTray
from job_tracker.ui.widgets.notification import NotificationContainer
from job_tracker.ui.widgets.debug_widget import DebugWidget
from job_tracker.ui.widgets.task_sidebar import TaskSidebar
from job_tracker.ui.messages import TaskStatusUpdate


class JobTrackerApp(App):
    """A retro terminal application for managing job applications."""

    CSS_PATH = [
        # Main CSS should be first as it sets global styles
        "css/main.tcss",
        # Widget-specific CSS files
        "css/task_tray.tcss",
        "css/task_sidebar.tcss",
        "css/notification.tcss",
        "css/debug_widget.tcss",
        "css/loading_indicator.tcss",
        # Screen-specific CSS files
        "css/detail_chat.tcss",
        "css/add_job_screen.tcss",
        "css/import_jobs_screen.tcss",
        "css/job_actions.tcss", 
        "css/confirmation_modal.tcss",
    ]

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_job", "Add Job", show=True),
        Binding("i", "import_jobs", "Import Jobs", show=True),
        Binding("h", "toggle_hidden", "Toggle Hidden Jobs", show=True),
        Binding("f", "focus_search", "Search", show=True),
        Binding("delete", "hide_selected_job", "Hide Job", show=True),
        Binding("space", "show_job_actions", "Job Actions", show=True),
        Binding("t", "toggle_task_tray", "Task Tray", show=True),
        Binding("s", "toggle_sidebar", "Task Sidebar", show=True),
    ]

    # ------------------------------------------------------------------ #
    # init / mount
    # ------------------------------------------------------------------ #

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self.container: Container = build_container(config)
        
        # Background task management (simulated for now)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_counts = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "error": 0
        }
        
        # For polling background tasks
        self.task_polling_timer_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the app with global UI elements."""
        # An ultra-simple debug widget that should be visible
        yield DebugWidget()
        
        # Try the TaskTray after the debug widget
        yield TaskTray()
        
        # Task sidebar (side panel with tasks)
        yield TaskSidebar()
        
        # Status bar for application-wide status (with markup disabled)
        yield Static(id="status-bar", markup=False)
        
        # Notification container for toast messages
        yield NotificationContainer()
        
        # The default widgets will be yielded by App
        yield Header()
        yield Footer()

    # Textual life-cycle ------------------------------------------------- #

    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        # Initialize the status bar controller
        self.status_bar = self.query_one("#status-bar", Static)
        self.status_controller = StatusBarController(self.status_bar)
        
        # Start the background task polling timer
        self.task_polling_timer_id = self.set_interval(0.5, self.check_background_tasks)
        
        # Initialize the notification container
        self.notification_container = self.query_one(NotificationContainer)
        
        # Create some demo tasks for debugging
        self.start_demo_task("job_fetch", "Debug task for visibility testing")
        self.start_demo_task("job_search", "Another debug task")
        
        # Show a notification to confirm functionality
        self.notification_container.add_notification(
            message="Debug mode: Task tray should be visible at the top",
            level="warning",
            timeout=10.0
        )
        
        # push main Jobs screen
        self.push_screen(
            JobsScreen(
                job_repo=self.container.job_repo,
                company_repo=self.container.company_repo,
                config=self.config,
                application_service=self.container.application_service,
                id="jobs_screen",
            )
        )

    # ------------------------------------------------------------------ #
    # key-binding actions
    # ------------------------------------------------------------------ #

    def action_show_job_actions(self) -> None:
        """Show job actions modal for the selected job."""
        if hasattr(self.screen, "show_job_actions"):
            self.screen.show_job_actions()

    def action_focus_search(self) -> None:
        if hasattr(self.screen, "focus_search"):
            self.screen.focus_search()

    def action_next_page(self) -> None:
        if hasattr(self.screen, "next_page"):
            self.screen.next_page()

    def action_prev_page(self) -> None:
        if hasattr(self.screen, "prev_page"):
            self.screen.prev_page()

    def action_toggle_hidden(self) -> None:
        if hasattr(self.screen, "toggle_hidden"):
            self.screen.toggle_hidden()

    def action_toggle_detail(self) -> None:
        if hasattr(self.screen, "toggle_detail"):
            self.screen.toggle_detail()
    
    def action_toggle_task_tray(self) -> None:
        """Toggle the task tray visibility."""
        task_tray = self.query_one(TaskTray)
        # Toggle the is_expanded property using styles or attributes depending on implementation
        if hasattr(task_tray, 'is_expanded'):
            task_tray.is_expanded = not task_tray.is_expanded
        else:
            # Fallback to class-based toggle
            if task_tray.has_class("expanded"):
                task_tray.remove_class("expanded")
            else:
                task_tray.add_class("expanded")
        
    def action_toggle_sidebar(self) -> None:
        """Toggle the task sidebar visibility."""
        sidebar = self.query_one(TaskSidebar)
        sidebar.toggle()

    # Add-job flow ------------------------------------------------------- #

    def action_add_job(self) -> None:
        Slogger.log("Opening AddJobScreen")

        self.push_screen(
            AddJobScreen(
                job_repo=self.container.job_repo,
                company_repo=self.container.company_repo,
                job_extractor_service=self.container.job_extractor_service,
                openai_service=self.container.openai_service  # Keep for backward compatibility
            )
        )
        
    def action_import_jobs(self) -> None:
        """Open the import jobs screen."""
        Slogger.log("Opening ImportJobsScreen")
        
        self.push_screen(
            ImportJobsScreen()
        )

    def action_hide_selected_job(self) -> None:
        """Hide the selected job."""
        if hasattr(self.screen, "hide_selected_job"):
            self.screen.hide_selected_job()

    # ------------------------------------------------------------------ #
    # background task management
    # ------------------------------------------------------------------ #
    
    def check_background_tasks(self) -> None:
        """Periodic check for updates to background tasks."""
        # In a real implementation, this would poll a background worker service
        # For demonstration, we'll simulate task updates
        
        # Update the task counts in the status bar
        self.status_controller.update_task_status(
            pending=self.task_counts["pending"],
            in_progress=self.task_counts["in_progress"],
            completed=self.task_counts["completed"],
            error=self.task_counts["error"]
        )
    
    def create_task(self, task_type: str, params: Dict[str, Any], message: str = "") -> str:
        """Create a new background task and return its ID."""
        # Generate a UUID and remove dashes to make it a valid Textual ID
        raw_uuid = str(uuid.uuid4())
        task_id = f"task_{raw_uuid.replace('-', '_')}"
        
        # Create the task data structure
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "pending",
            "params": params,
            "progress": {
                "current": 0,
                "total": 100,
                "message": message or "Waiting to start..."
            },
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Store the task
        self.tasks[task_id] = task
        
        # Update counts
        self.task_counts["pending"] += 1
        
        # Update the task tray UI
        task_tray = self.query_one(TaskTray)
        task_tray.update_task(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            progress_value=0,
            progress_total=100,
            message=message or "Waiting to start..."
        )
        
        # Show a notification
        self.notification_container.add_notification(
            message=f"Task queued: {message or task_type}",
            level="info"
        )
        
        # Post a message for screens to react to
        self.post_message(TaskStatusUpdate(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            message=message
        ))
        
        return task_id
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress_value: Optional[int] = None,
        progress_total: Optional[int] = None,
        message: Optional[str] = None,
        result: Any = None,
        error: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the status of a background task."""
        if task_id not in self.tasks:
            return
            
        task = self.tasks[task_id]
        old_status = task["status"]
        
        # Update the task status
        task["status"] = status
        
        # Update progress if provided
        if progress_value is not None:
            task["progress"]["current"] = progress_value
        if progress_total is not None:
            task["progress"]["total"] = progress_total
        if message is not None:
            task["progress"]["message"] = message
            
        # Update timestamps based on status changes
        if old_status != status:
            if status == "in_progress" and task["started_at"] is None:
                task["started_at"] = datetime.now()
            elif status in ["completed", "failed", "canceled"] and task["completed_at"] is None:
                task["completed_at"] = datetime.now()
                
        # Update result or error if provided
        if result is not None:
            task["result"] = result
        if error is not None:
            task["error"] = error
            
        # Update task counts
        if old_status != status:
            if old_status in self.task_counts:
                self.task_counts[old_status] -= 1
            
            # Map status to count category
            count_category = status
            if status in ["failed", "canceled"]:
                count_category = "error"
                
            if count_category in self.task_counts:
                self.task_counts[count_category] += 1
                
        # Update the task tray UI
        task_tray = self.query_one(TaskTray)
        task_tray.update_task(
            task_id=task_id,
            task_type=task["task_type"],
            status=status,
            progress_value=task["progress"]["current"],
            progress_total=task["progress"]["total"],
            message=task["progress"]["message"]
        )
        
        # Show notifications for significant status changes
        if old_status != status:
            if status == "completed":
                self.notification_container.add_notification(
                    message=f"Task completed: {task['progress']['message'] or task['task_type']}",
                    level="success"
                )
            elif status == "failed":
                error_msg = error.get("message", "Unknown error") if error else "Unknown error"
                self.notification_container.add_notification(
                    message=f"Task failed: {error_msg}",
                    level="error",
                    timeout=10.0  # Show errors longer
                )
            elif status == "canceled":
                self.notification_container.add_notification(
                    message=f"Task canceled: {task['progress']['message'] or task['task_type']}",
                    level="warning"
                )
                
        # Post a message for screens to react to
        self.post_message(TaskStatusUpdate(
            task_id=task_id,
            task_type=task["task_type"],
            status=status,
            progress_value=task["progress"]["current"],
            progress_total=task["progress"]["total"],
            message=task["progress"]["message"]
        ))
    
    def start_demo_task(self, task_type: str, message: str = "") -> str:
        """Start a demonstration task that shows progress over time."""
        # Create the task
        task_id = self.create_task(task_type, {}, message)
        
        # Start a timer to simulate progress
        def update_progress() -> None:
            task = self.tasks.get(task_id)
            if not task:
                return
                
            # Get current progress
            current = task["progress"]["current"]
            
            # Simulate progress
            if current < 100:
                if task["status"] == "pending":
                    # Start the task
                    self.update_task_status(
                        task_id=task_id,
                        status="in_progress",
                        message=f"Processing {task_type}..."
                    )
                    
                # Increment progress
                new_progress = min(100, current + 10)
                self.update_task_status(
                    task_id=task_id,
                    status="in_progress",
                    progress_value=new_progress,
                    message=f"Processing {task_type} ({new_progress}%)..."
                )
                
                # Schedule the next update
                self.set_timer(1.0, update_progress)
            else:
                # Complete the task
                self.update_task_status(
                    task_id=task_id,
                    status="completed",
                    message=f"Completed {task_type}"
                )
        
        # Start the progress updates
        self.set_timer(1.0, update_progress)
        
        return task_id

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def refresh_jobs_list(self) -> None:
        """Refresh the jobs list in the main screen."""
        jobs_screen = self.query_one("#jobs_screen", JobsScreen)
        jobs_screen.load_jobs()
        pass