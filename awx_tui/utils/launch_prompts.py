"""
AWX TUI - Launch Prompt & Survey Utilities

Helpers for detecting prompt-on-launch requirements, parsing survey specs,
and validating/building the POST payload for job and workflow template launches.
"""

from typing import Any, Dict, List, Tuple

import yaml

WORKFLOW_PROMPT_FIELDS = (
    "ask_variables_on_launch",
    "ask_inventory_on_launch",
    "ask_limit_on_launch",
    "ask_scm_branch_on_launch",
    "ask_labels_on_launch",
    "ask_skip_tags_on_launch",
    "ask_tags_on_launch",
    "survey_enabled",
)

JOB_PROMPT_FIELDS = (
    "ask_variables_on_launch",
    "ask_inventory_on_launch",
    "ask_credential_on_launch",
    "ask_limit_on_launch",
    "ask_tags_on_launch",
    "ask_skip_tags_on_launch",
    "ask_job_type_on_launch",
    "ask_execution_environment_on_launch",
    "ask_labels_on_launch",
    "ask_scm_branch_on_launch",
    "ask_diff_mode_on_launch",
    "ask_verbosity_on_launch",
    "ask_forks_on_launch",
    "survey_enabled",
)


def get_active_prompt_fields(template_data: Dict[str, Any]) -> List[str]:
    """Return the list of prompt-on-launch flags enabled on a template or launch-info dict."""
    template_type = template_data.get("type", "")
    fields = WORKFLOW_PROMPT_FIELDS if template_type == "workflow_job_template" else JOB_PROMPT_FIELDS
    return [field for field in fields if template_data.get(field, False)]


def parse_survey_choices(choices: Any) -> List[str]:
    """Normalize AWX/AAP survey choices (newline-delimited string or list) into a list of strings."""
    if not choices:
        return []
    if isinstance(choices, list):
        return [str(c) for c in choices if str(c).strip()]
    return [line.strip() for line in str(choices).splitlines() if line.strip()]


def build_launch_payload(
    prompt_values: Dict[str, Any],
    survey_spec: List[Dict[str, Any]] | None = None,
    survey_values: Dict[str, Any] | None = None,
    raw_extra_vars: str = "",
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate user inputs and build the POST payload for `/launch/`.

    Args:
        prompt_values: Dict of standard prompted fields (inventory, limit, scm_branch,
            job_tags, skip_tags, job_type, verbosity, diff_mode, forks).
        survey_spec: List of survey question spec dicts.
        survey_values: Map of `variable -> raw value` from survey widgets.
        raw_extra_vars: Raw YAML/JSON string entered in the Extra Variables field.

    Returns:
        Tuple of (payload_dict, error_messages_list).
    """
    payload: Dict[str, Any] = {}
    errors: List[str] = []

    # 1. Standard prompt-on-launch fields
    if "inventory" in prompt_values and prompt_values["inventory"] is not None:
        payload["inventory"] = int(prompt_values["inventory"])

    for str_key in ("limit", "scm_branch", "job_tags", "skip_tags", "job_type"):
        if str_key in prompt_values:
            val = prompt_values[str_key]
            if val is not None and str(val).strip() != "":
                payload[str_key] = str(val).strip()

    if "verbosity" in prompt_values and prompt_values["verbosity"] is not None:
        try:
            payload["verbosity"] = int(prompt_values["verbosity"])
        except (TypeError, ValueError):
            errors.append("Verbosity must be an integer (0-5).")

    if "diff_mode" in prompt_values and prompt_values["diff_mode"] is not None:
        payload["diff_mode"] = bool(prompt_values["diff_mode"])

    if "forks" in prompt_values:
        forks_raw = prompt_values["forks"]
        if forks_raw is not None and str(forks_raw).strip() != "":
            try:
                forks_int = int(str(forks_raw).strip())
                if forks_int < 0:
                    errors.append("Forks must be >= 0.")
                else:
                    payload["forks"] = forks_int
            except ValueError:
                errors.append("Forks must be a valid integer.")

    # 2. Extra variables (YAML or JSON mapping)
    extra_vars: Dict[str, Any] = {}
    if raw_extra_vars and raw_extra_vars.strip():
        try:
            parsed = yaml.safe_load(raw_extra_vars)
            if parsed is None:
                parsed = {}
            if not isinstance(parsed, dict):
                errors.append("Extra variables must be a valid YAML/JSON mapping (key: value).")
            else:
                extra_vars.update(parsed)
        except yaml.YAMLError as exc:
            errors.append(f"Invalid YAML/JSON in Extra Variables: {exc}")

    # 3. Survey questions
    survey_values = survey_values or {}
    for question in survey_spec or []:
        var_name = question.get("variable", "")
        if not var_name:
            continue
        q_label = question.get("question_name") or var_name
        q_type = (question.get("type") or "text").lower()
        required = bool(question.get("required", False))
        raw_val = survey_values.get(var_name)

        if q_type == "multiselect":
            selected = [str(v) for v in (raw_val or []) if str(v).strip()]
            if required and not selected:
                errors.append(f"Survey '{q_label}' is required.")
            elif selected:
                extra_vars[var_name] = selected
            continue

        val_str = "" if raw_val is None else str(raw_val).strip()
        if not val_str:
            if required:
                errors.append(f"Survey '{q_label}' is required.")
            continue

        if q_type == "integer":
            try:
                int_val = int(val_str)
                q_min = question.get("min")
                q_max = question.get("max")
                if q_min is not None and int_val < int(q_min):
                    errors.append(f"Survey '{q_label}' must be >= {q_min}.")
                elif q_max is not None and int_val > int(q_max):
                    errors.append(f"Survey '{q_label}' must be <= {q_max}.")
                else:
                    extra_vars[var_name] = int_val
            except ValueError:
                errors.append(f"Survey '{q_label}' must be an integer.")
        elif q_type == "float":
            try:
                float_val = float(val_str)
                q_min = question.get("min")
                q_max = question.get("max")
                if q_min is not None and float_val < float(q_min):
                    errors.append(f"Survey '{q_label}' must be >= {q_min}.")
                elif q_max is not None and float_val > float(q_max):
                    errors.append(f"Survey '{q_label}' must be <= {q_max}.")
                else:
                    extra_vars[var_name] = float_val
            except ValueError:
                errors.append(f"Survey '{q_label}' must be a number.")
        else:
            extra_vars[var_name] = raw_val if isinstance(raw_val, str) else val_str

    if extra_vars:
        payload["extra_vars"] = extra_vars

    return payload, errors
