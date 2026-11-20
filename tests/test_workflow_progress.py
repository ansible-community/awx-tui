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
