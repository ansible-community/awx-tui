"""
Headless Textual E2E regression tests for Job Template preview, host-level template launch,
job-specific prompt-on-launch fields, and Textual 8 Select.NULL handling.
"""

import asyncio
import json

from textual.app import App
from textual.widgets import DataTable, Input, Select

from awx_tui.config import AppConfig
from awx_tui.mock_data import MockAWXClient
from awx_tui.modals.job_template_preview import JobTemplatePreviewModal
from awx_tui.modals.launch_prompt import LaunchPromptModal
from awx_tui.modals.select_workflow import SelectWorkflowModal
from awx_tui.screens.update_job_template import _SELECT_EMPTY


class _MockInstanceManager:
    def __init__(self, instance_name: str = "mock-dev"):
        self.current_instance = instance_name
        self._client = MockAWXClient(instance_name=instance_name)

    def get_current_client(self):
        return self._client


class _JobTemplateTestApp(App):
    def __init__(self):
        super().__init__()
        self.instance_manager = _MockInstanceManager()
        self.app_config = AppConfig()


def test_e2e_job_template_preview_modal_and_launch():
    """Verify JobTemplatePreviewModal renders metadata/prompts and Launch button dismisses with 'launch'."""

    async def _run():
        app = _JobTemplateTestApp()
        dismissed = []
        template = {
            "id": 7,
            "type": "job_template",
            "name": "Deploy Web App",
            "description": "Deploys web tier",
            "job_type": "run",
            "playbook": "deploy.yml",
            "ask_limit_on_launch": True,
            "survey_enabled": True,
            "summary_fields": {
                "organization": {"name": "Engineering"},
                "project": {"name": "Web Playbooks"},
                "inventory": {"name": "Production"},
            },
        }
        async with app.run_test(size=(140, 40)) as pilot:
            modal = JobTemplatePreviewModal(template)
            preview_text = modal._format_preview()
            assert "Deploy Web App" in preview_text
            assert "deploy.yml" in preview_text
            assert "limit" in preview_text
            assert "survey" in preview_text

            app.push_screen(modal, callback=dismissed.append)
            await pilot.pause(0.1)
            await pilot.click("#launch-jt-button")
            await pilot.pause(0.1)
            assert dismissed == ["launch"]

    asyncio.run(_run())


def test_e2e_select_template_modal_mixed_job_and_workflow():
    """Verify SelectWorkflowModal lists both job_template and workflow_job_template and selects a job template."""

    async def _run():
        app = _JobTemplateTestApp()
        dismissed = []
        templates = [
            {"id": 10, "type": "job_template", "name": "Patch Linux Host", "ask_limit_on_launch": True},
            {"id": 102, "type": "workflow_job_template", "name": "Disaster Recovery", "ask_limit_on_launch": True},
        ]
        async with app.run_test(size=(140, 40)) as pilot:
            modal = SelectWorkflowModal(
                host_name="web-01.example.com",
                inventory_name="Production Servers",
                workflows=templates,
            )
            app.push_screen(modal, callback=dismissed.append)
            await pilot.pause(0.1)

            table = modal.query_one("#select-wf-table", DataTable)
            assert table.row_count == 2

            modal.query_one("#select-wf-filter", Input).value = "Patch"
            await pilot.pause(0.1)
            assert table.row_count == 1

            await pilot.click("#select-button")
            await pilot.pause(0.1)
            assert len(dismissed) == 1
            assert dismissed[0]["type"] == "job_template"
            assert dismissed[0]["id"] == 10

    asyncio.run(_run())


def test_e2e_job_template_launch_prompt_with_job_only_fields():
    """Verify LaunchPromptModal handles job_template-only fields (job_type, verbosity, diff_mode, forks)."""

    async def _run():
        app = _JobTemplateTestApp()
        dismissed = []
        async with app.run_test(size=(140, 40)) as pilot:
            modal = LaunchPromptModal(
                template_data={
                    "id": 10,
                    "type": "job_template",
                    "name": "Patch Linux Host",
                    "ask_limit_on_launch": True,
                    "ask_job_type_on_launch": True,
                    "ask_verbosity_on_launch": True,
                    "ask_diff_mode_on_launch": True,
                    "ask_forks_on_launch": True,
                },
                launch_info={
                    "defaults": {
                        "limit": "web-01.example.com",
                        "job_type": "check",
                        "verbosity": 2,
                        "diff_mode": True,
                        "forks": 10,
                    }
                },
            )
            app.push_screen(modal, callback=dismissed.append)
            await pilot.pause(0.2)

            await pilot.click("#launch-button")
            await pilot.pause(0.1)
            assert len(dismissed) == 1
            payload = dismissed[0]
            assert payload["limit"] == "web-01.example.com"
            assert payload["job_type"] == "check"
            assert payload["verbosity"] == 2
            assert payload["diff_mode"] is True
            assert payload["forks"] == 10
            # Confirm payload is cleanly JSON-serializable
            json.dumps(payload)

    asyncio.run(_run())


def test_update_job_template_select_null_sentinel():
    """Verify _SELECT_EMPTY matches Textual 8 Select.NULL so NoSelection is never serialized."""
    assert _SELECT_EMPTY == getattr(Select, "NULL", Select.BLANK)
    val = getattr(Select, "NULL", Select.BLANK)
    normalized = None if val == _SELECT_EMPTY else val
    assert normalized is None
    assert json.dumps({"execution_environment": normalized}) == '{"execution_environment": null}'
