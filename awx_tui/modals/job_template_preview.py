"""
AWX TUI - Job Template Preview Modal

Read-only preview for Job Templates (especially those with prompt-on-launch
or survey fields enabled that cannot be edited inline), with direct Launch support.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Static

from awx_tui.utils.launch_prompts import get_active_prompt_fields


class JobTemplatePreviewModal(ModalScreen[Optional[str]]):
    """
    Read-only preview modal for a Job Template.

    Returns:
        "launch" if the user clicks Launch / presses Ctrl+L
        None if closed
    """

    CSS = """
    JobTemplatePreviewModal {
        align: center middle;
    }

    #jt-preview-container {
        width: 85;
        height: auto;
        max-height: 85%;
        border: solid $primary;
        background: $surface;
    }

    #jt-preview-body {
        width: 100%;
        padding: 1 2;
        background: $boost;
        margin: 1;
        border: solid $accent;
    }

    #jt-preview-actions {
        height: auto;
        align: center middle;
        padding: 1;
        border-top: solid $primary;
    }

    #jt-preview-actions Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Quit"),
        Binding("ctrl+l", "launch", "Launch", show=True),
    ]

    def __init__(self, template_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.template_data = template_data
        self.template_id = template_data.get("id")

    def compose(self) -> ComposeResult:
        with Vertical(id="jt-preview-container"):
            yield Header()
            yield Static(self._format_preview(), id="jt-preview-body")
            with Horizontal(id="jt-preview-actions"):
                yield Button("Launch Template (Ctrl+L)", variant="primary", id="launch-jt-button")
                yield Button("Close (Esc)", variant="default", id="close-jt-button")
            yield Footer()

    def on_mount(self) -> None:
        self.title = f"Job Template Preview - {self.template_data.get('name', f'#{self.template_id}')}"

    def _format_preview(self) -> str:
        """Format job template details for read-only display."""
        t = self.template_data
        name = t.get("name", "Unknown")
        description = t.get("description") or "No description"
        job_type = (t.get("job_type") or "run").upper()
        playbook = t.get("playbook") or "N/A"
        summary = t.get("summary_fields", {})
        org = summary.get("organization", {}).get("name", "N/A")
        project = summary.get("project", {}).get("name", "N/A")
        inventory = summary.get("inventory", {}).get("name", "N/A")
        ee = summary.get("execution_environment", {}).get("name", "PROJECT DEFAULT")

        active_prompts = get_active_prompt_fields(t)
        if active_prompts:
            short = [p.replace("ask_", "").replace("_on_launch", "").replace("_enabled", "") for p in active_prompts]
            prompts_str = ", ".join(short)
        else:
            prompts_str = "None"

        lines = [
            f"🚀 [bold]Job Template #{self.template_id}: {name}[/bold]",
            f"📝 {description[:100]}",
            "",
            f"Organization:          {org}",
            f"Job Type:              {job_type}",
            f"Project:               {project}",
            f"Playbook:              {playbook}",
            f"Inventory:             {inventory}",
            f"Execution Environment: {ee}",
            "",
            f"📋 Prompts on launch:  [yellow]{prompts_str}[/yellow]",
            "",
            "[dim]Read-only preview (templates with prompt-on-launch fields cannot be edited inline).[/dim]",
        ]
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-jt-button":
            self.dismiss("launch")
        else:
            self.dismiss(None)

    def action_launch(self) -> None:
        self.dismiss("launch")

    def action_close(self) -> None:
        self.dismiss(None)
