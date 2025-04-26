# job_tracker/ui/widgets/chat_panel.py
"""
Chat panel widget without a header.
"""
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Button, Input, Label
from textual.message import Message

class ChatPanel(Container):
    """Chat interface for the Job Tracker."""
    # ------------------------------------------------------------------ #
    # custom messages
    # ------------------------------------------------------------------ #
    class MessageSent(Message):
        """Emitted when the user sends a chat message."""
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    # ------------------------------------------------------------------ #
    # compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        """Build the widget layout."""
        # message history
        with VerticalScroll(id="chat-history"):
            yield Label(
                "Assistant: Welcome to the Job Tracker! How can I help you today?",
                classes="assistant-message",
            )
        # input row
        with Container(id="chat-input-container"):
            yield Input(placeholder="Type your message here...", id="chat-input")
            yield Button("Send", id="chat-send", variant="primary")

    # ------------------------------------------------------------------ #
    # events
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat-send":
            self._send_message()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            self._send_message()

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _send_message(self) -> None:
        input_widget = self.query_one("#chat-input", Input)
        message = input_widget.value.strip()
        if not message:
            return
        input_widget.value = ""  # clear
        self.add_user_message(message)
        self.post_message(self.MessageSent(message))

    def add_user_message(self, text: str) -> None:
        chat_history = self.query_one("#chat-history", VerticalScroll)
        chat_history.mount(Label(f"You: {text}", classes="user-message"))
        chat_history.scroll_end(animate=False)

    def add_assistant_message(self, text: str) -> None:
        chat_history = self.query_one("#chat-history", VerticalScroll)
        chat_history.mount(Label(f"Assistant: {text}", classes="assistant-message"))
        chat_history.scroll_end(animate=False)