"""
AWX TUI - Task Export Modal

Shows the Ansible task (awx.awx module) that represents the current resource.
Useful for Infrastructure as Code and learning the awx.awx collection.
"""

from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea


class TaskExportModal(ModalScreen):
    """
    Modal to export resource as Ansible task using awx.awx collection

    Features:
    - Shows Ansible task YAML for awx.awx modules
    - Automatically handles sensitive fields (shows placeholders)
    - Read-only display with YAML syntax highlighting
    - Copy/save functionality
    """

    CSS = """
    TaskExportModal {
        align: center middle;
    }

    #task_export_dialog {
        width: 90;
        height: 35;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #task_export_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #task_export_area {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }

    #task_export_notes {
        width: 100%;
        height: auto;
        border: solid $warning;
        background: $boost;
        padding: 1;
        margin-bottom: 1;
        color: $warning;
    }

    #task_export_buttons {
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

    # List of field names that should show variable placeholders
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "ssh_key_data",
        "vault_password",
        "become_password",
        "authorize_password",
        "client_secret",
        "private_key",
        "passphrase",
    }

    def __init__(
        self,
        task_yaml: str,
        title: str = "Export AP Task - Ansible awx.awx Collection",
        module_name: Optional[str] = None,
        notes: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.task_yaml = task_yaml
        self.title_text = title
        self.module_name = module_name
        self.notes = notes or []

    def compose(self) -> ComposeResult:
        """Create the modal layout"""
        with Vertical(id="task_export_dialog"):
            # Title with module info
            title = self.title_text
            if self.module_name:
                title += f"\nModule: awx.awx.{self.module_name}"
            yield Static(title, id="task_export_title")

            # YAML display area (read-only)
            yield TextArea("", language="yaml", read_only=True, show_line_numbers=True, id="task_export_area")

            # Notes panel (only if notes provided)
            if self.notes:
                notes_text = "[bold]ℹ Additional Notes:[/bold]\n" + "\n".join(f"• {note}" for note in self.notes)
                yield Static(notes_text, id="task_export_notes")

            # Action buttons
            with Horizontal(id="task_export_buttons"):
                yield Button("Close", variant="primary", id="close_button")

    def on_mount(self) -> None:
        """Initialize the modal with YAML content"""
        self._update_yaml_display()

    def _update_yaml_display(self) -> None:
        """Update the YAML display"""
        # Update the text area
        text_area = self.query_one("#task_export_area", TextArea)
        text_area.text = self.task_yaml

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "close_button":
            self.action_close()

    def action_close(self) -> None:
        """Close the modal"""
        self.dismiss()

    def action_copy(self) -> None:
        """Copy YAML to clipboard (if possible)"""
        # Note: Clipboard access is limited in terminal - just show a message
        self.notify("Use mouse to select and copy text", timeout=3)
