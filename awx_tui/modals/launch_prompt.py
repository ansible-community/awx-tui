"""
AWX TUI - Launch Prompt & Survey Modal

Collects prompt-on-launch parameters and survey answers before launching
a Job Template or Workflow Job Template.
"""

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, SelectionList, Static, Switch, TextArea
from textual.widgets.selection_list import Selection

from awx_tui.utils.launch_prompts import build_launch_payload, parse_survey_choices

# Textual 8+ uses Select.NULL for blank selection (Select.BLANK is False in Textual 8)
_SELECT_EMPTY = getattr(Select, "NULL", Select.BLANK)


class LaunchPromptModal(ModalScreen[Optional[Dict[str, Any]]]):
    """
    Modal dialog for collecting prompt-on-launch fields and survey answers.

    Returns:
        Dict payload to POST to `/launch/` if confirmed, or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    LaunchPromptModal {
        align: center middle;
    }

    #launch-prompt-dialog {
        width: 90;
        max-height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #launch-prompt-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #launch-prompt-scroll {
        height: 1fr;
        max-height: 30;
        padding: 0 1;
    }

    .section-header {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }

    .field-label {
        margin-top: 1;
        color: $text;
    }

    .field-help {
        color: $text-muted;
    }

    #prompt-extra-vars,
    .survey-textarea {
        height: 6;
    }

    .survey-multiselect {
        height: 6;
    }

    #launch-prompt-errors {
        width: 100%;
        color: $error;
        margin-top: 1;
        display: none;
    }

    #launch-prompt-errors.visible {
        display: block;
    }

    #launch-prompt-buttons {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    #launch-prompt-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        template_data: Dict[str, Any],
        launch_info: Optional[Dict[str, Any]] = None,
        survey_spec: Optional[Dict[str, Any]] = None,
        inventories: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.template_data = template_data
        self.launch_info = launch_info or {}
        self.survey_spec = (survey_spec or {}).get("spec", [])
        self.survey_title = (survey_spec or {}).get("name") or "Survey"
        self.survey_description = (survey_spec or {}).get("description") or ""
        self.inventories = inventories or []
        self._survey_widget_map: Dict[str, tuple[str, str]] = {}  # variable -> (widget_id, q_type)

    def _flag(self, name: str) -> bool:
        """Check whether a prompt flag is enabled in launch_info or template_data."""
        if name in self.launch_info:
            return bool(self.launch_info.get(name, False))
        return bool(self.template_data.get(name, False))

    def _default(self, key: str, fallback: Any = "") -> Any:
        """Read a default value from launch_info.defaults or template_data."""
        defaults = self.launch_info.get("defaults") or {}
        if key in defaults and defaults[key] is not None:
            return defaults[key]
        val = self.template_data.get(key)
        return fallback if val is None else val

    def compose(self) -> ComposeResult:
        is_workflow = self.template_data.get("type") == "workflow_job_template"
        kind = "Workflow Template" if is_workflow else "Job Template"
        name = self.template_data.get("name", "Unknown")

        with Vertical(id="launch-prompt-dialog"):
            yield Static(f"Launch {kind}: {name}", id="launch-prompt-title")

            with VerticalScroll(id="launch-prompt-scroll"):
                has_standard_prompts = any(
                    self._flag(f)
                    for f in (
                        "ask_inventory_on_launch",
                        "ask_limit_on_launch",
                        "ask_scm_branch_on_launch",
                        "ask_tags_on_launch",
                        "ask_skip_tags_on_launch",
                        "ask_job_type_on_launch",
                        "ask_verbosity_on_launch",
                        "ask_diff_mode_on_launch",
                        "ask_forks_on_launch",
                        "ask_variables_on_launch",
                    )
                )

                if has_standard_prompts:
                    yield Static("Launch Parameters", classes="section-header")

                if self._flag("ask_inventory_on_launch"):
                    yield Label("Inventory", classes="field-label")
                    inv_options = [
                        (f"{inv.get('name', 'Unknown')} (#{inv.get('id')})", inv.get("id")) for inv in self.inventories
                    ]
                    default_inv = self._default("inventory", None)
                    if isinstance(default_inv, dict):
                        default_inv = default_inv.get("id")
                    valid_ids = {opt[1] for opt in inv_options}
                    initial_inv = (
                        default_inv
                        if (not isinstance(default_inv, bool) and default_inv in valid_ids)
                        else _SELECT_EMPTY
                    )
                    yield Select(
                        inv_options,
                        prompt="Select inventory...",
                        value=initial_inv,
                        allow_blank=True,
                        id="prompt-inventory",
                    )

                if self._flag("ask_limit_on_launch"):
                    yield Label("Limit (host pattern)", classes="field-label")
                    yield Input(
                        value=str(self._default("limit", "")),
                        placeholder="e.g. webservers:&prod",
                        id="prompt-limit",
                    )

                if self._flag("ask_scm_branch_on_launch"):
                    yield Label("SCM Branch / Tag / Commit", classes="field-label")
                    yield Input(
                        value=str(self._default("scm_branch", "")),
                        placeholder="e.g. main",
                        id="prompt-scm-branch",
                    )

                if self._flag("ask_tags_on_launch"):
                    yield Label("Job Tags (comma-separated)", classes="field-label")
                    yield Input(
                        value=str(self._default("job_tags", "")),
                        placeholder="e.g. deploy,config",
                        id="prompt-job-tags",
                    )

                if self._flag("ask_skip_tags_on_launch"):
                    yield Label("Skip Tags (comma-separated)", classes="field-label")
                    yield Input(
                        value=str(self._default("skip_tags", "")),
                        placeholder="e.g. debug",
                        id="prompt-skip-tags",
                    )

                if not is_workflow and self._flag("ask_job_type_on_launch"):
                    yield Label("Job Type", classes="field-label")
                    default_jt = str(self._default("job_type", "run"))
                    yield Select(
                        [("Run", "run"), ("Check (Dry Run)", "check")],
                        value=default_jt if default_jt in ("run", "check") else "run",
                        allow_blank=False,
                        id="prompt-job-type",
                    )

                if not is_workflow and self._flag("ask_verbosity_on_launch"):
                    yield Label("Verbosity", classes="field-label")
                    default_verb = int(self._default("verbosity", 0) or 0)
                    yield Select(
                        [
                            ("0 (Normal)", 0),
                            ("1 (Verbose)", 1),
                            ("2 (More Verbose)", 2),
                            ("3 (Debug)", 3),
                            ("4 (Connection Debug)", 4),
                            ("5 (WinRM Debug)", 5),
                        ],
                        value=default_verb if 0 <= default_verb <= 5 else 0,
                        allow_blank=False,
                        id="prompt-verbosity",
                    )

                if not is_workflow and self._flag("ask_diff_mode_on_launch"):
                    yield Label("Show Changes (Diff Mode)", classes="field-label")
                    yield Switch(value=bool(self._default("diff_mode", False)), id="prompt-diff-mode")

                if not is_workflow and self._flag("ask_forks_on_launch"):
                    yield Label("Forks", classes="field-label")
                    default_forks = self._default("forks", "")
                    yield Input(
                        value="" if default_forks == "" else str(default_forks),
                        placeholder="e.g. 5",
                        id="prompt-forks",
                    )

                if self._flag("ask_variables_on_launch"):
                    yield Label("Extra Variables (YAML or JSON)", classes="field-label")
                    default_ev = self._default("extra_vars", "")
                    if isinstance(default_ev, dict):
                        import yaml

                        default_ev = yaml.safe_dump(default_ev, sort_keys=False)
                    yield TextArea(text=str(default_ev or ""), id="prompt-extra-vars")

                # Survey section
                if self.survey_spec:
                    yield Static(self.survey_title, classes="section-header")
                    if self.survey_description:
                        yield Static(self.survey_description, classes="field-help")

                    for idx, question in enumerate(self.survey_spec):
                        var_name = question.get("variable", "")
                        if not var_name:
                            continue
                        q_name = question.get("question_name") or var_name
                        q_desc = question.get("question_description") or ""
                        q_type = (question.get("type") or "text").lower()
                        required = bool(question.get("required", False))
                        default_val = question.get("default")
                        widget_id = f"survey-q-{idx}"
                        self._survey_widget_map[var_name] = (widget_id, q_type)

                        label_text = f"{q_name} *" if required else q_name
                        yield Label(label_text, classes="field-label")
                        if q_desc:
                            yield Static(q_desc, classes="field-help")

                        if q_type == "multiplechoice":
                            choices = parse_survey_choices(question.get("choices"))
                            options = [(c, c) for c in choices]
                            initial = (
                                str(default_val)
                                if default_val is not None and str(default_val) in choices
                                else _SELECT_EMPTY
                            )
                            yield Select(
                                options,
                                prompt="Select an option...",
                                value=initial,
                                allow_blank=not required,
                                id=widget_id,
                            )
                        elif q_type == "multiselect":
                            choices = parse_survey_choices(question.get("choices"))
                            default_selected = set(parse_survey_choices(default_val))
                            selections = [Selection(c, c, c in default_selected) for c in choices]
                            yield SelectionList(*selections, id=widget_id, classes="survey-multiselect")
                        elif q_type == "textarea":
                            yield TextArea(text=str(default_val or ""), id=widget_id, classes="survey-textarea")
                        elif q_type == "password":
                            yield Input(
                                value=str(default_val or ""),
                                password=True,
                                placeholder="Enter password...",
                                id=widget_id,
                            )
                        else:
                            # text, integer, float
                            placeholder = f"Enter {q_type}..."
                            yield Input(
                                value="" if default_val is None else str(default_val),
                                placeholder=placeholder,
                                id=widget_id,
                            )

            yield Static("", id="launch-prompt-errors")

            with Horizontal(id="launch-prompt-buttons"):
                yield Button("Launch", variant="primary", id="launch-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def _collect_and_validate(self) -> tuple[Dict[str, Any], List[str]]:
        """Read all rendered widgets and build/validate the launch payload."""
        prompt_values: Dict[str, Any] = {}
        raw_extra_vars = ""

        if self._flag("ask_inventory_on_launch"):
            inv_val = self.query_one("#prompt-inventory", Select).value
            if inv_val != _SELECT_EMPTY:
                prompt_values["inventory"] = inv_val

        for flag_name, widget_id, payload_key in (
            ("ask_limit_on_launch", "#prompt-limit", "limit"),
            ("ask_scm_branch_on_launch", "#prompt-scm-branch", "scm_branch"),
            ("ask_tags_on_launch", "#prompt-job-tags", "job_tags"),
            ("ask_skip_tags_on_launch", "#prompt-skip-tags", "skip_tags"),
        ):
            if self._flag(flag_name):
                prompt_values[payload_key] = self.query_one(widget_id, Input).value

        is_workflow = self.template_data.get("type") == "workflow_job_template"
        if not is_workflow:
            if self._flag("ask_job_type_on_launch"):
                jt_val = self.query_one("#prompt-job-type", Select).value
                if jt_val != _SELECT_EMPTY:
                    prompt_values["job_type"] = jt_val
            if self._flag("ask_verbosity_on_launch"):
                v_val = self.query_one("#prompt-verbosity", Select).value
                if v_val != _SELECT_EMPTY:
                    prompt_values["verbosity"] = v_val
            if self._flag("ask_diff_mode_on_launch"):
                prompt_values["diff_mode"] = self.query_one("#prompt-diff-mode", Switch).value
            if self._flag("ask_forks_on_launch"):
                prompt_values["forks"] = self.query_one("#prompt-forks", Input).value

        if self._flag("ask_variables_on_launch"):
            raw_extra_vars = self.query_one("#prompt-extra-vars", TextArea).text

        survey_values: Dict[str, Any] = {}
        for var_name, (widget_id, q_type) in self._survey_widget_map.items():
            if q_type == "multiplechoice":
                sel_val = self.query_one(f"#{widget_id}", Select).value
                survey_values[var_name] = "" if sel_val == _SELECT_EMPTY else sel_val
            elif q_type == "multiselect":
                survey_values[var_name] = list(self.query_one(f"#{widget_id}", SelectionList).selected)
            elif q_type == "textarea":
                survey_values[var_name] = self.query_one(f"#{widget_id}", TextArea).text
            else:
                survey_values[var_name] = self.query_one(f"#{widget_id}", Input).value

        return build_launch_payload(
            prompt_values=prompt_values,
            survey_spec=self.survey_spec,
            survey_values=survey_values,
            raw_extra_vars=raw_extra_vars,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)
            return

        if event.button.id == "launch-button":
            payload, errors = self._collect_and_validate()
            error_widget = self.query_one("#launch-prompt-errors", Static)
            if errors:
                error_widget.update("\n".join(f"• {err}" for err in errors))
                error_widget.add_class("visible")
                return

            error_widget.remove_class("visible")
            self.dismiss(payload)

    def action_cancel(self) -> None:
        """Cancel the launch (ESC key)"""
        self.dismiss(None)
