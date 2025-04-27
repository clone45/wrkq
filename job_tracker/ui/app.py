"""
Main Textual application class for the Job Tracker
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from simple_logger import Slogger

from bson import ObjectId
from textual import log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from job_tracker.di import build_container, Container
from job_tracker.ui.screens.jobs_screen import JobsScreen
from job_tracker.ui.screens.add_job_screen import AddJobScreen

# hard-coded user until AuthService arrives
HARDCODED_USER_EMAIL = "clone45@gmail.com"


class JobTrackerApp(App):
    """A retro terminal application for managing job applications."""


    CSS_PATH = [
        "css/main.tcss",
        "css/detail_chat.tcss",
        "css/add_job_screen.tcss"
    ]

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_job", "Add Job", show=True),
        Binding("n", "next_page", "Next Page", show=True),
        Binding("p", "prev_page", "Previous Page", show=True),
        Binding("h", "toggle_hidden", "Toggle Hidden Jobs", show=True),
        Binding("f", "focus_search", "Search", show=True),
        Binding("d", "toggle_detail", "Toggle Details", show=True),
    ]

    # ------------------------------------------------------------------ #
    # init / mount
    # ------------------------------------------------------------------ #

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self.container: Container = build_container(config)

        # user state
        self.current_user_id: Optional[ObjectId] = None
        self.current_user_data: Optional[Dict[str, Any]] = None

    # Textual life-cycle ------------------------------------------------- #

    def on_mount(self) -> None:
        self.fetch_current_user()

        if not self.current_user_id:
            log.critical(f"User {HARDCODED_USER_EMAIL} not found. Exiting.")
            self.exit(message="Error: user not found in MongoDB.")
            return

        # push main Jobs screen
        self.push_screen(
            JobsScreen(
                job_repo=self.container.job_repo,
                company_repo=self.container.company_repo,
                config=self.config,
                id="jobs_screen",
            )
        )

    # ------------------------------------------------------------------ #
    # key-binding actions
    # ------------------------------------------------------------------ #

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

    # Add-job flow ------------------------------------------------------- #

    def action_add_job(self) -> None:
        if not self.current_user_id:
            self.notify("Cannot add job: user not loaded.", severity="error", timeout=4)
            return

        Slogger.log("Opening AddJobScreen")

        def on_job_added(added_job):
            if added_job:
                self.refresh_jobs_list()

        self.push_screen(
            AddJobScreen(
                job_repo=self.container.job_repo,
                company_repo=self.container.company_repo,
                user_id=str(self.current_user_id)
            )
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def fetch_current_user(self) -> None:
        """Look up the hard-coded user via UserRepo."""
        log(f"Fetching user for {HARDCODED_USER_EMAIL}")
        user_repo = self.container.user_repo
        user_doc = user_repo.by_email(HARDCODED_USER_EMAIL)
        if user_doc and isinstance(user_doc.id, str):
            self.current_user_id = ObjectId(user_doc.id)
            self.current_user_data = user_doc
            log(f"Authenticated as {user_doc.email}")
        else:
            log.error("User not found or _id invalid")

    def refresh_jobs_list(self) -> None:
        """Refresh the jobs list in the main screen."""
        jobs_screen = self.query_one("#jobs_screen", JobsScreen)
        jobs_screen.load_jobs()
        pass
