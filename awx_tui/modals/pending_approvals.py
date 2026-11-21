"""
AWX TUI - Pending Workflow Approvals Quick-View Modal

Lists pending workflow approval nodes (`/api/v2/workflow_approvals/?status=pending`)
and lets operators approve, deny, or inspect the parent workflow job directly.
"""

from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Static

from awx_tui.utils import format_time_ago


def build_approval_node_entry(approval: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a `/api/v2/workflow_approvals/` item into the entry shape expected by ConfirmApprovalModal."""
    summary = approval.get("summary_fields", {})
    source_wf = summary.get("source_workflow_job") or {}
    wf_name = source_wf.get("name", "N/A")
    wf_id = source_wf.get("id")
    branch_info = f"Workflow #{wf_id}: {wf_name}" if wf_id else wf_name

    return {
        "name": approval.get("name", f"Approval #{approval.get('id', '?')}"),
        "job_id": approval.get("id"),
        "branch": branch_info,
        "node": {
            "summary_fields": {
                "job": {
                    "description": approval.get("description", ""),
                }
            }
        },
    }


class PendingApprovalsModal(ModalScreen[bool]):
    """
    Quick-view modal for pending workflow approvals.

    Returns:
        True if any approval was approved or denied, False otherwise.
    """

    CSS = """
    PendingApprovalsModal {
        align: center middle;
    }

    #approvals-container {
        width: 92%;
        height: 85%;
        border: solid $accent;
        background: $surface;
    }

    #approvals-header {
        dock: top;
        height: auto;
        background: $boost;
        padding: 1;
        border-bottom: solid $accent;
    }

    #pending-approvals-table {
        height: 1fr;
    }

    #approvals-actions {
        dock: bottom;
        height: 3;
        align: center middle;
        padding: 0 1;
        border-top: solid $accent;
    }

    #approvals-actions Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("f5", "refresh", "Refresh"),
        Binding("w", "inspect_workflow", "Inspect Workflow", show=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._approvals: List[Dict[str, Any]] = []
        self._loading = False
        self._modified = False

    def compose(self) -> ComposeResult:
        with Vertical(id="approvals-container"):
            yield Header()
            yield Static("✋ Pending Workflow Approvals (Loading...)", id="approvals-header")

            table = DataTable(id="pending-approvals-table", cursor_type="row")
            table.add_columns("ID", "Approval Name", "Workflow Job", "Created", "Expires")
            yield table

            with Horizontal(id="approvals-actions"):
                yield Button("Review (Enter)", variant="primary", id="review-button")
                yield Button("Inspect Workflow (w)", variant="default", id="inspect-wf-button")
                yield Button("Close (Esc)", variant="default", id="close-button")

            yield Footer()

    async def on_mount(self) -> None:
        self.title = "Pending Workflow Approvals"
        self.run_worker(self._load_approvals())

    async def _load_approvals(self) -> None:
        """Fetch pending workflow approvals from API."""
        if self._loading:
            return
        self._loading = True
        try:
            from awx_tui.client import AWXClient

            client = self.app.instance_manager.get_current_client()
            endpoint = "/api/v2/workflow_approvals/"
            params = {"status": "pending", "page_size": 200}

            if isinstance(client, AWXClient):
                async with client:
                    resp = await client.get(endpoint, params=params)
            else:
                resp = await client.get(endpoint, params=params)

            self._approvals = resp.get("results", [])
            self._populate_table()
        except Exception as e:
            self.app.log.error(f"Failed to load pending approvals: {e}")
            self.notify(f"Error loading pending approvals: {e}", severity="error")
        finally:
            self._loading = False

    def _populate_table(self) -> None:
        """Update header and DataTable with current pending approvals."""
        count = len(self._approvals)
        header = self.query_one("#approvals-header", Static)
        if count == 0:
            header.update("✋ Pending Workflow Approvals (0) — [green]All caught up![/green]")
        else:
            header.update(
                f"✋ Pending Workflow Approvals ([bold magenta]{count}[/bold magenta])  |  "
                "Press [bold]Enter[/bold] to Approve/Deny, [bold]w[/bold] to inspect parent workflow"
            )

        table = self.query_one("#pending-approvals-table", DataTable)
        table.clear()

        for item in self._approvals:
            approval_id = str(item.get("id", ""))
            name = item.get("name", "Unknown")[:38]
            summary = item.get("summary_fields", {})
            source_wf = summary.get("source_workflow_job") or {}
            wf_id = source_wf.get("id")
            wf_name = source_wf.get("name", "N/A")
            wf_display = f"#{wf_id} {wf_name[:30]}" if wf_id else wf_name[:35]

            created = item.get("created")
            created_str = f"{format_time_ago(created)} ago" if created else "N/A"

            expiration = item.get("approval_expiration")
            expires_str = expiration[:19].replace("T", " ") if expiration else "No timeout"

            table.add_row(approval_id, name, wf_display, created_str, expires_str)

        if table.row_count > 0:
            table.focus()

    def _get_selected_approval(self) -> Dict[str, Any] | None:
        table = self.query_one("#pending-approvals-table", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return None
        idx = table.cursor_row
        if 0 <= idx < len(self._approvals):
            return self._approvals[idx]
        return None

    async def _review_selected(self) -> None:
        approval = self._get_selected_approval()
        if not approval:
            self.notify("No pending approval selected", severity="warning", timeout=2)
            return

        from awx_tui.client import AWXClient
        from awx_tui.modals.confirm_approval import ConfirmApprovalModal

        entry = build_approval_node_entry(approval)
        decision = await self.app.push_screen_wait(ConfirmApprovalModal(entry))
        if decision not in ("approve", "deny"):
            return

        approval_id = approval.get("id")
        approval_name = approval.get("name", "Approval")
        endpoint = f"/api/v2/workflow_approvals/{approval_id}/{decision}/"

        try:
            client = self.app.instance_manager.get_current_client()
            if isinstance(client, AWXClient):
                async with client:
                    await client.post(endpoint, data={})
            else:
                await client.post(endpoint, data={})

            self._modified = True
            past_tense = "approved" if decision == "approve" else "denied"
            self.notify(f"[green]✓[/green] Approval '{approval_name}' (#{approval_id}) {past_tense}", timeout=4)
            await self._load_approvals()
        except Exception as e:
            self.app.log.error(f"Failed to {decision} approval #{approval_id}: {e}")
            self.notify(f"[red]✗[/red] Failed to {decision} approval: {e}", severity="error", timeout=5)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "pending-approvals-table":
            self.run_worker(self._review_selected())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "review-button":
            self.run_worker(self._review_selected())
        elif event.button.id == "inspect-wf-button":
            self.action_inspect_workflow()
        else:
            self.action_close()

    def action_inspect_workflow(self) -> None:
        """Open JobDetailModal for the parent workflow job of the selected approval"""
        approval = self._get_selected_approval()
        if not approval:
            self.notify("No pending approval selected", severity="warning", timeout=2)
            return

        source_wf = approval.get("summary_fields", {}).get("source_workflow_job") or {}
        wf_id = source_wf.get("id")
        if not wf_id:
            self.notify("No parent workflow job associated with this approval", severity="warning", timeout=3)
            return

        from awx_tui.modals.job_detail import JobDetailModal

        self.app.push_screen(JobDetailModal(job_id=wf_id, job_type="workflow_job"))

    def action_refresh(self) -> None:
        self.run_worker(self._load_approvals())

    def action_close(self) -> None:
        self.dismiss(self._modified)
