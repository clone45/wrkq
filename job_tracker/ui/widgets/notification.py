# job_tracker/ui/widgets/notification.py
"""Toast notification widget for displaying status messages."""

from __future__ import annotations

from typing import Optional, Callable, Any
from datetime import datetime, timedelta

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static


class NotificationToast(Static):
    """A toast notification that automatically disappears after a timeout."""
    
    level = reactive("info")  # info, warning, error, success
    auto_dismiss = reactive(True)
    remaining_time = reactive(5.0)  # seconds
    
    def __init__(
        self,
        message: str,
        *,
        level: str = "info",
        auto_dismiss: bool = True,
        timeout: float = 5.0,
        on_dismiss: Optional[Callable[[], None]] = None,
        id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a notification toast."""
        super().__init__("", id=id, **kwargs)
        self.message = message
        self.level = level
        self.auto_dismiss = auto_dismiss
        self.remaining_time = timeout
        self.on_dismiss_callback = on_dismiss
        self.dismiss_timer_id: Optional[str] = None
        self.start_time = datetime.now()
    
    def on_mount(self) -> None:
        """Start the dismissal timer when mounted."""
        if self.auto_dismiss:
            self.dismiss_timer_id = self.set_interval(0.1, self.update_remaining_time)
    
    def on_click(self) -> None:
        """Dismiss the notification when clicked."""
        self.dismiss()
    
    def update_remaining_time(self) -> None:
        """Update the remaining time and dismiss if expired."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.remaining_time = max(0.0, 5.0 - elapsed)
        
        if self.remaining_time <= 0:
            self.dismiss()
    
    def dismiss(self) -> None:
        """Remove the notification."""
        # Simply remove the notification without trying to cancel the timer
        # This is safe because the widget will be gone and the timer callback won't have an effect
        if self.on_dismiss_callback:
            self.on_dismiss_callback()
        
        self.remove()
    
    def render(self) -> RenderableType:
        """Render the notification with appropriate styling."""
        # Set title and style based on level
        if self.level == "info":
            title = "Information"
            style = "blue"
            icon = "ℹ"
        elif self.level == "warning":
            title = "Warning"
            style = "yellow"
            icon = "⚠"
        elif self.level == "error":
            title = "Error"
            style = "red"
            icon = "✗"
        elif self.level == "success":
            title = "Success"
            style = "green"
            icon = "✓"
        else:
            title = "Notification"
            style = "white"
            icon = "*"

        # Create the message with an icon
        text = Text()
        text.append(f"{icon} ", style=style)
        text.append(self.message)
        
        # Add remaining time if auto-dismiss is enabled
        if self.auto_dismiss and self.remaining_time > 0:
            seconds_left = round(self.remaining_time)
            text.append(f" ({seconds_left}s)", style="bright_black")
        
        return Panel(
            text,
            title=title,
            border_style=style,
            padding=(0, 1),
        )


class NotificationContainer(Widget):
    """Container for managing multiple notification toasts."""
    
    def __init__(self) -> None:
        """Initialize the notification container."""
        super().__init__(id="notification-container")
        self.notifications: list[NotificationToast] = []
    
    def compose(self) -> ComposeResult:
        """No default content."""
        yield Container(id="notifications-wrapper")
    
    def add_notification(
        self,
        message: str,
        level: str = "info",
        timeout: float = 5.0,
        auto_dismiss: bool = True,
    ) -> None:
        """Add a new notification toast."""
        # Generate a unique ID (using underscores instead of dashes and timestamp)
        notification_id = f"notification_{len(self.notifications)}_{str(datetime.now().timestamp()).replace('.', '_')}"
        
        # Create the notification toast
        notification = NotificationToast(
            message=message,
            level=level,
            auto_dismiss=auto_dismiss,
            timeout=timeout,
            on_dismiss=lambda: self.notifications.remove(notification),
            id=notification_id,
            classes="notification-toast",
        )
        
        # Add to the list and mount
        self.notifications.append(notification)
        self.query_one("#notifications-wrapper").mount(notification)
    
    def clear_all(self) -> None:
        """Clear all notifications."""
        while self.notifications:
            notification = self.notifications.pop()
            notification.dismiss()