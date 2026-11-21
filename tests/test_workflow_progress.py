"""
Tests for workflow job progress ordering, summarization, and mock endpoints.
"""

import asyncio

from awx_tui.mock_data import MockAWXClient
from awx_tui.utils.workflow import (
    format_workflow_progress_bar,
    order_workflow_nodes,
    summarize_workflow_progress,
)


def test_order_workflow_nodes_empty():
    assert order_workflow_nodes([]) == []


def test_order_workflow_nodes_linear_and_branching():
    nodes = [
        {
            "id": 3,
            "job": None,
            "do_not_run": False,
            "success_nodes": [],
            "failure_nodes": [],
            "always_nodes": [],
            "summary_fields": {
                "unified_job_template": {"name": "Notify", "unified_job_type": "job"},
            },
        },
        {
            "id": 1,
            "job": 501,
            "do_not_run": False,
            "success_nodes": [2],
            "failure_nodes": [3],
            "always_nodes": [],
            "summary_fields": {
                "unified_job_template": {"name": "Build", "unified_job_type": "job"},
                "job": {"id": 501, "name": "Build", "type": "job", "status": "successful", "elapsed": 12.0},
            },
        },
        {
            "id": 2,
            "job": 502,
            "do_not_run": False,
            "success_nodes": [3],
            "failure_nodes": [],
            "always_nodes": [],
            "summary_fields": {
                "unified_job_template": {"name": "Deploy", "unified_job_type": "job"},
                "job": {"id": 502, "name": "Deploy", "type": "job", "status": "running", "elapsed": 5.5},
            },
        },
    ]

    ordered = order_workflow_nodes(nodes)
    assert [n["node_id"] for n in ordered] == [1, 2, 3]
    assert ordered[0]["branch"] == "start"
    assert ordered[0]["status"] == "successful"
    assert ordered[1]["branch"] == "on success"
    assert ordered[1]["status"] == "running"
    # Node 3 is a convergence node (referenced by node 1 on failure and node 2 on success)
    assert "converge" in ordered[2]["branch"]
    assert ordered[2]["status"] == "not_run"


def test_order_workflow_nodes_skipped_and_approval():
    nodes = [
        {
            "id": 10,
            "job": 601,
            "do_not_run": False,
            "success_nodes": [11],
            "failure_nodes": [12],
            "always_nodes": [],
            "summary_fields": {
                "unified_job_template": {"name": "Approval Gate", "unified_job_type": "workflow_approval"},
                "job": {"id": 601, "type": "workflow_approval", "status": "pending", "elapsed": 0.0},
            },
        },
        {
            "id": 11,
            "job": None,
            "do_not_run": False,
            "success_nodes": [],
            "failure_nodes": [],
            "always_nodes": [],
            "summary_fields": {
                "unified_job_template": {"name": "Prod Release", "unified_job_type": "job"},
            },
        },
        {
            "id": 12,
            "job": None,
            "do_not_run": True,
            "success_nodes": [],
            "failure_nodes": [],
            "always_nodes": [],
            "summary_fields": {
                "unified_job_template": {"name": "Rollback", "unified_job_type": "job"},
            },
        },
    ]

    ordered = order_workflow_nodes(nodes)
    assert ordered[0]["status"] == "waiting_approval"
    assert ordered[1]["status"] == "not_run"
    assert ordered[2]["status"] == "skipped"


def test_summarize_and_format_workflow_progress():
    ordered = [
        {"status": "successful"},
        {"status": "running"},
        {"status": "failed"},
        {"status": "skipped"},
        {"status": "not_run"},
    ]
    summary = summarize_workflow_progress(ordered)
    assert summary["total"] == 5
    assert summary["completed"] == 1
    assert summary["running"] == 1
    assert summary["failed"] == 1
    assert summary["skipped"] == 1
    assert summary["pending"] == 1
    # 3 of 5 finished (completed + failed + skipped) => 60%
    assert summary["percent"] == 60

    bar = format_workflow_progress_bar(summary)
    assert "60%" in bar
    assert "1/5 ✓" in bar
    assert "1 running" in bar
    assert "1 failed" in bar
    assert "1 pending" in bar
    assert "1 skipped" in bar


def test_mock_client_workflow_endpoints():
    client = MockAWXClient(instance_name="mock-dev")
    wf_detail = asyncio.run(client.get("/api/v2/workflow_jobs/999/"))
    assert wf_detail["id"] == 999
    assert wf_detail["type"] == "workflow_job"

    nodes_resp = asyncio.run(client.get("/api/v2/workflow_jobs/999/workflow_nodes/"))
    assert nodes_resp["count"] == 5
    ordered = order_workflow_nodes(nodes_resp["results"])
    assert len(ordered) == 5
    summary = summarize_workflow_progress(ordered)
    assert summary["total"] == 5
    assert summary["completed"] == 1
    assert summary["running"] == 1


def test_mock_client_workflow_actions():
    client = MockAWXClient(instance_name="mock-dev")

    launched = asyncio.run(client.post("/api/v2/workflow_job_templates/10/launch/", data={}))
    assert launched["type"] == "workflow_job"
    assert launched["status"] == "running"

    relaunched = asyncio.run(client.post(f"/api/v2/workflow_jobs/{launched['id']}/relaunch/", data={"hosts": "failed"}))
    assert relaunched["type"] == "workflow_job"
    assert relaunched["launch_type"] == "relaunch"
    assert relaunched["id"] != launched["id"]

    approved = asyncio.run(client.post("/api/v2/workflow_approvals/42/approve/", data={}))
    assert approved["status"] == "approved"

    denied = asyncio.run(client.post("/api/v2/workflow_approvals/43/deny/", data={}))
    assert denied["status"] == "denied"

    # Canceling a workflow job updates its running mock node to canceled
    asyncio.run(client.post(f"/api/v2/workflow_jobs/{launched['id']}/cancel/", data={}))
    canceled_nodes = asyncio.run(client.get(f"/api/v2/workflow_jobs/{launched['id']}/workflow_nodes/"))["results"]
    deploy_node = next(n for n in canceled_nodes if n["id"] == 102)
    assert deploy_node["summary_fields"]["job"]["status"] == "canceled"


def test_workflow_modal_formatting():
    from awx_tui.modals.confirm_approval import ConfirmApprovalModal
    from awx_tui.modals.confirm_cancel import ConfirmCancelModal
    from awx_tui.modals.confirm_launch import ConfirmLaunchModal
    from awx_tui.modals.confirm_relaunch import ConfirmRelaunchModal

    wf_template = {
        "id": 10,
        "type": "workflow_job_template",
        "name": "Deploy Pipeline",
        "description": "End-to-end deploy workflow",
        "summary_fields": {"organization": {"name": "Default"}},
    }
    launch_modal = ConfirmLaunchModal(wf_template)
    launch_info = launch_modal._format_template_info()
    assert "Workflow Template: Deploy Pipeline" in launch_info
    assert "Playbook:" not in launch_info

    wf_job = {
        "id": 500,
        "type": "workflow_job",
        "name": "Deploy Pipeline",
        "status": "failed",
        "summary_fields": {
            "organization": {"name": "Default"},
            "created_by": {"username": "admin"},
            "workflow_job_template": {"name": "Deploy Pipeline"},
        },
    }
    relaunch_modal = ConfirmRelaunchModal(wf_job)
    relaunch_info = relaunch_modal._format_job_info()
    assert "Workflow Job ID: #500" in relaunch_info
    assert "Workflow Template: Deploy Pipeline" in relaunch_info

    cancel_modal = ConfirmCancelModal(wf_job)
    cancel_info = cancel_modal._format_job_info()
    assert "Workflow Job #500: Deploy Pipeline" in cancel_info
    assert "Template: Deploy Pipeline" in cancel_info

    approval_modal = ConfirmApprovalModal(
        {
            "name": "Prod Gate",
            "job_id": 77,
            "branch": "on success",
            "node": {"summary_fields": {"job": {"description": "Approve prod rollout"}}},
        }
    )
    approval_info = approval_modal._format_approval_info()
    assert "Approval Node: Prod Gate" in approval_info
    assert "Approval ID: #77" in approval_info
    assert "Approve prod rollout" in approval_info


def test_workflow_structure_preview_and_transitions():
    from awx_tui.modals.workflow_structure import WorkflowStructureModal
    from awx_tui.utils.workflow import format_node_transitions

    client = MockAWXClient(instance_name="mock-dev")
    nodes_resp = asyncio.run(client.get("/api/v2/workflow_job_templates/102/workflow_nodes/"))
    assert nodes_resp["count"] == 5

    ordered = order_workflow_nodes(nodes_resp["results"])
    assert [n["name"] for n in ordered] == [
        "Verify Backups",
        "DR Failover Approval",
        "Notify Incident Channel",
        "Promote Standby DB",
        "Switch DNS Traffic",
    ]
    id_to_step = {e["node_id"]: e["step"] for e in ordered}
    first_transitions = format_node_transitions(ordered[0], id_to_step)
    assert "#2" in first_transitions
    assert "#3" in first_transitions
    terminal_transitions = format_node_transitions(ordered[2], id_to_step)
    assert "—" in terminal_transitions

    modal = WorkflowStructureModal(
        {
            "id": 102,
            "type": "workflow_job_template",
            "name": "Disaster Recovery",
            "description": "DR failover pipeline",
            "ask_inventory_on_launch": True,
            "survey_enabled": True,
            "summary_fields": {"organization": {"name": "Operations"}},
        }
    )
    header = modal._format_header(node_count=5)
    assert "Disaster Recovery" in header
    assert "Nodes: 5" in header
    assert "inventory" in header
    assert "survey" in header


def test_pending_approvals_quick_view_and_mock_lifecycle():
    """Test pending workflow approvals mock listing, approve/deny state transition, and entry mapping."""
    from awx_tui.modals.pending_approvals import PendingApprovalsModal, build_approval_node_entry

    client = MockAWXClient(instance_name="mock-staging")
    client.mock_data.pop("workflow_approvals", None)

    pending = asyncio.run(client.get("/api/v2/workflow_approvals/", params={"status": "pending"}))
    assert pending["count"] == 2
    first = pending["results"][0]

    entry = build_approval_node_entry(first)
    assert entry["job_id"] == first["id"]
    assert entry["name"] == first["name"]
    assert "Workflow #" in entry["branch"]

    # Approve first, deny second -> 0 pending left
    asyncio.run(client.post(f"/api/v2/workflow_approvals/{first['id']}/approve/", data={}))
    after_one = asyncio.run(client.get("/api/v2/workflow_approvals/", params={"status": "pending"}))
    assert after_one["count"] == 1

    second = after_one["results"][0]
    asyncio.run(client.post(f"/api/v2/workflow_approvals/{second['id']}/deny/", data={}))
    after_two = asyncio.run(client.get("/api/v2/workflow_approvals/", params={"status": "pending"}))
    assert after_two["count"] == 0

    modal = PendingApprovalsModal()
    assert modal._modified is False
