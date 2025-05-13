"""
Job detail widget showing comprehensive job information (model-aware).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import html2text

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll, Horizontal
from textual.widgets import Label, Markdown  # Using Markdown for rendered content
from textual.reactive import var

from job_tracker.models.job import Job


class JobDetail(Container):
    """Scrollable detail pane for a Job."""

    # reactives
    job_data: var[Optional[Job]] = var(None)          # current Job model
    current_job_id: var[Optional[str]] = var(None)    # convenience

    # ------------------------------------------------------------------ #
    # compose
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        # The VerticalScroll is the single direct child handling scroll
        with VerticalScroll(id="job-detail-scroll"):
            # Header Widgets (directly under scroll)
            yield Label("No Job Selected", id="detail-company-title", classes="detail-title")

            # Basic Info Widgets (directly under scroll)
            yield Label("Basic Information", id="basic-info-title", classes="section-title")
            yield Horizontal(Label("Location:", classes="detail-label"), Label("-", id="detail-location", classes="detail-value"), classes="detail-row")
            yield Horizontal(Label("Salary:", classes="detail-label"), Label("-", id="detail-salary", classes="detail-value"), classes="detail-row")
            yield Horizontal(Label("Posted:", classes="detail-label"), Label("-", id="detail-posted", classes="detail-value"), classes="detail-row")
            yield Horizontal(Label("Source:", classes="detail-label"), Label("-", id="detail-source", classes="detail-value"), classes="detail-row")
            yield Horizontal(Label("Status:", classes="detail-label"), Label("-", id="detail-status", classes="detail-value"), classes="detail-row")
            yield Horizontal(Label("Hidden:", classes="detail-label"), Label("-", id="detail-hidden", classes="detail-value"), classes="detail-row")
            yield Horizontal(Label("Link:", classes="detail-label"), Label("-", id="detail-link", classes="detail-value"), classes="detail-row")

            # Description Widgets (directly under scroll)
            # Use id instead of meta for section titles
            yield Label("Job Description", id="description-title", classes="section-title")
            yield Markdown("", id="job-description-content")  # Using Markdown widget

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _fmt_date(value: datetime | str | None, fmt: str = "%Y-%m-%d") -> str:
        if not value:
            return "N/A"
        if isinstance(value, datetime):
            return value.strftime(fmt)
        try:
            # Handle potential ISO format strings from DB
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime(fmt)
        except (ValueError, TypeError):
             # Fallback for non-datetime, non-ISO strings
            return str(value) if value else "N/A"

    @staticmethod
    def _fmt_money(value) -> str:
        if value is None:
            return "N/A"
        # Attempt to convert to float if it's a string representing a number
        if isinstance(value, str):
            try:
                value = float(value.replace('$', '').replace(',', '').strip())
            except ValueError:
                # If conversion fails, return the original string if non-empty
                return value.strip() or "N/A"
        # Format if it's a number
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        # Fallback for other types or empty strings after potential conversion attempt
        return str(value).strip() or "N/A"

    @staticmethod
    def _html_to_markdown(html_content: str) -> str:
        """Convert HTML content to Markdown format."""
        if not html_content or html_content == "N/A":
            return "N/A"
            
        # Configure html2text
        h = html2text.HTML2Text()
        h.ignore_links = False  # Keep links in the markdown
        h.body_width = 0  # Don't wrap text at a specific width
        h.unicode_snob = True  # Use Unicode instead of ASCII
        h.ignore_images = True  # Ignore images as they won't display in terminal
        
        # Convert to markdown
        markdown_content = h.handle(html_content)
        return markdown_content

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def update_job(self, job: Optional[Job]) -> None:
        """Populate widgets with model data (or clear if None)."""

        self.job_data = job
        self.current_job_id = job.id if job else None

        # Grab widgets once
        company_title = self.query_one("#detail-company-title", Label)
        loc_lbl       = self.query_one("#detail-location", Label)
        sal_lbl       = self.query_one("#detail-salary", Label)
        post_lbl      = self.query_one("#detail-posted", Label)
        src_lbl       = self.query_one("#detail-source", Label)
        status_lbl    = self.query_one("#detail-status", Label)
        hid_lbl       = self.query_one("#detail-hidden", Label)
        link_lbl      = self.query_one("#detail-link", Label)
        desc_md       = self.query_one("#job-description-content", Markdown)  # Using Markdown widget

        # Query the section title labels using their new IDs
        basic_info_title = self.query_one("#basic-info-title", Label)
        description_title = self.query_one("#description-title", Label)
        
        if job:
            company_title.update(f"{job.company} - {job.title}")

            loc_lbl.update(job.location or "N/A")
            sal_lbl.update(self._fmt_money(job.salary))
            post_lbl.update(self._fmt_date(job.posting_date))
            # Use getattr for safety if attributes might be missing from some Job objects
            src_lbl.update(getattr(job, "source", "N/A"))  # Assuming 'source' attribute might exist
            status_lbl.update(job.status or "N/A")
            hid_lbl.update("Yes" if job.hidden else "No")
            link_lbl.update(getattr(job, "details_link", "N/A"))  # Assuming 'details_link' attribute might exist

            # Convert HTML job description to Markdown and update widget
            html_content = getattr(job, "job_description", "N/A")
            markdown_content = self._html_to_markdown(html_content)
            desc_md.update(markdown_content)  # Use update() for Markdown widget
            
            desc_md.display = True
            basic_info_title.display = True
            description_title.display = True
            self.display = True
        else:
            # Clear details when no job is selected
            company_title.update("No Job Selected")
            for lbl in (loc_lbl, sal_lbl, post_lbl, src_lbl, status_lbl, hid_lbl, link_lbl):
                lbl.update("-")

            desc_md.update("")  # Clear markdown content
            desc_md.display = False
            # Hide section titles
            basic_info_title.display = False
            description_title.display = False

            # Keep JobDetail container visible to show "No Job Selected"
            self.display = True