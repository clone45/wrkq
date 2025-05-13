# job_tracker/ui/messages.py
"""Message classes for the application."""

from __future__ import annotations

from textual.message import Message


class TaskStatusUpdate(Message):
    """Message for task status updates."""
    
    def __init__(
        self,
        task_id: str,
        task_type: str,
        status: str,
        progress_value: int = 0,
        progress_total: int = 100,
        message: str = "",
    ) -> None:
        """Initialize with task details."""
        super().__init__()
        self.task_id = task_id
        self.task_type = task_type
        self.status = status
        self.progress_value = progress_value
        self.progress_total = progress_total
        self.message = message