"""
AWX TUI - JSON Preview Modal

Shows the JSON payload that will be sent to the AWX API.
Useful for debugging and learning the API structure.
"""

import json
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea


class JsonPreviewModal(ModalScreen):
    """
    Modal to preview JSON payload before sending to API

    Features:
    - Shows formatted JSON that will be sent to AWX API
    - Automatically redacts sensitive fields (passwords, tokens, secrets)
    - Toggle button to show/hide sensitive information
    - Read-only display with syntax highlighting
    """

    CSS = """
    JsonPreviewModal {
        align: center middle;
    }

    #json_preview_dialog {
        width: 90;
        height: 35;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #json_preview_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #json_preview_area {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }

    #json_preview_notes {
        width: 100%;
        height: auto;
        border: solid $warning;
        background: $boost;
        padding: 1;
        margin-bottom: 1;
        color: $warning;
    }

    #json_preview_buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True, priority=True),
        Binding("ctrl+c", "copy", "Copy", show=True),
    ]

    # List of field names that should be considered sensitive
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "ssh_key_data",
        "vault_password",
        "become_password",
        "credential",
        "authorize_password",
        "client_secret",
        "private_key",
        "passphrase",
    }

    def __init__(
        self,
        json_data: Dict[str, Any],
        title: str = "JSON Preview - API Payload",
        endpoint: Optional[str] = None,
        method: str = "POST",
        notes: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.json_data = json_data
        self.title_text = title
        self.endpoint = endpoint
        self.method = method
        self.notes = notes or []
        self.show_sensitive = False  # Start with sensitive data hidden

    def compose(self) -> ComposeResult:
        """Create the modal layout"""
        with Vertical(id="json_preview_dialog"):
            # Title with endpoint info
            title = self.title_text
            if self.endpoint:
                title += f"\n{self.method} {self.endpoint}"
            yield Static(title, id="json_preview_title")

            # JSON display area (read-only)
            yield TextArea("", language="json", read_only=True, show_line_numbers=True, id="json_preview_area")

            # Notes panel (only if notes provided)
            if self.notes:
                notes_text = "[bold]ℹ Additional Notes:[/bold]\n" + "\n".join(f"• {note}" for note in self.notes)
                yield Static(notes_text, id="json_preview_notes")

            # Action buttons
            with Horizontal(id="json_preview_buttons"):
                yield Button("Toggle Sensitive Info", variant="warning", id="toggle_sensitive")
                yield Button("Close", variant="primary", id="close_button")

    def on_mount(self) -> None:
        """Initialize the modal with JSON content"""
        self._update_json_display()

    def _update_json_display(self) -> None:
        """Update the JSON display with current sensitivity setting"""
        # Get the JSON data (either scrubbed or raw)
        if self.show_sensitive:
            display_data = self.json_data
        else:
            display_data = self._scrub_sensitive_data(self.json_data)

        # Format as pretty JSON
        json_text = json.dumps(display_data, indent=2)

        # Update the text area
        text_area = self.query_one("#json_preview_area", TextArea)
        text_area.text = json_text

    def _scrub_sensitive_data(self, data: Any) -> Any:
        """Recursively scrub sensitive fields from JSON data"""
        if isinstance(data, dict):
            scrubbed = {}
            for key, value in data.items():
                # Check if field name contains any sensitive keywords
                is_sensitive = any(sensitive_field in key.lower() for sensitive_field in self.SENSITIVE_FIELDS)

                # Always recurse into dicts and lists, even if field name is sensitive
                if isinstance(value, (dict, list)):
                    scrubbed[key] = self._scrub_sensitive_data(value)
                elif is_sensitive and value:
                    # Only redact primitive values in sensitive fields
                    scrubbed[key] = "***REMOVED***"
                else:
                    scrubbed[key] = value
            return scrubbed
        elif isinstance(data, list):
            return [self._scrub_sensitive_data(item) for item in data]
        else:
            return data

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "toggle_sensitive":
            self.show_sensitive = not self.show_sensitive
            self._update_json_display()

            # Update button text based on state
            status = "SHOWN" if self.show_sensitive else "HIDDEN"
            self.notify(f"Sensitive information now {status}", timeout=2)
        elif event.button.id == "close_button":
            self.action_close()

    def action_close(self) -> None:
        """Close the modal"""
        self.dismiss()

    def action_copy(self) -> None:
        """Copy JSON to clipboard (if possible)"""
        # Note: Clipboard access is limited in terminal - just show a message
        self.notify("Use mouse to select and copy text", timeout=3)
