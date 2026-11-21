"""
AWX TUI - Workflow Utilities

Helpers for ordering workflow job nodes and summarizing workflow progress.
"""

from collections import deque
from typing import Any, Dict, List, Optional, Tuple


# Statuses considered terminal/finished for progress calculation
_COMPLETED_STATUSES = {"successful"}
_FAILED_STATUSES = {"failed", "error", "canceled"}
_RUNNING_STATUSES = {"running"}
_SKIPPED_STATUSES = {"skipped"}


def _resolve_node_status(node: Dict[str, Any], node_type: str) -> str:
    """Resolve a normalized display status for a workflow job node."""
    if node.get("do_not_run", False):
        return "skipped"

    summary = node.get("summary_fields", {})
    job_info = summary.get("job") or {}
    raw_status = (job_info.get("status") or "").lower()

    if not raw_status:
        return "not_run"

    if node_type == "workflow_approval" and raw_status in ("pending", "waiting"):
        return "waiting_approval"

    return raw_status


def _resolve_node_type(node: Dict[str, Any]) -> str:
    """Resolve the unified job type for a workflow job node."""
    summary = node.get("summary_fields", {})
    job_info = summary.get("job") or {}
    if job_info.get("type"):
        return job_info["type"]

    ujt = summary.get("unified_job_template") or {}
    ujt_type = ujt.get("unified_job_type") or ""
    type_map = {
        "job": "job",
        "project_update": "project_update",
        "inventory_update": "inventory_update",
        "workflow_job": "workflow_job",
        "workflow_approval": "workflow_approval",
        "system_job": "system_job",
    }
    return type_map.get(ujt_type, "job")


def _resolve_node_name(node: Dict[str, Any]) -> str:
    """Resolve a human-readable name for a workflow job node."""
    summary = node.get("summary_fields", {})
    ujt = summary.get("unified_job_template") or {}
    if ujt.get("name"):
        return ujt["name"]

    job_info = summary.get("job") or {}
    if job_info.get("name"):
        return job_info["name"]

    return f"Node #{node.get('id', '?')}"


def order_workflow_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Order workflow job nodes topologically from root nodes, deduplicating convergence nodes.

    Args:
        nodes: Raw list of workflow_job_node dicts from `/api/v2/workflow_jobs/{id}/workflow_nodes/`

    Returns:
        List of normalized node entry dicts in execution order.
    """
    if not nodes:
        return []

    node_map: Dict[int, Dict[str, Any]] = {}
    incoming: Dict[int, List[Tuple[int, str]]] = {}

    for node in nodes:
        node_id = node.get("id")
        if node_id is None:
            continue
        node_map[node_id] = node
        incoming.setdefault(node_id, [])

    # Build incoming edge map
    for node_id, node in node_map.items():
        for branch_key, label in (
            ("success_nodes", "on success"),
            ("failure_nodes", "on failure"),
            ("always_nodes", "always"),
        ):
            for child_id in node.get(branch_key) or []:
                if child_id in node_map:
                    incoming[child_id].append((node_id, label))

    # Roots are nodes with no incoming edges; fallback to lowest ID if cyclic
    roots = sorted([nid for nid, parents in incoming.items() if not parents])
    if not roots:
        roots = [min(node_map.keys())]

    visited: set[int] = set()
    ordered_ids: List[Tuple[int, int]] = []  # (node_id, depth)
    queue: deque[Tuple[int, int]] = deque((rid, 0) for rid in roots)

    while queue:
        current_id, depth = queue.popleft()
        if current_id in visited:
            continue
        visited.add(current_id)
        ordered_ids.append((current_id, depth))

        current_node = node_map[current_id]
        for branch_key in ("success_nodes", "failure_nodes", "always_nodes"):
            for child_id in current_node.get(branch_key) or []:
                if child_id in node_map and child_id not in visited:
                    queue.append((child_id, depth + 1))

    # Append any disconnected nodes not reached from roots
    for nid in sorted(node_map.keys()):
        if nid not in visited:
            ordered_ids.append((nid, 0))

    result: List[Dict[str, Any]] = []
    for step_idx, (nid, depth) in enumerate(ordered_ids, start=1):
        node = node_map[nid]
        parents = incoming.get(nid, [])
        if not parents:
            branch_label = "start"
        else:
            unique_labels = list(dict.fromkeys(label for _, label in parents))
            if len(parents) > 1:
                branch_label = f"converge ({', '.join(unique_labels)})"
            else:
                branch_label = unique_labels[0]

        node_type = _resolve_node_type(node)
        summary = node.get("summary_fields", {})
        job_info = summary.get("job") or {}

        result.append(
            {
                "step": step_idx,
                "node_id": nid,
                "name": _resolve_node_name(node),
                "node_type": node_type,
                "branch": branch_label,
                "depth": depth,
                "job_id": node.get("job"),
                "status": _resolve_node_status(node, node_type),
                "elapsed": job_info.get("elapsed"),
                "node": node,
            }
        )

    return result


def summarize_workflow_progress(ordered_nodes: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Summarize workflow progress counts from ordered node entries.

    Returns:
        Dict with keys: total, completed, failed, running, pending, skipped, percent
    """
    total = len(ordered_nodes)
    completed = 0
    failed = 0
    running = 0
    skipped = 0
    pending = 0

    for entry in ordered_nodes:
        status = entry.get("status", "not_run")
        if status in _COMPLETED_STATUSES:
            completed += 1
        elif status in _FAILED_STATUSES:
            failed += 1
        elif status in _RUNNING_STATUSES:
            running += 1
        elif status in _SKIPPED_STATUSES:
            skipped += 1
        else:
            pending += 1

    done = completed + failed + skipped
    percent = int(round((done / total) * 100)) if total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "pending": pending,
        "skipped": skipped,
        "percent": percent,
    }


def format_workflow_progress_bar(summary: Dict[str, int], width: int = 16) -> str:
    """Format a compact Rich-markup progress bar and node breakdown string."""
    total = summary.get("total", 0)
    if total == 0:
        return "No workflow nodes"

    percent = summary.get("percent", 0)
    filled = int(round((percent / 100) * width))
    empty = max(0, width - filled)
    bar = f"[green]{'█' * filled}[/green][dim]{'░' * empty}[/dim]"

    parts = [f"{summary['completed']}/{total} ✓"]
    if summary.get("running", 0):
        parts.append(f"{summary['running']} running")
    if summary.get("failed", 0):
        parts.append(f"[red]{summary['failed']} failed[/red]")
    if summary.get("pending", 0):
        parts.append(f"{summary['pending']} pending")
    if summary.get("skipped", 0):
        parts.append(f"{summary['skipped']} skipped")

    return f"{bar} {percent}% ({' | '.join(parts)})"


def format_node_transitions(entry: Dict[str, Any], id_to_step: Dict[int, int]) -> str:
    """
    Format outgoing transitions of a workflow node using step numbers.

    Returns a compact string like '✓→#2, ✗→#4' or '—' for terminal nodes.
    """
    raw_node = entry.get("node") or {}
    parts: List[str] = []

    for key, symbol in (
        ("success_nodes", "[green]✓[/green]"),
        ("failure_nodes", "[red]✗[/red]"),
        ("always_nodes", "[cyan]*[/cyan]"),
    ):
        targets = raw_node.get(key) or []
        if targets:
            step_refs = [f"#{id_to_step.get(tid, tid)}" for tid in targets]
            parts.append(f"{symbol}→{','.join(step_refs)}")

    return "  ".join(parts) if parts else "[dim]—[/dim]"
