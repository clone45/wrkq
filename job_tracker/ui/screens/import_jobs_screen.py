"""
Screen for importing jobs into the system.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Label, Button, Input, TabPane, TabbedContent, ProgressBar
from textual.reactive import reactive
from simple_logger import Slogger

from job_tracker.ui.messages import TaskStatusUpdate


class ImportJobsScreen(Screen):
    """Full-screen interface for importing jobs."""

    BINDINGS = [
        ("escape", "go_back", "Back to Jobs"),
    ]

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        """
        Initialize the ImportJobsScreen.
        """
        super().__init__(name=name, id=id, classes=classes)
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.active_task_ids: List[str] = []
        self.completed_tasks: List[str] = []

    def compose(self) -> ComposeResult:
        """Compose the screen widgets."""
        # Header with title
        yield Header(show_clock=True)
        
        # Main content container
        with Container(id="import-jobs-container"):
            yield Label("Import Jobs", id="page-title", classes="heading")
            
            # Tabbed content for different import modes
            with TabbedContent(id="import-tabs"):
                # URL Import Tab
                with TabPane("URL Import", id="url-import-tab"):
                    yield Label("Import a job from a LinkedIn URL", classes="tab-description")
                    
                    with Container(classes="form-container"):
                        yield Label("LinkedIn Job URL:")
                        with Horizontal(classes="input-with-button"):
                            yield Input(
                                placeholder="https://www.linkedin.com/jobs/view/...",
                                id="linkedin-url-input"
                            )
                            yield Button("Import", id="import-url-btn", variant="primary")
                    
                    # Status and progress section
                    with Container(id="url-import-status", classes="status-container"):
                        yield Label("Ready to import", id="url-status-text")
                    
                # Search Import Tab
                with TabPane("Search Import", id="search-import-tab"):
                    yield Label("Search and import multiple jobs from LinkedIn", classes="tab-description")
                    
                    with Container(classes="form-container"):
                        yield Label("Keywords:")
                        yield Input(
                            placeholder="Software Engineer, Python, etc.",
                            id="keywords-input"
                        )
                        
                        yield Label("Location:")
                        yield Input(
                            placeholder="San Francisco, Remote, etc.",
                            id="location-input"
                        )
                        
                        with Horizontal(classes="buttons-row"):
                            yield Button("Search", id="search-jobs-btn", variant="primary")
                            yield Button("Clear", id="clear-search-btn")
                    
                    # Status and progress section
                    with Container(id="search-import-status", classes="status-container"):
                        yield Label("Ready to search", id="search-status-text")
            
            # Demonstration controls
            with Container(id="demo-controls", classes="demo-controls"):
                yield Label("Demonstration Controls", classes="section-title")
                with Horizontal(classes="buttons-row"):
                    yield Button("Demo URL Import", id="demo-url-import-btn", variant="success")
                    yield Button("Demo Batch Search", id="demo-search-btn", variant="success")
                    yield Button("Demo Failed Task", id="demo-fail-btn", variant="error")
        
        # Footer with key bindings
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        Slogger.log("Import Jobs Screen mounted")
    
    def action_go_back(self) -> None:
        """Return to the jobs screen."""
        Slogger.log("Closing Import Jobs Screen")
        self.app.pop_screen()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "import-url-btn":
            self.import_url()
        elif button_id == "search-jobs-btn":
            self.search_jobs()
        elif button_id == "clear-search-btn":
            self.clear_search_inputs()
        elif button_id == "demo-url-import-btn":
            self.start_demo_task("job_fetch", "Demo LinkedIn Job URL")
        elif button_id == "demo-search-btn":
            self.start_demo_task("job_search", "Demo LinkedIn Job Search")
        elif button_id == "demo-fail-btn":
            self.start_demo_fail_task()
    
    def import_url(self) -> None:
        """Import a job from the URL input."""
        url_input = self.query_one("#linkedin-url-input", Input)
        url = url_input.value.strip()
        
        if not url:
            self.update_status("url", "Please enter a LinkedIn job URL")
            return
        
        # Start a demo task
        task_message = f"Importing job from {url[:30]}..."
        self.start_demo_task("job_fetch", task_message)
        
        # Clear the input
        url_input.value = ""
    
    def search_jobs(self) -> None:
        """Search and import jobs based on criteria."""
        keywords_input = self.query_one("#keywords-input", Input)
        location_input = self.query_one("#location-input", Input)
        
        keywords = keywords_input.value.strip()
        location = location_input.value.strip()
        
        if not keywords and not location:
            self.update_status("search", "Please enter search criteria")
            return
        
        # Start a demo task
        task_message = f"Searching for jobs: {keywords} in {location}"
        self.start_demo_task("job_search", task_message)
    
    def clear_search_inputs(self) -> None:
        """Clear the search input fields."""
        self.query_one("#keywords-input", Input).value = ""
        self.query_one("#location-input", Input).value = ""
        self.update_status("search", "Ready to search")
    
    def update_status(self, mode: str, message: str) -> None:
        """Update the status text for a specific import mode."""
        if mode == "url":
            status_text = self.query_one("#url-status-text", Label)
        else:
            status_text = self.query_one("#search-status-text", Label)
        
        status_text.update(message)
    
    def start_demo_task(self, task_type: str, message: str) -> None:
        """Start a demonstration task through the app's background task system."""
        # Call the app's task creation method
        task_id = self.app.start_demo_task(task_type, message)
        
        # Track the task locally
        self.active_tasks[task_id] = {
            "type": task_type,
            "message": message
        }
        
        self.active_task_ids.append(task_id)
        
        # Update status
        if task_type == "job_fetch":
            self.update_status("url", f"Processing: {message}")
        else:
            self.update_status("search", f"Processing: {message}")
    
    def start_demo_fail_task(self) -> None:
        """Start a task that will fail for demonstration purposes."""
        # Create a task
        task_id = self.app.create_task("job_fetch", {}, "Demo Failing Task")
        
        # Track the task locally
        self.active_tasks[task_id] = {
            "type": "job_fetch",
            "message": "Demo Failing Task"
        }
        
        self.active_task_ids.append(task_id)
        
        # Set a timer to simulate the task starting and then failing
        def start_task():
            self.app.update_task_status(
                task_id=task_id,
                status="in_progress",
                progress_value=20,
                message="Processing task..."
            )
            
            # Set a timer for failure
            self.set_timer(2.0, fail_task)
        
        def fail_task():
            self.app.update_task_status(
                task_id=task_id,
                status="failed",
                error={"message": "Simulated error: Could not connect to LinkedIn"}
            )
        
        # Start the sequence
        self.set_timer(1.0, start_task)
    
    def on_task_status_update(self, message: TaskStatusUpdate) -> None:
        """Handle task status update messages."""
        task_id = message.task_id
        
        # If this is one of our tasks, update the status
        if task_id in self.active_tasks:
            task_type = message.task_type
            status = message.status
            
            if status == "completed":
                self.completed_tasks.append(task_id)
                if task_type == "job_fetch":
                    self.update_status("url", f"Successfully imported job")
                else:
                    self.update_status("search", f"Search completed")
            elif status == "failed":
                if task_type == "job_fetch":
                    self.update_status("url", f"Failed to import job: {message.message}")
                else:
                    self.update_status("search", f"Search failed: {message.message}")
            elif status == "in_progress":
                # Update progress display
                if task_type == "job_fetch":
                    self.update_status("url", f"Processing: {message.message}")
                else:
                    self.update_status("search", f"Processing: {message.message}")
            elif status == "canceled":
                if task_type == "job_fetch":
                    self.update_status("url", "Import canceled")
                else:
                    self.update_status("search", "Search canceled")