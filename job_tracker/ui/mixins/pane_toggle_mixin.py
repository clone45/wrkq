# job_tracker/ui/mixins/pane_toggle_mixin.py

from typing import Optional
# Import from your custom widgets instead of textual.widgets
from job_tracker.ui.widgets.job_details import JobDetail
from job_tracker.ui.widgets.chat_panel import ChatPanel


class PaneToggleMixin:
    """Mixin handling pane visibility toggling for JobsScreen"""
    
    def watch_show_detail_pane(self, show: bool) -> None:
        """React to changes in show_detail_pane to show/hide the detail view"""
        detail_widget = self.query_one(JobDetail)
        table_widget = self.query_one("#jobs-table")

        if show:
            detail_widget.remove_class("-hidden")
            detail_widget.display = True
            table_widget.styles.height = "1fr"
            detail_widget.styles.height = "2fr"

            if self.selected_job_id:
                 job = self._get_job_data(self.selected_job_id)
                 detail_widget.update_job(job)
            else:
                 detail_widget.update_job(None)
        else:
            detail_widget.add_class("-hidden")
            detail_widget.display = False
            table_widget.styles.height = "1fr"
            detail_widget.styles.height = None
            detail_widget.update_job(None)
    
    def watch_show_chat_pane(self, show: bool) -> None:
        """React to changes in show_chat_pane to show/hide the chat panel"""
        chat_panel = self.query_one(ChatPanel)
        
        if show:
            chat_panel.remove_class("-hidden")
            chat_panel.display = True
            # Adjust layout proportions
        else:
            chat_panel.add_class("-hidden")
            chat_panel.display = False
            
    def action_toggle_detail(self) -> None:
        """Toggle the visibility of the job detail pane"""
        if not self.show_detail_pane and not self.selected_job_id:
             self.notify("Select a job first to view details.", severity="warning", timeout=2)
             return
        self.show_detail_pane = not self.show_detail_pane
        
    def action_toggle_chat(self) -> None:
        """Toggle the visibility of the chat panel"""
        self.show_chat_pane = not self.show_chat_pane

    def on_chat_panel_close_requested(self, event: ChatPanel.CloseRequested) -> None:
        self.show_chat_pane = False