"""
AWX TUI - Select Workflow Template Modal

Allows picking a Workflow Job Template to launch targeting a specific host
from the Inventory / Hosts screen.
"""

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Static

from awx_tui.utils.launch_prompts import get_active_prompt_fields


class SelectWorkflowModal(ModalScreen[Optional[Dict[str, Any]]]):
    """
    Modal for selecting a workflow job template to launch for a host.

    Returns:
        Selected workflow_job_template dict, or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    SelectWorkflowModal {
        align: center middle;
    }

    #select-wf-dialog {
        width: 90;
        max-height: 85%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #select-wf-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #select-wf-subtitle {
        width: 100%;
        color: $text-muted;
        margin-bottom: 1;
    }

    #select-wf-filter {
        margin-bottom: 1;
    }

    #select-wf-table {
        height: 1fr;
        max-height: 18;
    }

    #select-wf-buttons {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    #select-wf-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        host_name: str,
        inventory_name: str,
        workflows: List[Dict[str, Any]],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.host_name = host_name
        self.inventory_name = inventory_name
        self._all_workflows = workflows
        self._filtered_workflows = list(workflows)

    def compose(self) -> ComposeResult:
        with Vertical(id="select-wf-dialog"):
            yield Static(f"🚀 Launch Template for Host: {self.host_name}", id="select-wf-title")
            yield Static(
                f"Inventory: {self.inventory_name}  |  Templates with 'limit' prompt will pre-fill limit={self.host_name}",
                id="select-wf-subtitle",
            )
            yield Input(placeholder="Filter job & workflow templates by name...", id="select-wf-filter")

            table = DataTable(id="select-wf-table", cursor_type="row")
            table.add_columns("ID", "Type", "Template", "Organization", "Limit Prompt", "Prompts")
            yield table

            with Horizontal(id="select-wf-buttons"):
                yield Button("Select", variant="primary", id="select-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        self._populate_table(self._filtered_workflows)
        self.query_one("#select-wf-table", DataTable).focus()

    def _populate_table(self, workflows: List[Dict[str, Any]]) -> None:
        table = self.query_one("#select-wf-table", DataTable)
        table.clear()

        for wf in workflows:
            wf_id = str(wf.get("id", ""))
            t_type = wf.get("type", "workflow_job_template")
            type_label = "🔀 Workflow" if t_type == "workflow_job_template" else "🚀 Job"
            name = wf.get("name", "Unknown")[:32]
            org = wf.get("summary_fields", {}).get("organization", {}).get("name", "N/A")[:18]
            limit_flag = "[green]✓[/green]" if wf.get("ask_limit_on_launch", False) else "[dim]—[/dim]"
            prompts = get_active_prompt_fields(wf)
            prompt_str = (
                ", ".join(p.replace("ask_", "").replace("_on_launch", "").replace("_enabled", "") for p in prompts)
                if prompts
                else "None"
            )
            table.add_row(wf_id, type_label, name, org, limit_flag, prompt_str[:22])

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "select-wf-filter":
            return
        query = event.value.strip().lower()
        if not query:
            self._filtered_workflows = list(self._all_workflows)
        else:
            self._filtered_workflows = [
                wf
                for wf in self._all_workflows
                if query in wf.get("name", "").lower() or query in wf.get("description", "").lower()
            ]
        self._populate_table(self._filtered_workflows)

    def _dismiss_selected(self) -> None:
        table = self.query_one("#select-wf-table", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            self.dismiss(None)
            return
        idx = table.cursor_row
        if 0 <= idx < len(self._filtered_workflows):
            self.dismiss(self._filtered_workflows[idx])
        else:
            self.dismiss(None)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "select-wf-table":
            self._dismiss_selected()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select-button":
            self._dismiss_selected()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
