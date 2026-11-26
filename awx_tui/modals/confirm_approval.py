"""
AWX TUI - Confirm Workflow Approval Modal

Dialog for approving or denying a pending workflow approval node.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmApprovalModal(ModalScreen[Optional[str]]):
    """
    Confirmation modal for workflow approval nodes.

    Returns:
        "approve" to approve the node
        "deny" to deny the node
        None if cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    ConfirmApprovalModal {
        align: center middle;
    }

    #approval-dialog {
        width: 72;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #approval-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #approval-info {
        width: 100%;
        color: $text;
        margin: 1 0;
        padding: 1;
        background: $boost;
        border: solid $accent;
    }

    #approval-buttons {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    #approval-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, node_entry: dict, **kwargs):
        super().__init__(**kwargs)
        self.node_entry = node_entry

    def compose(self) -> ComposeResult:
        with Vertical(id="approval-dialog"):
            yield Static("✋  Workflow Approval Required", id="approval-title")
            yield Static(self._format_approval_info(), id="approval-info")
            with Horizontal(id="approval-buttons"):
                yield Button("Approve", variant="success", id="approve-button")
                yield Button("Deny", variant="error", id="deny-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def _format_approval_info(self) -> str:
        """Format approval node details for display"""
        name = self.node_entry.get("name", "Unknown Approval")
        approval_id = self.node_entry.get("job_id", "N/A")
        branch = self.node_entry.get("branch", "N/A")
        node_raw = self.node_entry.get("node") or {}
        summary = node_raw.get("summary_fields", {})
        job_info = summary.get("job") or {}
        description = job_info.get("description") or summary.get("unified_job_template", {}).get("description") or "N/A"

        lines = [
            f"Approval Node: {name}",
            f"Approval ID: #{approval_id}",
            f"Branch: {branch}",
            f"Description: {description[:120]}",
            "",
            "Choose whether to approve or deny this workflow step.",
        ]
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve-button":
            self.dismiss("approve")
        elif event.button.id == "deny-button":
            self.dismiss("deny")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel without taking action (ESC key)"""
        self.dismiss(None)

    def on_mount(self) -> None:
        """Focus the Approve button by default"""
        self.query_one("#approve-button", Button).focus()
