# job_tracker/ui/controllers/status_bar.py
"""Formats and updates the status bar."""

from __future__ import annotations

from typing import Dict, Optional

from textual.widgets import Static

from job_tracker.models.job import Job


class StatusBarController:
    """Builds the human-readable status text and writes it to the bar."""

    def __init__(self, status_bar: Static) -> None:
        self._bar = status_bar

    # ------------------------------------------------------------------ #
    # public helpers
    # ------------------------------------------------------------------ #

    def update(
        self,
        meta: Dict[str, int | str | bool],
        selected_job_id: Optional[str] = None,
        selected_job: Optional[Job] = None,
    ) -> None:
        """
        Refresh the whole status line.

        `meta` expected keys:
            total, pages, current_page, search_query, show_hidden
        """
        parts: list[str] = [
            f"Jobs: {meta.get('total', 0)}",
            f"Page: {meta.get('current_page', 1)}/{meta.get('pages', 1)}",
        ]

        if meta.get("search_query"):
            parts.append(f"Search: '{meta['search_query']}'")
        if meta.get("show_hidden"):
            parts.append("Hidden: Yes")

        text = " | ".join(parts)

        if selected_job_id and selected_job:
            text = self._append_selection(text, selected_job)

        self._bar.update(text)

    def update_with_selection(
        self, base_text: str, selected_job: Optional[Job] = None
    ) -> None:
        """Convenience: keep the left part untouched, change selection info."""
        self._bar.update(
            self._append_selection(base_text, selected_job) if selected_job else base_text
        )

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _append_selection(text: str, job: Job) -> str:
        comp = job.company or "Unk"
        title = job.title or "Unk"
        return f"{text} | Selected: {comp} - {title}"
