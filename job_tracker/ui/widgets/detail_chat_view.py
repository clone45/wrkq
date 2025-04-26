# job_tracker/ui/widgets/detail_chat_view.py
"""
Combined job detail and chat panel view.
"""
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message

from job_tracker.ui.widgets.job_details import JobDetail
from job_tracker.ui.widgets.chat_panel import ChatPanel
from job_tracker.models.job import Job


class DetailChatView(Container):
    """Combined view with job details and chat panel."""
    
    # ------------------------------------------------------------------ #
    # messages
    # ------------------------------------------------------------------ #
    
    class JobDetailMessage(Message):
        """Forward messages from the job detail widget."""
        def __init__(self, original_message: Message) -> None:
            super().__init__()
            self.original_message = original_message
            
    class ChatMessage(Message):
        """Forward messages from the chat panel."""
        def __init__(self, original_message: Message) -> None:
            super().__init__()
            self.original_message = original_message
    
    # ------------------------------------------------------------------ #
    # compose
    # ------------------------------------------------------------------ #
    
    def compose(self) -> ComposeResult:
        """Build the combined layout."""
        with Container(id="detail-chat-grid"):
            yield JobDetail(id="job-detail")
            yield ChatPanel(id="chat-panel")
    
    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    
    def update_job(self, job: Job | None) -> None:
        """Update the job detail component."""
        job_detail = self.query_one(JobDetail)
        job_detail.update_job(job)
        
        # If a job is selected, we could add context to the chat
        if job:
            chat_panel = self.query_one(ChatPanel)
            chat_panel.add_assistant_message(f"Now viewing details for: {job.company} - {job.title}")
    
    # ------------------------------------------------------------------ #
    # message handling
    # ------------------------------------------------------------------ #
    
    def on_job_detail_hide_job_requested(self, event: JobDetail.HideJobRequested) -> None:
        """Forward job detail messages."""
        self.post_message(self.JobDetailMessage(event))
        
    def on_job_detail_close_detail_requested(self, event: JobDetail.CloseDetailRequested) -> None:
        """Forward job detail messages."""
        self.post_message(self.JobDetailMessage(event))
    
    def on_chat_panel_message_sent(self, event: ChatPanel.MessageSent) -> None:
        """Forward chat panel messages."""
        self.post_message(self.ChatMessage(event))