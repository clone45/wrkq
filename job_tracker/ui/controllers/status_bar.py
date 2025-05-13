# job_tracker/ui/controllers/status_bar.py
"""Formats and updates the status bar."""

from __future__ import annotations

from typing import Dict, Optional, List, Tuple

from rich.text import Text
from textual.widgets import Static

from job_tracker.models.job import Job


class StatusBarController:
    """Builds the human-readable status text and writes it to the bar."""

    # Task status styles
    STATUS_STYLES = {
        "pending": ("TASKS [!]", "yellow"),
        "in_progress": ("TASKS [⟳]", "blue"),
        "completed": ("TASKS [✓]", "green"),
        "error": ("TASKS [✗]", "red"),
        "none": ("TASKS", "white"),
    }

    def __init__(self, status_bar: Static) -> None:
        self._bar = status_bar
        # Keep track of background task counts
        self._task_counts = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "error": 0
        }

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

        # Add background task status if any tasks exist
        text = self._append_task_status(text)

        self._bar.update(text)

    def update_with_selection(
        self, base_text: str, selected_job: Optional[Job] = None
    ) -> None:
        """Convenience: keep the left part untouched, change selection info."""
        if selected_job:
            text = self._append_selection(base_text, selected_job)
        else:
            text = base_text
        
        # Add background task status
        text = self._append_task_status(text)
        
        self._bar.update(text)

    def update_task_status(
        self, 
        pending: int = 0, 
        in_progress: int = 0, 
        completed: int = 0, 
        error: int = 0
    ) -> None:
        """Update the background task counters and refresh the status bar."""
        self._task_counts = {
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "error": error
        }
        
        # Get the current text and update it
        current_text = self._bar.renderable
        if isinstance(current_text, str):
            # Strip any existing task status
            base_text = self._strip_task_status(current_text)
            updated_text = self._append_task_status(base_text)
            self._bar.update(updated_text)
        else:
            # Handle rich Text objects if necessary
            self._bar.update(self._append_task_status(""))

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _append_selection(text: str, job: Job) -> str:
        comp = job.company or "Unk"
        title = job.title or "Unk"
        return f"{text} | Selected: {comp} - {title}"
    
    def _append_task_status(self, text: str) -> str:
        """Add task status to the status bar if tasks exist."""
        total_tasks = sum(self._task_counts.values())
        
        if total_tasks == 0:
            return text
        
        # Determine the primary status based on priority
        status = "none"
        if self._task_counts["error"] > 0:
            status = "error"
        elif self._task_counts["in_progress"] > 0:
            status = "in_progress"
        elif self._task_counts["pending"] > 0:
            status = "pending"
        elif self._task_counts["completed"] > 0:
            status = "completed"
        
        status_text, _ = self.STATUS_STYLES[status]
        
        # Format the task counts
        task_info = []
        if self._task_counts["pending"] > 0:
            task_info.append(f"P:{self._task_counts['pending']}")
        if self._task_counts["in_progress"] > 0:
            task_info.append(f"I:{self._task_counts['in_progress']}")
        if self._task_counts["completed"] > 0:
            task_info.append(f"C:{self._task_counts['completed']}")
        if self._task_counts["error"] > 0:
            task_info.append(f"E:{self._task_counts['error']}")
        
        task_counts = " ".join(task_info)
        
        # Append to the existing text
        if text:
            return f"{text} | {status_text} {task_counts}"
        else:
            return f"{status_text} {task_counts}"
    
    def _strip_task_status(self, text: str) -> str:
        """Remove any existing task status from the status bar text."""
        for status, (status_text, _) in self.STATUS_STYLES.items():
            if f"| {status_text}" in text:
                return text.split(f"| {status_text}")[0].rstrip()
        return text
