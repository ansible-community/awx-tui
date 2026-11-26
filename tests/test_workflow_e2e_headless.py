"""
Headless Textual end-to-end regression tests for workflow UI flows using MockAWXClient.
"""

import asyncio

from textual.app import App
from textual.widgets import Button, DataTable, Input, Static

from awx_tui.config import AppConfig
from awx_tui.mock_data import MockAWXClient
from awx_tui.modals.job_detail import JobDetailModal
from awx_tui.modals.launch_prompt import LaunchPromptModal
from awx_tui.modals.pending_approvals import PendingApprovalsModal
from awx_tui.modals.select_workflow import SelectWorkflowModal
from awx_tui.modals.workflow_structure import WorkflowStructureModal


class _MockInstanceManager:
    def __init__(self, instance_name: str = "mock-dev"):
        self.current_instance = instance_name
        self._client = MockAWXClient(instance_name=instance_name)

    def get_current_client(self):
        return self._client


class _WorkflowTestApp(App):
    def __init__(self, instance_name: str = "mock-dev"):
        super().__init__()
        self.instance_manager = _MockInstanceManager(instance_name=instance_name)
        self.app_config = AppConfig()


async def _wait_until(pilot, predicate, timeout_steps: int = 30, step: float = 0.1) -> bool:
    """Poll until predicate() is truthy or timeout_steps elapse."""
    for _ in range(timeout_steps):
        if predicate():
            return True
        await pilot.pause(step)
    return bool(predicate())


def test_e2e_workflow_structure_preview_and_launch_button():
    """Verify WorkflowStructureModal loads 5 nodes and Launch button dismisses with 'launch'."""

    async def _run():
        app = _WorkflowTestApp()
        dismissed = []
        async with app.run_test(size=(140, 40)) as pilot:
            modal = WorkflowStructureModal(
                {
                    "id": 102,
                    "type": "workflow_job_template",
                    "name": "Disaster Recovery",
                    "description": "DR workflow",
                    "ask_inventory_on_launch": True,
                    "survey_enabled": True,
                    "summary_fields": {"organization": {"name": "Operations"}},
                }
            )
            app.push_screen(modal, callback=dismissed.append)
            await pilot.pause()
            table = modal.query_one("#workflow-structure-table", DataTable)
            assert await _wait_until(pilot, lambda: table.row_count == 5)

            modal.query_one("#launch-wf-button", Button).press()
            assert await _wait_until(pilot, lambda: dismissed == ["launch"])

    asyncio.run(_run())


def test_e2e_launch_prompt_validation_and_submit():
    """Verify LaunchPromptModal blocks invalid required survey input, then submits valid payload."""

    async def _run():
        app = _WorkflowTestApp()
        dismissed = []
        async with app.run_test(size=(140, 40)) as pilot:
            modal = LaunchPromptModal(
                template_data={
                    "id": 102,
                    "type": "workflow_job_template",
                    "name": "Disaster Recovery",
                    "ask_inventory_on_launch": True,
                    "ask_limit_on_launch": True,
                    "ask_variables_on_launch": True,
                    "survey_enabled": True,
                },
                launch_info={"defaults": {"inventory": None, "limit": "web-01.example.com", "extra_vars": "env: dr\n"}},
                survey_spec={
                    "name": "Deployment Survey",
                    "spec": [
                        {
                            "question_name": "Change Ticket",
                            "variable": "change_ticket",
                            "type": "text",
                            "required": True,
                            "default": "",
                        }
                    ],
                },
                inventories=[{"id": 1, "name": "Production Servers"}],
            )
            app.push_screen(modal, callback=dismissed.append)
            await pilot.pause(0.1)

            # Submit with empty required survey field -> should show validation error and stay open
            modal.query_one("#launch-button", Button).press()
            errors_widget = modal.query_one("#launch-prompt-errors", Static)
            assert await _wait_until(pilot, lambda: errors_widget.has_class("visible"))
            assert dismissed == []

            # Fill required survey field -> should dismiss with merged payload
            modal.query_one("#survey-q-0", Input).value = "CHG999"
            await pilot.pause(0.05)
            modal.query_one("#launch-button", Button).press()
            assert await _wait_until(pilot, lambda: len(dismissed) == 1)
            assert dismissed[0]["limit"] == "web-01.example.com"
            assert dismissed[0]["extra_vars"] == {"env": "dr", "change_ticket": "CHG999"}

    asyncio.run(_run())


def test_e2e_select_workflow_modal_filter_and_select():
    """Verify SelectWorkflowModal filters by name and returns the selected workflow template."""

    async def _run():
        app = _WorkflowTestApp()
        dismissed = []
        workflows = [
            {"id": 101, "type": "workflow_job_template", "name": "Full Deployment Workflow"},
            {"id": 102, "type": "workflow_job_template", "name": "Disaster Recovery", "ask_limit_on_launch": True},
        ]
        async with app.run_test(size=(140, 40)) as pilot:
            modal = SelectWorkflowModal(
                host_name="prod-01.example.com",
                inventory_name="Production Servers",
                workflows=workflows,
            )
            app.push_screen(modal, callback=dismissed.append)
            await pilot.pause()
            table = modal.query_one("#select-wf-table", DataTable)
            assert await _wait_until(pilot, lambda: table.row_count == 2)

            modal.query_one("#select-wf-filter", Input).value = "Disaster"
            assert await _wait_until(pilot, lambda: table.row_count == 1)

            modal.query_one("#select-button", Button).press()
            assert await _wait_until(pilot, lambda: len(dismissed) == 1)
            assert dismissed[0]["id"] == 102

    asyncio.run(_run())


def test_e2e_workflow_job_detail_progress_view():
    """Verify JobDetailModal loads workflow nodes and displays live progress table."""

    async def _run():
        app = _WorkflowTestApp()
        client = app.instance_manager.get_current_client()
        launched = await client.post("/api/v2/workflow_job_templates/101/launch/", data={})
        wf_id = launched["id"]

        async with app.run_test(size=(140, 40)) as pilot:
            modal = JobDetailModal(job_id=wf_id, job_type="workflow_job")
            app.push_screen(modal)
            await pilot.pause()

            table = modal.query_one("#workflow-nodes-table", DataTable)
            assert await _wait_until(pilot, lambda: table.row_count == 5)
            assert len(modal._workflow_nodes) == 5

            modal.action_close()
            await pilot.pause(0.05)

    asyncio.run(_run())


def test_e2e_pending_approvals_review_and_approve():
    """Verify PendingApprovalsModal lists 2 pending approvals and approving decrements to 1."""

    async def _run():
        app = _WorkflowTestApp(instance_name="mock-prod")
        app.instance_manager.get_current_client().mock_data.pop("workflow_approvals", None)

        async with app.run_test(size=(140, 40)) as pilot:
            modal = PendingApprovalsModal()
            app.push_screen(modal)
            await pilot.pause()

            table = modal.query_one("#pending-approvals-table", DataTable)
            assert await _wait_until(pilot, lambda: table.row_count == 2)

            # Press Review -> opens ConfirmApprovalModal -> press Approve
            modal.query_one("#review-button", Button).press()
            assert await _wait_until(pilot, lambda: len(app.screen.query("#approve-button")) == 1)
            app.screen.query_one("#approve-button", Button).press()

            assert await _wait_until(pilot, lambda: table.row_count == 1)
            assert modal._modified is True

    asyncio.run(_run())
