"""
AWX TUI - Confirm Relaunch Modal

Confirmation dialog for job relaunch operations.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from awx_tui.utils import format_time_ago


class ConfirmRelaunchModal(ModalScreen[Optional[str]]):
    """
    Confirmation modal for job relaunch

    Returns:
        "all" if relaunch all hosts
        "failed" if relaunch failed hosts only
        None if cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    ConfirmRelaunchModal {
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

    #job-info {
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

    def __init__(self, job_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.job_data = job_data

    def compose(self) -> ComposeResult:
        # Check job status and type to determine labels and buttons
        status = self.job_data.get("status", "unknown")
        is_workflow = self.job_data.get("type") == "workflow_job"
        title = "Relaunch Workflow Job" if is_workflow else "Relaunch Job"
        all_label = "Relaunch All Nodes" if is_workflow else "Relaunch All Hosts"
        failed_label = "Relaunch Failed Nodes Only" if is_workflow else "Relaunch Failed Only"

        with Vertical(id="confirm-dialog"):
            yield Static(title, id="confirm-title")
            yield Static(self._format_job_info(), id="job-info")
            with Horizontal(id="confirm-buttons"):
                # For failed jobs: show both "Relaunch All" and "Relaunch Failed Only"
                # For successful jobs: show only "Relaunch"
                if status == "failed":
                    yield Button(all_label, variant="primary", id="relaunch-all-button")
                    yield Button(failed_label, variant="warning", id="relaunch-failed-button")
                else:
                    yield Button("Relaunch", variant="primary", id="relaunch-all-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def _format_job_info(self) -> str:
        """Format job information for display"""
        jid = self.job_data.get("id", "Unknown")
        name = self.job_data.get("name", "Unknown")
        summary = self.job_data.get("summary_fields", {})

        org = summary.get("organization", {}).get("name", "N/A")
        inventory = summary.get("inventory", {}).get("name", "N/A")
        project = summary.get("project", {}).get("name", "N/A")
        exec_env = summary.get("execution_environment", {}).get("name", "N/A")
        created_by = summary.get("created_by", {}).get("username", "N/A")

        playbook = self.job_data.get("playbook", "N/A")
        job_type = self.job_data.get("job_type", "run")
        status = self.job_data.get("status", "unknown")

        # Original job finished time
        finished = self.job_data.get("finished")
        finished_str = "Never"
        if finished:
            finished_str = format_time_ago(finished)

        # Status emoji
        status_emoji = {
            "successful": "[green]✓[/green]",
            "failed": "[red]✗[/red]",
            "running": "🏃",
            "error": "❗",
            "canceled": "⚠",
        }.get(status, "❓")

        # Build info display
        is_workflow = self.job_data.get("type") == "workflow_job"
        if is_workflow:
            wf_template = summary.get("workflow_job_template", {}).get("name", "N/A")
            info_lines = [
                f"Workflow Job ID: #{jid}",
                f"Name: {name}",
                f"Organization: {org}",
                f"Created By: {created_by}",
                "",
                "Type: 🔗 WORKFLOW",
                f"Workflow Template: {wf_template}",
                f"Inventory: {inventory}",
                "",
                f"Original Job Status: {status_emoji} {status.title()}",
                f"Finished: {finished_str} ago",
            ]
        else:
            info_lines = [
                f"Job ID: #{jid}",
                f"Name: {name}",
                f"Organization: {org}",
                f"Created By: {created_by}",
                "",
                f"Job Type: {job_type.upper()}",
                f"Inventory: {inventory}",
                f"Project: {project}",
                f"Playbook: {playbook}",
                f"Execution Environment: {exec_env if exec_env != 'N/A' else 'PROJECT DEFAULT'}",
                "",
                f"Original Job Status: {status_emoji} {status.title()}",
                f"Finished: {finished_str} ago",
            ]

        return "\n".join(info_lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "relaunch-all-button":
            self.dismiss("all")
        elif event.button.id == "relaunch-failed-button":
            self.dismiss("failed")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel the relaunch (ESC key)"""
        self.dismiss(None)

    def on_mount(self) -> None:
        """Set focus to the primary relaunch button"""
        # Focus the primary relaunch button by default
        self.query_one("#relaunch-all-button", Button).focus()
