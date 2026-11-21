"""
Tests for prompt-on-launch & survey utilities, modal, and mock endpoints.
"""

import asyncio

from awx_tui.mock_data import MockAWXClient
from awx_tui.modals.launch_prompt import LaunchPromptModal
from awx_tui.utils.launch_prompts import (
    build_launch_payload,
    get_active_prompt_fields,
    parse_survey_choices,
)


def test_get_active_prompt_fields_workflow_vs_job():
    wf = {
        "type": "workflow_job_template",
        "ask_inventory_on_launch": True,
        "ask_limit_on_launch": True,
        "ask_forks_on_launch": True,  # ignored for workflows
        "survey_enabled": True,
    }
    wf_prompts = get_active_prompt_fields(wf)
    assert set(wf_prompts) == {"ask_inventory_on_launch", "ask_limit_on_launch", "survey_enabled"}

    jt = {
        "type": "job_template",
        "ask_forks_on_launch": True,
        "ask_diff_mode_on_launch": True,
        "survey_enabled": False,
    }
    jt_prompts = get_active_prompt_fields(jt)
    assert set(jt_prompts) == {"ask_forks_on_launch", "ask_diff_mode_on_launch"}


def test_parse_survey_choices():
    assert parse_survey_choices("dev\nstaging\n\nprod") == ["dev", "staging", "prod"]
    assert parse_survey_choices(["a", "b"]) == ["a", "b"]
    assert parse_survey_choices("") == []
    assert parse_survey_choices(None) == []


def test_build_launch_payload_valid_with_survey_and_extra_vars():
    survey_spec = [
        {"variable": "target_env", "question_name": "Env", "type": "multiplechoice", "required": True},
        {"variable": "retries", "question_name": "Retries", "type": "integer", "required": True, "min": 0, "max": 5},
        {"variable": "ratio", "question_name": "Ratio", "type": "float", "required": False},
        {"variable": "regions", "question_name": "Regions", "type": "multiselect", "required": True},
    ]
    payload, errors = build_launch_payload(
        prompt_values={
            "inventory": 3,
            "limit": "webservers",
            "scm_branch": "release/1.0",
            "job_tags": "deploy",
            "verbosity": 2,
            "diff_mode": True,
            "forks": "10",
        },
        survey_spec=survey_spec,
        survey_values={
            "target_env": "prod",
            "retries": "3",
            "ratio": "0.5",
            "regions": ["us-east", "eu-west"],
        },
        raw_extra_vars="app_version: 2.1.0\ntarget_env: dev\n",
    )

    assert errors == []
    assert payload["inventory"] == 3
    assert payload["limit"] == "webservers"
    assert payload["scm_branch"] == "release/1.0"
    assert payload["job_tags"] == "deploy"
    assert payload["verbosity"] == 2
    assert payload["diff_mode"] is True
    assert payload["forks"] == 10
    # Survey answer overrides matching extra_vars key while preserving others
    assert payload["extra_vars"] == {
        "app_version": "2.1.0",
        "target_env": "prod",
        "retries": 3,
        "ratio": 0.5,
        "regions": ["us-east", "eu-west"],
    }


def test_build_launch_payload_validation_errors():
    survey_spec = [
        {"variable": "ticket", "question_name": "Ticket", "type": "text", "required": True},
        {"variable": "retries", "question_name": "Retries", "type": "integer", "required": True, "min": 1, "max": 5},
        {"variable": "regions", "question_name": "Regions", "type": "multiselect", "required": True},
    ]
    _, errors = build_launch_payload(
        prompt_values={"forks": "-2"},
        survey_spec=survey_spec,
        survey_values={"ticket": "", "retries": "9", "regions": []},
        raw_extra_vars="- not_a_mapping",
    )
    assert len(errors) == 5
    assert any("Forks" in e for e in errors)
    assert any("Extra variables" in e for e in errors)
    assert any("Ticket" in e for e in errors)
    assert any("Retries" in e for e in errors)
    assert any("Regions" in e for e in errors)


def test_mock_client_launch_info_and_survey_spec():
    client = MockAWXClient(instance_name="mock-dev")

    launch_info = asyncio.run(client.get("/api/v2/workflow_job_templates/102/launch/"))
    assert launch_info["ask_inventory_on_launch"] is True
    assert launch_info["ask_variables_on_launch"] is True
    assert launch_info["survey_enabled"] is True

    survey_spec = asyncio.run(client.get("/api/v2/workflow_job_templates/102/survey_spec/"))
    assert survey_spec["name"] == "Deployment Survey"
    assert len(survey_spec["spec"]) == 3

    modal = LaunchPromptModal(
        template_data={"id": 102, "type": "workflow_job_template", "name": "Disaster Recovery"},
        launch_info=launch_info,
        survey_spec=survey_spec,
        inventories=[{"id": 1, "name": "Production"}],
    )
    assert modal._flag("survey_enabled") is True
    assert modal._flag("ask_inventory_on_launch") is True


def test_select_workflow_modal_instantiation():
    from awx_tui.modals.select_workflow import SelectWorkflowModal

    workflows = [
        {
            "id": 101,
            "type": "workflow_job_template",
            "name": "Full Deployment Workflow",
            "ask_limit_on_launch": False,
        },
        {
            "id": 102,
            "type": "workflow_job_template",
            "name": "Disaster Recovery",
            "ask_limit_on_launch": True,
            "survey_enabled": True,
        },
    ]
    modal = SelectWorkflowModal(host_name="web-01.prod", inventory_name="Production", workflows=workflows)
    assert modal.host_name == "web-01.prod"
    assert len(modal._filtered_workflows) == 2
