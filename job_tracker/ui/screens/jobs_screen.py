# job_tracker/ui/screens/jobs_screen.py with simplified details logic
"""
Main Jobs screen – updated with integrated chat and details view
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Grid
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

# Data access
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.company_repo import CompanyRepo

# Business layer
from job_tracker.services.job_service import JobService

# Domain models
from job_tracker.models.pagination import Page
from job_tracker.models.job import Job

# UI helpers
from job_tracker.ui.controllers.status_bar import StatusBarController
from job_tracker.utils.formatters import format_date

# Widgets
from job_tracker.ui.widgets.job_table import JobTable
from job_tracker.ui.widgets.pagination import Pagination
from job_tracker.ui.widgets.search_bar import SearchBar
from job_tracker.ui.widgets.job_details import JobDetail
from job_tracker.ui.widgets.chat_panel import ChatPanel


class JobsScreen(Screen):
    """Main screen for job listings with integrated chat panel."""

    # reactive state
    current_page: int = reactive(1)
    per_page: int = reactive(15)
    show_hidden: bool = reactive(False)
    selected_job_id: Optional[str] = reactive(None, layout=True)

    search_query: str = reactive("")
    total_jobs: int = reactive(0)
    total_pages: int = reactive(1)

    # ------------------------------------------------------------------ #

    def __init__(
        self,
        job_repo: JobRepo,
        company_repo: CompanyRepo,
        config: Dict[str, Any],
        *,
        id: str = "jobs_screen",
    ) -> None:
        super().__init__(id=id)

        self.config = config
        self.per_page = config.get("ui", {}).get("per_page", 15)

        # business service
        self.job_service = JobService(
            job_repo,
            company_repo,
            default_page_size=self.per_page,
        )

        # in-memory cache of current table rows
        self.jobs_data: List[Job] = []

    # ------------------------------------------------------------------ #
    # Compose & mount
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            with Vertical(id="content-area"):
                yield SearchBar(id="search-bar")
                yield JobTable(id="jobs-table")
                yield Pagination(id="pagination")
                
                # Always visible detail and chat section
                with Grid(id="detail-chat-grid"):
                    yield JobDetail(id="job-detail")
                    yield ChatPanel(id="chat-panel")

        yield Static(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        # table setup
        table = self.query_one(JobTable)
        table.add_columns(
            "ID",
            "Company",
            "Title",
            "Location",
            "Date Posted",
            "Salary",
            "Hidden",
        )
        table.styles.height = "1fr"

        # Initialize the job detail with null (shows "No Job Selected")
        detail_widget = self.query_one(JobDetail)
        detail_widget.update_job(None)

        # Initialize the chat panel
        chat_panel = self.query_one(ChatPanel)
        chat_panel.add_assistant_message("Welcome to Job Tracker! Select a job to view details.")

        # status-bar controller
        self.status_controller = StatusBarController(self.query_one("#status-bar"))

        self.load_jobs()

    # ------------------------------------------------------------------ #
    # Reactive watchers
    # ------------------------------------------------------------------ #

    def watch_selected_job_id(self, job_id: Optional[str]) -> None:
        detail_widget = self.query_one(JobDetail)

        if job_id:
            # Automatically update job details when a job is selected
            job = self._get_job_data(job_id)

            detail_widget.update_job(job)
            
            # Inform the chat panel about the selected job
            chat_panel = self.query_one(ChatPanel)
            if job:
                chat_panel.add_assistant_message(f"Now viewing: {job.company} - {job.title}")
        else:
            # Clear details if no job is selected
            detail_widget.update_job(None)

        # update status-bar selection text
        current = str(self.query_one("#status-bar").renderable)
        base = current.split(" | Selected:")[0]
        self.status_controller.update_with_selection(
            base, self._get_job_data(job_id) if job_id else None
        )

    # ------------------------------------------------------------------ #
    # Action handlers
    # ------------------------------------------------------------------ #


    def action_focus_search(self) -> None:
        self.query_one(SearchBar).focus_input()

    def action_next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_jobs()

    def action_prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.load_jobs()

    def action_toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        self.current_page = 1
        self.load_jobs()
        status = "showing" if self.show_hidden else "hiding"
        self.notify(f"Now {status} hidden jobs", title="Filter Changed")

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    def on_screen_resume(self, event) -> None:
        self.load_jobs()


    def on_job_table_row_selected(self, event: JobTable.RowSelected) -> None:
        row_index = event.row_key.value
        if row_index is not None and 0 <= row_index < len(self.jobs_data):
            job = self.jobs_data[row_index]
            self.selected_job_id = job.id

    def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
        self.search_query = event.query
        self.current_page = 1
        self.load_jobs()

    def on_pagination_page_changed(self, event: Pagination.PageChanged) -> None:
        if self.current_page != event.page:
            self.current_page = event.page
            self.load_jobs()



    # ------------------------------------------------------------------ #
    # Data helpers
    # ------------------------------------------------------------------ #

    def _get_job_data(self, job_id: str) -> Optional[Job]:
        return next((j for j in self.jobs_data if j.id == job_id), None) \
            or self.job_service.by_id(job_id)

    def load_jobs(self) -> None:

        """Fetch jobs from service and refresh UI widgets."""
        page_obj: Page[Job] = self.job_service.page(
            page=self.current_page,
            per_page=self.per_page,
            search=self.search_query,
            show_hidden=self.show_hidden,
        )

        self.jobs_data = list(page_obj.items)
        self.total_jobs = page_obj.total
        self.total_pages = page_obj.pages

        # -------- Table ----------
        table = self.query_one(JobTable)
        table.clear()

        current_selection_key: Optional[int] = None
        for idx, job in enumerate(self.jobs_data):
            job_id = job.id
            fmt = self.config.get("ui", {}).get("date_format", "%Y-%m-%d")
            table.add_row(
                job_id,
                job.company,
                job.title,
                job.location,
                format_date(job.posting_date, fmt),
                job.salary or "N/A",
                "Yes" if job.hidden else "No",
                key=idx,
            )
            if job_id == self.selected_job_id:
                current_selection_key = idx

        # scroll to selection
        if current_selection_key is not None:
            self.set_timer(
                0.05,
                lambda row=current_selection_key: table.move_cursor(
                    row=row, animate=False
                ),
            )

        # -------- Pagination -------
        self.query_one(Pagination).update_pages(
            self.current_page, self.total_pages
        )

        # -------- Status bar -------
        meta = {
            "total": self.total_jobs,
            "pages": self.total_pages,
            "current_page": self.current_page,
            "search_query": self.search_query,
            "show_hidden": self.show_hidden,
        }
        selected = (
            self._get_job_data(self.selected_job_id)
            if self.selected_job_id
            else None
        )
        self.status_controller.update(meta, self.selected_job_id, selected)