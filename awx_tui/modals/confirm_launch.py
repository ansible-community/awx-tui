"""
AWX TUI - Confirm Launch Modal

Confirmation dialog for job template launch operations.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from awx_tui.utils import format_time_ago


class ConfirmLaunchModal(ModalScreen[bool]):
    """
    Confirmation modal for job template launch

    Returns True if user confirms, False if cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    ConfirmLaunchModal {
        align: center middle;
    }

    #confirm-dialog {
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #confirm-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #template-info {
        width: 100%;
        color: $text;
        margin: 1 0;
        padding: 1;
        background: $boost;
        border: solid $accent;
    }

    #confirm-buttons {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, template_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.template_data = template_data

    def compose(self) -> ComposeResult:
        is_workflow = self.template_data.get("type") == "workflow_job_template"
        title = "Launch Workflow Template" if is_workflow else "Launch Job Template"

        with Vertical(id="confirm-dialog"):
            yield Static(title, id="confirm-title")
            yield Static(self._format_template_info(), id="template-info")
            with Horizontal(id="confirm-buttons"):
                yield Button("Launch", variant="primary", id="launch-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def _format_template_info(self) -> str:
        """Format template information for display"""
        name = self.template_data.get("name", "Unknown")
        summary = self.template_data.get("summary_fields", {})

        org = summary.get("organization", {}).get("name", "N/A")
        inventory = summary.get("inventory", {}).get("name", "N/A")
        project = summary.get("project", {}).get("name", "N/A")
        exec_env = summary.get("execution_environment", {}).get("name", "N/A")

        playbook = self.template_data.get("playbook", "N/A")
        job_type = self.template_data.get("job_type", "run")

        # Last run info
        last_job = summary.get("last_job", {})
        last_run_str = "Never"
        last_status_str = "N/A"

        if last_job:
            last_status = last_job.get("status", "unknown")
            last_finished = last_job.get("finished")

            # Status emoji
            status_emoji = {
                "successful": "[green]✓[/green]",
                "failed": "[red]✗[/red]",
                "running": "🏃",
                "error": "❗",
                "canceled": "⚠",
            }.get(last_status, "❓")

            last_status_str = f"{status_emoji} {last_status.title()}"

            if last_finished:
                last_run_str = format_time_ago(last_finished)

        # Build info display
        is_workflow = self.template_data.get("type") == "workflow_job_template"
        if is_workflow:
            description = self.template_data.get("description") or "N/A"
            info_lines = [
                f"Workflow Template: {name}",
                f"Organization: {org}",
                "Type: 🔀 WORKFLOW",
                f"Inventory: {inventory}",
                f"Description: {description[:60]}",
                "",
                f"Last Run: {last_run_str}",
                f"Last Status: {last_status_str}",
            ]
        else:
            info_lines = [
                f"Template: {name}",
                f"Organization: {org}",
                f"Job Type: {job_type.upper()}",
                "",
                f"Inventory: {inventory}",
                f"Project: {project}",
                f"Playbook: {playbook}",
                f"Execution Environment: {exec_env if exec_env != 'N/A' else 'PROJECT DEFAULT'}",
                "",
                f"Last Run: {last_run_str}",
                f"Last Status: {last_status_str}",
            ]

        return "\n".join(info_lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-button":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel the launch (ESC key)"""
        self.dismiss(False)

    def on_mount(self) -> None:
        """Focus the Launch button by default"""
        self.query_one("#launch-button", Button).focus()
