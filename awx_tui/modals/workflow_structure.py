"""
AWX TUI - Workflow Template Structure Preview Modal

Read-only preview of a Workflow Job Template's static node graph
(`/api/v2/workflow_job_templates/{id}/workflow_nodes/`), with an option
to launch the workflow directly from the preview.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Static

from awx_tui.utils.launch_prompts import get_active_prompt_fields
from awx_tui.utils.workflow import format_node_transitions, order_workflow_nodes


class WorkflowStructureModal(ModalScreen[Optional[str]]):
    """
    Modal displaying the static node structure of a Workflow Job Template.

    Returns:
        "launch" if the user clicks Launch / presses Ctrl+L
        None if closed
    """

    CSS = """
    WorkflowStructureModal {
        align: center middle;
    }

    #wf-structure-container {
        width: 95%;
        height: 90%;
        border: solid $primary;
        background: $surface;
    }

    #wf-structure-header {
        dock: top;
        height: auto;
        background: $boost;
        padding: 1;
        border-bottom: solid $primary;
    }

    #workflow-structure-table {
        height: 1fr;
    }

    #wf-structure-actions {
        height: auto;
        align: center middle;
        padding: 1;
        border-top: solid $primary;
    }

    #wf-structure-actions Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("f5", "refresh", "Refresh"),
        Binding("ctrl+l", "launch", "Launch", show=True),
    ]

    def __init__(self, template_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.template_data = template_data
        self.template_id = template_data.get("id")
        self._nodes = []
        self._loading = False

    def compose(self) -> ComposeResult:
        with Vertical(id="wf-structure-container"):
            yield Header()
            yield Static(self._format_header(node_count=None), id="wf-structure-header")

            table = DataTable(id="workflow-structure-table", cursor_type="row")
            table.add_columns("Step", "Node / Template", "Branch", "Type", "Converge", "Next Nodes")
            yield table

            with Horizontal(id="wf-structure-actions"):
                yield Button("Launch Workflow (Ctrl+L)", variant="primary", id="launch-wf-button")
                yield Button("Close (Esc)", variant="default", id="close-wf-button")

            yield Footer()

    def _format_header(self, node_count: Optional[int] = None) -> str:
        """Format compact workflow template header info."""
        name = self.template_data.get("name", "Unknown")
        summary = self.template_data.get("summary_fields", {})
        org = summary.get("organization", {}).get("name", "N/A")
        description = self.template_data.get("description") or "No description"

        active_prompts = get_active_prompt_fields(self.template_data)
        if active_prompts:
            short_prompts = [
                p.replace("ask_", "").replace("_on_launch", "").replace("_enabled", "") for p in active_prompts
            ]
            prompts_str = ", ".join(short_prompts)
        else:
            prompts_str = "None"

        nodes_str = "Loading..." if node_count is None else str(node_count)
        return (
            f"🔀 Workflow Template #{self.template_id}: [bold]{name[:65]}[/bold] | 🏢 {org} | Nodes: {nodes_str}\n"
            f"📝 {description[:90]}\n"
            f"📋 Prompts on launch: {prompts_str}  |  Legend: [green]✓[/green] on success  [red]✗[/red] on failure  [cyan]*[/cyan] always"
        )

    async def on_mount(self) -> None:
        self.title = f"Workflow Structure - {self.template_data.get('name', f'#{self.template_id}')}"
        self.run_worker(self._load_nodes())

    async def _load_nodes(self) -> None:
        """Fetch workflow template nodes from API and populate table."""
        if self._loading:
            return
        self._loading = True
        try:
            client = self.app.instance_manager.get_current_client()
            endpoint = f"/api/v2/workflow_job_templates/{self.template_id}/workflow_nodes/"

            from awx_tui.client import AWXClient

            async def _fetch(c):
                if hasattr(c, "get_all_pages"):
                    return await c.get_all_pages(endpoint, params={"page_size": 200})
                resp = await c.get(endpoint, params={"page_size": 200})
                return resp.get("results", [])

            if isinstance(client, AWXClient):
                async with client:
                    raw_nodes = await _fetch(client)
            else:
                raw_nodes = await _fetch(client)

            ordered = order_workflow_nodes(raw_nodes)
            self._nodes = ordered

            header = self.query_one("#wf-structure-header", Static)
            header.update(self._format_header(node_count=len(ordered)))

            self._populate_table(ordered)
        except Exception as e:
            self.app.log.error(f"Failed to load workflow template nodes: {e}")
            self.notify(f"Error loading workflow structure: {e}", severity="error")
        finally:
            self._loading = False

    def _populate_table(self, ordered_nodes: list) -> None:
        """Populate the workflow structure DataTable."""
        table = self.query_one("#workflow-structure-table", DataTable)
        table.clear()

        id_to_step = {entry["node_id"]: entry["step"] for entry in ordered_nodes}

        type_emoji_map = {
            "job": "🚀 Job",
            "project_update": "🔄 Project",
            "inventory_update": "📥 Inventory",
            "workflow_job": "🔗 Workflow",
            "workflow_approval": "✋ Approval",
            "system_job": "🔧 System",
        }

        for entry in ordered_nodes:
            indent = "  " * min(entry["depth"], 4)
            node_name = f"{indent}{entry['name'][:42]}"
            type_str = type_emoji_map.get(entry["node_type"], entry["node_type"])
            raw_node = entry.get("node") or {}
            converge_str = "ALL" if raw_node.get("all_parents_must_converge") else "ANY"
            next_str = format_node_transitions(entry, id_to_step)

            table.add_row(
                str(entry["step"]),
                node_name,
                entry["branch"],
                type_str,
                converge_str,
                next_str,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-wf-button":
            self.dismiss("launch")
        else:
            self.dismiss(None)

    def action_launch(self) -> None:
        """Launch the workflow template from preview (Ctrl+L)"""
        self.dismiss("launch")

    def action_refresh(self) -> None:
        """Refresh workflow template nodes"""
        self.run_worker(self._load_nodes())

    def action_close(self) -> None:
        """Close the modal"""
        self.dismiss(None)
