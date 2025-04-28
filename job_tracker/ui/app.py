"""
Main Textual application class for the Job Tracker
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from simple_logger import Slogger

from textual import log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from job_tracker.di import build_container, Container
from job_tracker.ui.screens.jobs_screen import JobsScreen
from job_tracker.ui.screens.add_job_screen import AddJobScreen


class JobTrackerApp(App):
    """A retro terminal application for managing job applications."""


    CSS_PATH = [
        "css/main.tcss",
        "css/detail_chat.tcss",
        "css/add_job_screen.tcss",
        "css/job_actions.tcss",
        "css/confirmation_modal.tcss",
        "css/loading_indicator.tcss",
    ]

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_job", "Add Job", show=True),
        Binding("h", "toggle_hidden", "Toggle Hidden Jobs", show=True),
        Binding("f", "focus_search", "Search", show=True),
        Binding("delete", "hide_selected_job", "Hide Job", show=True),
        Binding("space", "show_job_actions", "Job Actions", show=True),
    ]

    # ------------------------------------------------------------------ #
    # init / mount
    # ------------------------------------------------------------------ #

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self.container: Container = build_container(config)

    # Textual life-cycle ------------------------------------------------- #

    def on_mount(self) -> None:
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

    def action_hide_selected_job(self) -> None:
        """Hide the selected job."""
        if hasattr(self.screen, "hide_selected_job"):
            self.screen.hide_selected_job()

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def refresh_jobs_list(self) -> None:
        """Refresh the jobs list in the main screen."""
        jobs_screen = self.query_one("#jobs_screen", JobsScreen)
        jobs_screen.load_jobs()
        pass