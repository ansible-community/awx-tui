"""
AWX TUI - Confirm Cancel Job Modal

Simple confirmation modal for canceling a running job.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmCancelModal(ModalScreen[bool]):
    """
    Confirmation modal for canceling a job

    Returns:
        True if confirmed
        False if cancelled
    """

    CSS = """
    ConfirmCancelModal {
        align: center middle;
    }

    #confirm-dialog {
        width: 60;
        height: auto;
        border: thick $error 80%;
        background: $surface;
        padding: 1;
    }

    #confirm-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $error;
        background: $boost;
        padding: 1;
        margin-bottom: 1;
    }

    #job-info {
        width: 100%;
        height: auto;
        padding: 1;
        margin-bottom: 1;
    }

    #confirm-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding-top: 1;
    }

    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, job_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.job_data = job_data

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static("🛑  Cancel Job?  🛑", id="confirm-title")
            yield Static(self._format_job_info(), id="job-info")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel Job", variant="error", id="cancel-job-button")
                yield Button("Keep Running", variant="default", id="keep-running-button")

    def _format_job_info(self) -> str:
        """Format job information for display"""
        job_id = self.job_data.get("id", "Unknown")
        name = self.job_data.get("name", "Unknown")
        status = self.job_data.get("status", "unknown")
        is_workflow = self.job_data.get("type") == "workflow_job"

        summary = self.job_data.get("summary_fields", {})
        user = summary.get("created_by", {}).get("username", "N/A")
        if is_workflow:
            template = summary.get("workflow_job_template", {}).get("name", "N/A")
            label = "Workflow Job"
        else:
            template = summary.get("job_template", {}).get("name", "N/A")
            label = "Job"

        return f"""{label} #{job_id}: {name}
Status: {status.upper()}
Template: {template}
User: {user}

Are you sure you want to cancel this {label.lower()}?
This action cannot be undone."""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-job-button":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """ESC key cancels the cancel (keeps job running)"""
        self.dismiss(False)
