"""
AWX TUI - Mock Data

Mock AWX 23.x API responses for development without live AWX instance.

Based on AWX 21.x+ / 23.x API structure.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

# Launch type emojis (from JOB_DETAIL.md)
LAUNCH_TYPES = {
    "manual": "🚀",
    "scheduled": "⚙️",
    "workflow": "🔗",
    "relaunch": "🔄",
    "callback": "📞",
    "dependency": "⛓️",
    "scm": "🔀",
}


def generate_job_data(
    job_id: int,
    name: str,
    status: str,
    launch_type: str = "manual",
    template_name: str = None,
    project_name: str = None,
    inventory_name: str = None,
    exec_env_name: str = None,
    created_by: str = "admin",
    minutes_ago: int = 0,
) -> Dict[str, Any]:
    """
    Generate mock job data

    Args:
        job_id: Job ID
        name: Job name
        status: Job status (successful, failed, running, pending, etc.)
        launch_type: How job was launched
        template_name: Job template name
        project_name: Project name
        inventory_name: Inventory name
        exec_env_name: Execution environment name
        created_by: Username who launched
        minutes_ago: How many minutes ago job was created

    Returns:
        Mock job dict matching AWX API structure
    """
    now = datetime.now()
    created = now - timedelta(minutes=minutes_ago)

    # Defaults
    template_name = template_name or name
    project_name = project_name or "Default Project"
    inventory_name = inventory_name or "Default Inventory"
    exec_env_name = exec_env_name or "ee-29-rhel8"

    # Calculate timestamps based on status
    started = None
    finished = None
    elapsed = 0.0

    if status in ("running", "successful", "failed", "canceled", "error"):
        started = created + timedelta(seconds=random.randint(1, 10))  # NOSONAR

        if status in ("successful", "failed", "canceled", "error"):
            # Completed job
            elapsed = random.randint(30, 600)  # NOSONAR
            finished = started + timedelta(seconds=elapsed)
        else:
            # Running job
            elapsed = (now - started).total_seconds()

    return {
        "id": job_id,
        "type": "job",
        "url": f"/api/v2/jobs/{job_id}/",
        "related": {
            "created_by": f"/api/v2/users/{random.randint(1, 10)}/",  # NOSONAR
            "labels": "/api/v2/jobs/{job_id}/labels/",
            "inventory": f"/api/v2/inventories/{random.randint(1, 20)}/",  # NOSONAR
            "project": f"/api/v2/projects/{random.randint(1, 50)}/",  # NOSONAR
            "credentials": f"/api/v2/jobs/{job_id}/credentials/",
            "unified_job_template": f"/api/v2/job_templates/{random.randint(1, 100)}/",  # NOSONAR
            "stdout": f"/api/v2/jobs/{job_id}/stdout/",
            "execution_environment": f"/api/v2/execution_environments/{random.randint(1, 10)}/",  # NOSONAR
            "job_events": f"/api/v2/jobs/{job_id}/job_events/",
            "job_host_summaries": f"/api/v2/jobs/{job_id}/job_host_summaries/",
            "activity_stream": f"/api/v2/jobs/{job_id}/activity_stream/",
            "notifications": f"/api/v2/jobs/{job_id}/notifications/",
            "job_template": f"/api/v2/job_templates/{random.randint(1, 100)}/",  # NOSONAR
            "cancel": f"/api/v2/jobs/{job_id}/cancel/",
            "relaunch": f"/api/v2/jobs/{job_id}/relaunch/",
        },
        "summary_fields": {
            "organization": {
                "id": random.randint(1, 10),  # NOSONAR
                "name": random.choice(["Engineering", "Operations", "DevOps", "Platform", "QA"]),  # NOSONAR
                "description": "",
            },
            "inventory": {
                "id": random.randint(1, 20),  # NOSONAR
                "name": inventory_name,
                "description": "",
                "has_active_failures": False,
                "total_hosts": random.randint(5, 100),  # NOSONAR
                "hosts_with_active_failures": 0,
                "total_groups": random.randint(2, 20),  # NOSONAR
                "has_inventory_sources": True,
                "total_inventory_sources": random.randint(1, 5),  # NOSONAR
                "inventory_sources_with_failures": 0,
                "organization_id": random.randint(1, 10),  # NOSONAR
                "kind": "",
            },
            "execution_environment": {
                "id": random.randint(1, 10),  # NOSONAR
                "name": exec_env_name,
                "description": "",
                "image": f"quay.io/ansible/{exec_env_name}:latest",
            },
            "project": {
                "id": random.randint(1, 50),  # NOSONAR
                "name": project_name,
                "description": "",
                "status": "successful",
                "scm_type": "git",
            },
            "job_template": {"id": random.randint(1, 100), "name": template_name, "description": ""},  # NOSONAR
            "unified_job_template": {
                "id": random.randint(1, 100),  # NOSONAR
                "name": template_name,
                "description": "",
                "unified_job_type": "job",
            },
            "created_by": {
                "id": random.randint(1, 10),
                "username": created_by,
                "first_name": "",
                "last_name": "",
            },  # NOSONAR
            "user_capabilities": {"delete": True, "start": True},
            "labels": {"count": 0, "results": []},
            "credentials": [],
        },
        "created": created.isoformat() + "Z",
        "modified": (finished or now).isoformat() + "Z",
        "name": name,
        "description": "",
        "job_type": "run",
        "inventory": random.randint(1, 20),  # NOSONAR
        "project": random.randint(1, 50),  # NOSONAR
        "playbook": f'{name.lower().replace(" ", "_")}.yml',
        "scm_branch": "",
        "forks": random.choice([0, 5, 10, 20]),  # NOSONAR
        "limit": "",
        "verbosity": random.choice([0, 1, 2]),  # NOSONAR
        "extra_vars": "{}",
        "job_tags": random.choice(["", "deploy", "deploy,production", "backup", "test"]),  # NOSONAR
        "force_handlers": False,
        "skip_tags": "",
        "start_at_task": "",
        "timeout": 0,
        "use_fact_cache": False,
        "organization": random.randint(1, 10),
        "unified_job_template": random.randint(1, 100),
        "launch_type": launch_type,
        "status": status,
        "execution_environment": random.randint(1, 10),
        "failed": status == "failed",
        "started": started.isoformat() + "Z" if started else None,
        "finished": finished.isoformat() + "Z" if finished else None,
        "canceled_on": None,
        "elapsed": elapsed,
        "job_args": "",
        "job_cwd": "",
        "job_env": {},
        "job_explanation": "",
        "execution_node": random.choice(  # NOSONAR
            [
                "mock-controller-001.local",
                "mock-controller-002.local",
                "mock-aio-001.local",
            ]
        ),
        "controller_node": "",
        "result_traceback": "",
        "event_processing_finished": finished is not None,
        "launched_by": {
            "id": random.randint(1, 10),  # NOSONAR
            "name": created_by,
            "type": "user",
            "url": f"/api/v2/users/{random.randint(1, 10)}/",  # NOSONAR
        },
        "work_unit_id": None,
        "job_template": random.randint(1, 100),  # NOSONAR
        "passwords_needed_to_start": [],
        "allow_simultaneous": False,
        "artifacts": {},
        "scm_revision": "",
        "instance_group": random.randint(1, 5),  # NOSONAR
        "diff_mode": False,
        "job_slice_number": 0,
        "job_slice_count": 1,
        "webhook_service": "",
        "webhook_credential": None,
        "webhook_guid": "",
    }


def generate_job_output(job_id: int, status: str) -> str:
    """Generate mock Ansible job output"""

    if status == "pending":
        return ""

    if status == "waiting":
        return "Job is waiting for approval...\n"

    # Running or completed job
    output_lines = [
        f"Identity added: /tmp/awx_{job_id}/credential (/tmp/awx_{job_id}/credential)",
        "",
        "PLAY [Deploy Application] ******************************************************",
        "",
        "TASK [Gathering Facts] *********************************************************",
        "ok: [web-01]",
        "ok: [web-02]",
        "",
        "TASK [Install packages] ********************************************************",
    ]

    if status == "running":
        output_lines.append("...(output streaming)...")
    else:
        # Completed job
        if status == "failed":
            output_lines.extend(
                [
                    "fatal: [web-01]: FAILED! => {",
                    '    "changed": false,',
                    '    "msg": "Package install failed"',
                    "}",
                    "",
                    "PLAY RECAP *********************************************************************",
                    "web-01 : ok=5 changed=2 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0",
                    "web-02 : ok=7 changed=3 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0",
                ]
            )
        else:
            output_lines.extend(
                [
                    "changed: [web-01]",
                    "changed: [web-02]",
                    "",
                    "TASK [Start service] ***********************************************************",
                    "ok: [web-01]",
                    "ok: [web-02]",
                    "",
                    "PLAY RECAP *********************************************************************",
                    "web-01 : ok=12 changed=2 unreachable=0 failed=0 skipped=3 rescued=0 ignored=0",
                    "web-02 : ok=12 changed=2 unreachable=0 failed=0 skipped=3 rescued=0 ignored=0",
                ]
            )

    return "\n".join(output_lines) + "\n"


# Mock instance configurations
MOCK_INSTANCES = {
    "mock-prod": {
        "name": "mock-prod",
        "description": "Mock Production Data (many jobs, high success rate, HA cluster)",
        "status": "online",
        "response_time": "234ms",
        "ping": {
            "ha": True,
            "version": "23.1.0",
            "active_node": "mock-controller-001.local",
            "install_uuid": "e8f9a7b5-1234-5678-9abc-def012345678",
            "instances": [
                {
                    "node": "mock-controller-001.local",
                    "node_type": "control",
                    "node_state": "ready",
                    "heartbeat": datetime.now().isoformat() + "Z",
                    "capacity": 136,
                    "consumed_capacity": 45,  # ~33% used
                    "version": "23.1.0",
                },
                {
                    "node": "mock-controller-002.local",
                    "node_type": "control",
                    "node_state": "ready",
                    "heartbeat": datetime.now().isoformat() + "Z",
                    "capacity": 136,
                    "consumed_capacity": 82,  # ~60% used
                    "version": "23.1.0",
                },
            ],
            "instance_groups": [
                {
                    "name": "controlplane",
                    "capacity": 272,
                    "consumed_capacity": 127,  # ~47% used
                    "percent_capacity_remaining": 53.3,
                    "jobs_running": 3,
                    "jobs_total": 156,
                    "instances": 2,
                    "is_container_group": False,
                },
                {
                    "name": "default",
                    "capacity": 272,
                    "consumed_capacity": 68,  # ~25% used
                    "percent_capacity_remaining": 75.0,
                    "jobs_running": 1,
                    "jobs_total": 89,
                    "instances": 2,
                    "is_container_group": False,
                },
            ],
        },
        # Will generate jobs dynamically
    },
    "mock-dev": {
        "name": "mock-dev",
        "description": "Mock Development Data (fewer jobs, more failures, single node)",
        "status": "slow",
        "response_time": "2.3s",
        "ping": {
            "ha": False,
            "version": "23.1.0",
            "active_node": "dev-aio-001.local",
            "install_uuid": "a1b2c3d4-5678-9abc-def0-123456789abc",
            "instances": [
                {
                    "node": "dev-aio-001.local",
                    "node_type": "hybrid",
                    "node_state": "ready",
                    "heartbeat": datetime.now().isoformat() + "Z",
                    "capacity": 136,
                    "consumed_capacity": 20,  # ~15% used (light dev load)
                    "version": "23.1.0",
                }
            ],
            "instance_groups": [
                {
                    "name": "controlplane",
                    "capacity": 136,
                    "consumed_capacity": 20,  # ~15% used
                    "percent_capacity_remaining": 85.3,
                    "jobs_running": 1,
                    "jobs_total": 23,
                    "instances": 1,
                    "is_container_group": False,
                },
                {
                    "name": "default",
                    "capacity": 136,
                    "consumed_capacity": 10,  # ~7% used
                    "percent_capacity_remaining": 92.6,
                    "jobs_running": 0,
                    "jobs_total": 12,
                    "instances": 1,
                    "is_container_group": False,
                },
            ],
        },
    },
    "mock-staging": {
        "name": "mock-staging",
        "description": "Mock Staging Data (mixed workload, moderate failures)",
        "status": "very_slow",
        "response_time": "7.8s",
        "ping": {
            "ha": False,
            "version": "23.1.0",
            "active_node": "staging-controller-001.local",
            "install_uuid": "f1e2d3c4-b5a6-9876-5432-1098fedcba09",
            "instances": [
                {
                    "node": "staging-controller-001.local",
                    "node_type": "control",
                    "node_state": "ready",
                    "heartbeat": datetime.now().isoformat() + "Z",
                    "capacity": 136,
                    "consumed_capacity": 102,  # ~75% used (heavy staging load)
                    "version": "23.1.0",
                }
            ],
            "instance_groups": [
                {
                    "name": "controlplane",
                    "capacity": 136,
                    "consumed_capacity": 102,  # ~75% used
                    "percent_capacity_remaining": 25.0,
                    "jobs_running": 4,
                    "jobs_total": 67,
                    "instances": 1,
                    "is_container_group": False,
                },
                {
                    "name": "default",
                    "capacity": 136,
                    "consumed_capacity": 95,  # ~70% used
                    "percent_capacity_remaining": 30.1,
                    "jobs_running": 3,
                    "jobs_total": 34,
                    "instances": 1,
                    "is_container_group": False,
                },
            ],
        },
    },
    "mock-offline": {
        "name": "mock-offline",
        "description": "Mock Offline Instance (simulates network timeout)",
        "status": "offline",
        "response_time": "Timeout",
        "ping": {
            "ha": False,
            "version": "Unknown",
            "active_node": "offline-controller-001.local",
            "install_uuid": "00000000-0000-0000-0000-000000000000",
            "instances": [],
            "instance_groups": [],
        },
    },
    "mock-error": {
        "name": "mock-error",
        "description": "Mock Error Instance (simulates API error)",
        "status": "error",
        "response_time": "N/A",
        "ping": {
            "ha": False,
            "version": "Unknown",
            "active_node": "error-controller-001.local",
            "install_uuid": "11111111-1111-1111-1111-111111111111",
            "instances": [],
            "instance_groups": [],
        },
    },
    "mock-unknown": {
        "name": "mock-unknown",
        "description": "Mock Unknown Instance (never checked)",
        "status": "unknown",
        "response_time": "N/A",
        "ping": {
            "ha": False,
            "version": "Unknown",
            "active_node": "unknown-controller-001.local",
            "install_uuid": "22222222-2222-2222-2222-222222222222",
            "instances": [],
            "instance_groups": [],
        },
    },
    "mock-disabled": {
        "name": "mock-disabled",
        "description": "Mock Disabled Instance (deactivated)",
        "status": "disabled",
        "response_time": "N/A",
        "ping": {
            "ha": False,
            "version": "22.5.0",
            "active_node": "disabled-controller-001.local",
            "install_uuid": "33333333-3333-3333-3333-333333333333",
            "instances": [],
            "instance_groups": [],
        },
    },
}


class MockAWXClient:
    """
    Mock AWX client for development

    Returns realistic mock data without making real API calls.
    Simulates network latency for realistic testing.
    """

    def __init__(self, instance_name: str, api_call_log: Optional[list] = None):
        """
        Initialize mock client

        Args:
            instance_name: One of: mock-prod, mock-dev, mock-staging
            api_call_log: Optional list to log API calls for debug console
        """
        if instance_name not in MOCK_INSTANCES:
            raise ValueError(f"Unknown mock instance: {instance_name}")

        self.instance_name = instance_name
        self.mock_data = MOCK_INSTANCES[instance_name]
        self.api_call_log = api_call_log

        # Generate mock jobs based on instance type
        self._generate_mock_jobs()

    def _generate_mock_jobs(self):
        """Generate realistic job data for this instance"""

        # Different job counts for different instances
        if self.instance_name == "mock-prod":
            num_running = 3
            num_recent = 50
            failure_rate = 0.05  # 5% failures
        elif self.instance_name == "mock-dev":
            num_running = 1
            num_recent = 20
            failure_rate = 0.25  # 25% failures
        else:  # mock-staging
            num_running = 2
            num_recent = 35
            failure_rate = 0.15  # 15% failures

        # Generate running jobs
        self.mock_data["running_jobs"] = []
        for i in range(num_running):
            job_id = 5000 + i
            status = random.choice(["running", "running", "pending"])  # NOSONAR
            launch_type = random.choice(["manual", "scheduled", "relaunch"])  # NOSONAR

            job = generate_job_data(
                job_id=job_id,
                name=random.choice(  # NOSONAR
                    ["Deploy Production", "Backup Database", "Update DNS", "Rollback Application", "Test Staging"]
                ),
                status=status,
                launch_type=launch_type,
                template_name=random.choice(
                    ["Deploy Playbook", "DB Backup", "DNS Update", "Rollback", "Test Suite"]
                ),  # NOSONAR
                project_name=random.choice(  # NOSONAR
                    ["Production Playbooks", "Operations Playbooks", "Network Playbooks", "Test Playbooks"]
                ),
                inventory_name=random.choice(  # NOSONAR
                    ["Production Servers", "DB Servers", "DNS Servers", "Staging Inventory"]
                ),
                exec_env_name=random.choice(["ee-29-rhel8", "ee-minimal", "ee-test"]),  # NOSONAR
                created_by=random.choice(["admin", "ansible", "jenkins", "netops"]),  # NOSONAR
                minutes_ago=random.randint(0, 10),  # NOSONAR
            )
            self.mock_data["running_jobs"].append(job)

        # Generate recent completed jobs
        self.mock_data["recent_jobs"] = []
        for i in range(num_recent):
            job_id = 4000 + num_recent - i  # Descending IDs

            # Determine status based on failure rate
            if random.random() < failure_rate:
                status = random.choice(["failed", "failed", "canceled"])  # NOSONAR
            else:
                status = "successful"

            launch_type = random.choice(["manual", "manual", "scheduled", "relaunch", "workflow"])  # NOSONAR

            job = generate_job_data(
                job_id=job_id,
                name=random.choice(  # NOSONAR
                    [
                        "Deploy Production",
                        "Backup Database",
                        "Update DNS",
                        "Rollback Application",
                        "Test Staging",
                        "Deploy Prod",
                    ]
                ),
                status=status,
                launch_type=launch_type,
                template_name=random.choice(  # NOSONAR
                    ["Deploy Playbook", "DB Backup", "DNS Update", "Rollback", "Test Suite"]
                ),
                project_name=random.choice(  # NOSONAR
                    ["Production Playbooks", "Operations Playbooks", "Network Playbooks", "Test Playbooks"]
                ),
                inventory_name=random.choice(  # NOSONAR
                    ["Production Servers", "DB Servers", "DNS Servers", "Staging Inventory"]
                ),
                exec_env_name=random.choice(["ee-29-rhel8", "ee-minimal", "ee-test"]),  # NOSONAR
                created_by=random.choice(["admin", "admin", "ansible", "jenkins", "netops"]),  # NOSONAR
                minutes_ago=random.randint(10, 60 * 24 * 7),  # NOSONAR
            )
            self.mock_data["recent_jobs"].append(job)

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Mock GET request

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Mock response data
        """
        # Simulate network latency (50-200ms)
        await asyncio.sleep(random.uniform(0.05, 0.2))  # NOSONAR

        # Route to appropriate mock response
        if endpoint == "/api/v2/ping/":
            return self.mock_data["ping"]

        elif endpoint == "/api/v2/jobs/" or endpoint == "/api/v2/unified_jobs/":
            return self._get_jobs_list(params or {})

        elif endpoint.startswith("/api/v2/jobs/") and endpoint.endswith("/"):
            # Job detail
            job_id = int(endpoint.split("/")[-2])
            return self._get_job_detail(job_id)

        elif endpoint.startswith("/api/v2/jobs/") and "/stdout/" in endpoint:
            # Job output
            job_id = int(endpoint.split("/")[4])
            return self._get_job_output(job_id)

        elif endpoint == "/api/v2/instances/":
            return self._get_instances()

        elif endpoint == "/api/v2/instance_groups/":
            return self._get_instance_groups()

        elif endpoint == "/api/v2/job_templates/":
            return self._get_job_templates()

        elif endpoint == "/api/v2/workflow_job_templates/":
            return self._get_workflow_templates()

        elif endpoint == "/api/v2/projects/":
            return self._get_projects()

        elif endpoint == "/api/v2/unified_job_templates/":
            # Unified endpoint returns both job and workflow templates
            return self._get_unified_templates()

        elif endpoint == "/api/v2/organizations/":
            return self._get_organizations()

        elif endpoint == "/api/v2/inventories/":
            return self._get_inventories()

        elif endpoint == "/api/v2/hosts/":
            return self._get_hosts()

        elif endpoint == "/api/v2/execution_environments/":
            return self._get_execution_environments()

        elif endpoint == "/api/v2/credentials/":
            return self._get_credentials()

        elif endpoint == "/api/v2/job_events/":
            return self._get_job_events()

        else:
            # Default response for unhandled endpoints
            return {"count": 0, "next": None, "previous": None, "results": []}

    def _get_jobs_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get jobs list with filtering"""

        # Check status filter
        status_filter = params.get("status__in", "").split(",")

        # Combine running and recent jobs
        all_jobs = self.mock_data.get("running_jobs", []) + self.mock_data.get("recent_jobs", [])

        # Filter by status
        if status_filter and status_filter[0]:
            filtered_jobs = [job for job in all_jobs if job["status"] in status_filter]
        else:
            filtered_jobs = all_jobs

        # Sort by started (descending)
        filtered_jobs.sort(key=lambda j: j.get("started") or j.get("created") or "", reverse=True)

        # Pagination
        page_size = int(params.get("page_size", 25))
        page = int(params.get("page", 1))
        start = (page - 1) * page_size
        end = start + page_size

        paginated_jobs = filtered_jobs[start:end]

        return {
            "count": len(filtered_jobs),
            "next": f"/api/v2/jobs/?page={page + 1}" if end < len(filtered_jobs) else None,
            "previous": f"/api/v2/jobs/?page={page - 1}" if page > 1 else None,
            "results": paginated_jobs,
        }

    def _get_job_detail(self, job_id: int) -> Dict[str, Any]:
        """Get individual job detail"""
        all_jobs = self.mock_data.get("running_jobs", []) + self.mock_data.get("recent_jobs", [])

        for job in all_jobs:
            if job["id"] == job_id:
                return job

        # Job not found
        raise ValueError(f"Job {job_id} not found")

    def _get_job_output(self, job_id: int) -> str:
        """Get job output/stdout"""
        try:
            job = self._get_job_detail(job_id)
            return generate_job_output(job_id, job["status"])
        except ValueError:
            return "Job not found\n"

    def _get_instances(self) -> Dict[str, Any]:
        """Get controller instances"""
        instances = self.mock_data["ping"]["instances"]

        # Add full instance details
        full_instances = []
        for idx, inst in enumerate(instances, start=1):
            capacity = inst["capacity"]
            consumed = inst.get("consumed_capacity", 0)
            pct_remaining = ((capacity - consumed) / capacity * 100) if capacity > 0 else 100.0
            # Derive jobs_running from consumed (rough estimate: ~20 capacity per job)
            jobs_running = max(0, consumed // 20)
            full_instances.append(
                {
                    "id": idx,
                    "type": "instance",
                    "url": f"/api/v2/instances/{idx}/",
                    "hostname": inst["node"],
                    "uuid": f"uuid-{idx}",
                    "created": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                    "modified": datetime.now().isoformat() + "Z",
                    "capacity_adjustment": "1.0",
                    "version": inst["version"],
                    "capacity": capacity,
                    "consumed_capacity": consumed,
                    "percent_capacity_remaining": pct_remaining,
                    "jobs_running": jobs_running,
                    "jobs_total": random.randint(50, 200),  # NOSONAR
                    "cpu": random.uniform(10.0, 30.0),  # NOSONAR
                    "memory": random.uniform(20.0, 50.0),  # NOSONAR
                    "cpu_capacity": capacity,
                    "mem_capacity": capacity,
                    "enabled": True,
                    "managed_by_policy": True,
                    "node_type": inst["node_type"],
                    "node_state": inst["node_state"],
                    "ip_address": f"10.0.0.{idx + 10}",
                    "listener_port": 27199,
                }
            )

        return {"count": len(full_instances), "next": None, "previous": None, "results": full_instances}

    def _get_instance_groups(self) -> Dict[str, Any]:
        """Get instance groups"""
        groups = self.mock_data["ping"]["instance_groups"]

        # Add full instance group details
        full_groups = []
        for idx, group in enumerate(groups, start=1):
            full_groups.append(
                {
                    "id": idx,
                    "type": "instance_group",
                    "url": f"/api/v2/instance_groups/{idx}/",
                    "name": group["name"],
                    "created": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                    "modified": datetime.now().isoformat() + "Z",
                    "capacity": group["capacity"],
                    "consumed_capacity": group["consumed_capacity"],
                    "percent_capacity_remaining": group["percent_capacity_remaining"],
                    "jobs_running": group["jobs_running"],
                    "jobs_total": group["jobs_total"],
                    "instances": group["instances"],
                    "is_container_group": group["is_container_group"],
                    "credential": None,
                    "policy_instance_percentage": 100,
                    "policy_instance_minimum": 0,
                    "policy_instance_list": [],
                    "pod_spec_override": "",
                }
            )

        return {"count": len(full_groups), "next": None, "previous": None, "results": full_groups}

    def _get_job_templates(self) -> Dict[str, Any]:
        """Get job templates"""
        job_templates = [
            {
                "id": 1,
                "type": "job_template",
                "url": "/api/v2/job_templates/1/",
                "name": "Deploy Application",
                "description": "Deploy application to production servers",
                "job_type": "run",
                "inventory": 1,
                "project": 1,
                "playbook": "deploy.yml",
                "created": (datetime.now() - timedelta(days=90)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=2)).isoformat() + "Z",
                "ask_variables_on_launch": False,
                "ask_limit_on_launch": False,
                "ask_tags_on_launch": False,
                "ask_skip_tags_on_launch": False,
                "ask_job_type_on_launch": False,
                "ask_inventory_on_launch": False,
                "ask_execution_environment_on_launch": False,
                "ask_credential_on_launch": False,
                "last_job_run": (datetime.now() - timedelta(hours=2)).isoformat() + "Z",
                "last_job_failed": False,
                "summary_fields": {
                    "organization": {"id": 1, "name": "Engineering"},
                    "inventory": {"id": 1, "name": "Production Servers"},
                    "project": {"id": 1, "name": "Application Playbooks", "status": "successful"},
                    "execution_environment": {"id": 1, "name": "ee-29-rhel8"},
                    "last_job": {
                        "id": 142,
                        "status": "successful",
                        "finished": (datetime.now() - timedelta(hours=2)).isoformat() + "Z",
                    },
                    "recent_jobs": [
                        {"id": 142, "status": "successful"},
                        {"id": 141, "status": "successful"},
                        {"id": 140, "status": "successful"},
                        {"id": 139, "status": "failed"},
                        {"id": 138, "status": "successful"},
                    ],
                },
            },
            {
                "id": 2,
                "type": "job_template",
                "url": "/api/v2/job_templates/2/",
                "name": "Database Backup",
                "description": "Backup all production databases",
                "job_type": "run",
                "inventory": 2,
                "project": 2,
                "playbook": "backup_db.yml",
                "created": (datetime.now() - timedelta(days=60)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
                "ask_variables_on_launch": True,
                "ask_limit_on_launch": False,
                "ask_tags_on_launch": False,
                "ask_skip_tags_on_launch": False,
                "ask_job_type_on_launch": False,
                "ask_inventory_on_launch": False,
                "ask_execution_environment_on_launch": False,
                "ask_credential_on_launch": False,
                "last_job_run": (datetime.now() - timedelta(hours=12)).isoformat() + "Z",
                "last_job_failed": False,
                "summary_fields": {
                    "organization": {"id": 1, "name": "Engineering"},
                    "inventory": {"id": 2, "name": "DB Servers"},
                    "project": {"id": 2, "name": "Database Playbooks", "status": "successful"},
                    "execution_environment": {"id": 1, "name": "ee-29-rhel8"},
                    "last_job": {
                        "id": 98,
                        "status": "successful",
                        "finished": (datetime.now() - timedelta(hours=12)).isoformat() + "Z",
                    },
                    "recent_jobs": [
                        {"id": 98, "status": "successful"},
                        {"id": 97, "status": "successful"},
                        {"id": 96, "status": "successful"},
                    ],
                },
            },
            {
                "id": 3,
                "type": "job_template",
                "url": "/api/v2/job_templates/3/",
                "name": "Config Sync",
                "description": "Sync configuration files",
                "job_type": "run",
                "inventory": 3,
                "project": 3,
                "playbook": "sync_config.yml",
                "created": (datetime.now() - timedelta(days=45)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(hours=12)).isoformat() + "Z",
                "ask_variables_on_launch": False,
                "ask_limit_on_launch": True,
                "ask_tags_on_launch": False,
                "ask_skip_tags_on_launch": False,
                "ask_job_type_on_launch": False,
                "ask_inventory_on_launch": False,
                "ask_execution_environment_on_launch": False,
                "ask_credential_on_launch": False,
                "last_job_run": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
                "last_job_failed": True,
                "summary_fields": {
                    "organization": {"id": 2, "name": "Operations"},
                    "inventory": {"id": 3, "name": "All Servers"},
                    "project": {"id": 3, "name": "Operations Playbooks", "status": "successful"},
                    "execution_environment": {"id": 2, "name": "ee-minimal"},
                    "last_job": {
                        "id": 76,
                        "status": "failed",
                        "finished": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
                    },
                    "recent_jobs": [
                        {"id": 76, "status": "failed"},
                        {"id": 75, "status": "successful"},
                        {"id": 74, "status": "failed"},
                        {"id": 73, "status": "successful"},
                        {"id": 72, "status": "successful"},
                    ],
                },
            },
            {
                "id": 4,
                "type": "job_template",
                "url": "/api/v2/job_templates/4/",
                "name": "Network Device Config",
                "description": "Configure network switches and routers",
                "job_type": "run",
                "inventory": 4,
                "project": 4,
                "playbook": "network_config.yml",
                "created": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(hours=6)).isoformat() + "Z",
                "ask_variables_on_launch": False,
                "ask_limit_on_launch": False,
                "ask_tags_on_launch": False,
                "ask_skip_tags_on_launch": False,
                "ask_job_type_on_launch": False,
                "ask_inventory_on_launch": False,
                "ask_execution_environment_on_launch": False,
                "ask_credential_on_launch": False,
                "last_job_run": (datetime.now() - timedelta(hours=6)).isoformat() + "Z",
                "last_job_failed": False,
                "summary_fields": {
                    "organization": {"id": 3, "name": "Network Team"},
                    "inventory": {"id": 4, "name": "Network Devices"},
                    "project": {"id": 4, "name": "Network Playbooks", "status": "successful"},
                    "execution_environment": {"id": 3, "name": "ee-network"},
                    "last_job": {
                        "id": 203,
                        "status": "successful",
                        "finished": (datetime.now() - timedelta(hours=6)).isoformat() + "Z",
                    },
                    "recent_jobs": [
                        {"id": 203, "status": "successful"},
                        {"id": 202, "status": "successful"},
                        {"id": 201, "status": "successful"},
                        {"id": 200, "status": "successful"},
                        {"id": 199, "status": "successful"},
                        {"id": 198, "status": "successful"},
                        {"id": 197, "status": "successful"},
                        {"id": 196, "status": "successful"},
                        {"id": 195, "status": "successful"},
                        {"id": 194, "status": "successful"},
                    ],
                },
            },
            {
                "id": 5,
                "type": "job_template",
                "url": "/api/v2/job_templates/5/",
                "name": "System Patching",
                "description": "Apply OS patches to all servers",
                "job_type": "run",
                "inventory": 1,
                "project": 5,
                "playbook": "patch_systems.yml",
                "created": (datetime.now() - timedelta(days=120)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=7)).isoformat() + "Z",
                "ask_variables_on_launch": False,
                "ask_limit_on_launch": True,
                "ask_tags_on_launch": True,
                "ask_skip_tags_on_launch": True,
                "ask_job_type_on_launch": True,
                "ask_inventory_on_launch": True,
                "ask_execution_environment_on_launch": True,
                "ask_credential_on_launch": True,
                "last_job_run": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                "last_job_failed": False,
                "summary_fields": {
                    "organization": {"id": 2, "name": "Operations"},
                    "inventory": {"id": 1, "name": "Production Servers"},
                    "project": {"id": 5, "name": "Operations Playbooks", "status": "successful"},
                    "execution_environment": {"id": 1, "name": "ee-29-rhel8"},
                    "last_job": {
                        "id": 12,
                        "status": "successful",
                        "finished": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                    },
                    "recent_jobs": [
                        {"id": 12, "status": "successful"},
                        {"id": 11, "status": "failed"},
                        {"id": 10, "status": "successful"},
                    ],
                },
            },
        ]

        return {"count": len(job_templates), "next": None, "previous": None, "results": job_templates}

    def _get_workflow_templates(self) -> Dict[str, Any]:
        """Get workflow templates"""
        workflow_templates = [
            {
                "id": 101,
                "type": "workflow_job_template",
                "url": "/api/v2/workflow_job_templates/101/",
                "name": "Full Deployment Workflow",
                "description": "Complete deployment: backup, deploy, verify, rollback on failure",
                "created": (datetime.now() - timedelta(days=75)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=5)).isoformat() + "Z",
                "ask_variables_on_launch": False,
                "ask_inventory_on_launch": False,
                "ask_limit_on_launch": False,
                "summary_fields": {
                    "organization": {"id": 1, "name": "Engineering"},
                },
            },
            {
                "id": 102,
                "type": "workflow_job_template",
                "url": "/api/v2/workflow_job_templates/102/",
                "name": "Disaster Recovery",
                "description": "DR workflow: backup verification, restore testing, failover",
                "created": (datetime.now() - timedelta(days=50)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=10)).isoformat() + "Z",
                "ask_variables_on_launch": True,
                "ask_inventory_on_launch": True,
                "ask_limit_on_launch": False,
                "summary_fields": {
                    "organization": {"id": 2, "name": "Operations"},
                },
            },
            {
                "id": 103,
                "type": "workflow_job_template",
                "url": "/api/v2/workflow_job_templates/103/",
                "name": "Monthly Maintenance",
                "description": "Monthly maintenance: patch, backup, security scan, cleanup",
                "created": (datetime.now() - timedelta(days=100)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=15)).isoformat() + "Z",
                "ask_variables_on_launch": False,
                "ask_inventory_on_launch": False,
                "ask_limit_on_launch": False,
                "summary_fields": {
                    "organization": {"id": 2, "name": "Operations"},
                },
            },
        ]

        return {"count": len(workflow_templates), "next": None, "previous": None, "results": workflow_templates}

    def _get_projects(self) -> Dict[str, Any]:
        """Get projects"""
        projects = [
            {
                "id": 1,
                "type": "project",
                "url": "/api/v2/projects/1/",
                "name": "Application Playbooks",
                "description": "Main application deployment playbooks",
                "scm_type": "git",
                "scm_url": "https://github.com/example/app-playbooks.git",
                "scm_branch": "main",
                "scm_revision": "a1b2c3d4e5f6",
                "scm_update_on_launch": True,
                "allow_override": False,
                "status": "successful",
                "created": (datetime.now() - timedelta(days=120)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
                "last_updated": (datetime.now() - timedelta(hours=6)).isoformat() + "Z",
                "summary_fields": {
                    "organization": {"id": 1, "name": "Engineering"},
                    "default_environment": {"id": 1, "name": "ee-29-rhel8"},
                },
            },
            {
                "id": 2,
                "type": "project",
                "url": "/api/v2/projects/2/",
                "name": "Database Playbooks",
                "description": "Database management and backup playbooks",
                "scm_type": "git",
                "scm_url": "https://github.com/example/db-playbooks.git",
                "scm_branch": "production",
                "scm_revision": "f6e5d4c3b2a1",
                "scm_update_on_launch": False,
                "allow_override": True,
                "status": "successful",
                "created": (datetime.now() - timedelta(days=90)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(hours=12)).isoformat() + "Z",
                "last_updated": (datetime.now() - timedelta(hours=12)).isoformat() + "Z",
                "summary_fields": {
                    "organization": {"id": 1, "name": "Engineering"},
                    "default_environment": {"id": 1, "name": "ee-29-rhel8"},
                },
            },
            {
                "id": 3,
                "type": "project",
                "url": "/api/v2/projects/3/",
                "name": "Operations Playbooks",
                "description": "General operations and maintenance playbooks",
                "scm_type": "git",
                "scm_url": "https://github.com/example/ops-playbooks.git",
                "scm_branch": "main",
                "scm_revision": "9876543210ab",
                "scm_update_on_launch": True,
                "allow_override": False,
                "status": "successful",
                "created": (datetime.now() - timedelta(days=75)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(hours=3)).isoformat() + "Z",
                "last_updated": (datetime.now() - timedelta(hours=3)).isoformat() + "Z",
                "summary_fields": {
                    "organization": {"id": 2, "name": "Operations"},
                    "default_environment": {"id": 2, "name": "ee-minimal"},
                },
            },
            {
                "id": 4,
                "type": "project",
                "url": "/api/v2/projects/4/",
                "name": "Network Playbooks",
                "description": "Network device configuration playbooks",
                "scm_type": "git",
                "scm_url": "https://github.com/example/network-playbooks.git",
                "scm_branch": "stable",
                "scm_revision": "abc123def456",
                "scm_update_on_launch": False,
                "allow_override": False,
                "status": "successful",
                "created": (datetime.now() - timedelta(days=60)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(days=5)).isoformat() + "Z",
                "last_updated": (datetime.now() - timedelta(days=5)).isoformat() + "Z",
                "summary_fields": {
                    "organization": {"id": 3, "name": "Network Team"},
                    "default_environment": {"id": 3, "name": "ee-network"},
                },
            },
            {
                "id": 5,
                "type": "project",
                "url": "/api/v2/projects/5/",
                "name": "Security Playbooks",
                "description": "Security scanning and hardening playbooks",
                "scm_type": "git",
                "scm_url": "https://github.com/example/security-playbooks.git",
                "scm_branch": "main",
                "scm_revision": "fedcba987654",
                "scm_update_on_launch": True,
                "allow_override": True,
                "status": "failed",
                "created": (datetime.now() - timedelta(days=45)).isoformat() + "Z",
                "modified": (datetime.now() - timedelta(hours=1)).isoformat() + "Z",
                "last_updated": (datetime.now() - timedelta(hours=1)).isoformat() + "Z",
                "summary_fields": {
                    "organization": {"id": 2, "name": "Operations"},
                    "default_environment": {"id": 1, "name": "ee-29-rhel8"},
                },
            },
        ]

        return {"count": len(projects), "next": None, "previous": None, "results": projects}

    def _get_organizations(self) -> Dict[str, Any]:
        """Get organizations"""
        organizations = [
            {"id": 1, "name": "Engineering", "description": "Software engineering team"},
            {"id": 2, "name": "Operations", "description": "IT operations team"},
            {"id": 3, "name": "Network Team", "description": "Network infrastructure team"},
            {"id": 4, "name": "Security", "description": "Security and compliance team"},
        ]
        return {"count": len(organizations), "next": None, "previous": None, "results": organizations}

    def _get_inventories(self) -> Dict[str, Any]:
        """Get inventories"""
        inventories = [
            {"id": 1, "name": "Production Servers", "description": "All production hosts", "total_hosts": 45},
            {"id": 2, "name": "DB Servers", "description": "Database servers", "total_hosts": 12},
            {"id": 3, "name": "All Servers", "description": "Complete server inventory", "total_hosts": 87},
            {"id": 4, "name": "Network Devices", "description": "Switches and routers", "total_hosts": 34},
            {"id": 5, "name": "Staging Inventory", "description": "Staging environment", "total_hosts": 20},
            {"id": 6, "name": "Development", "description": "Dev environment hosts", "total_hosts": 15},
        ]
        return {"count": len(inventories), "next": None, "previous": None, "results": inventories}

    def _get_hosts(self) -> Dict[str, Any]:
        """Get hosts"""
        # Generate mock hosts
        hosts = []
        for i in range(1, 214):  # 213 hosts total
            hosts.append(
                {
                    "id": i,
                    "name": f"host-{i:03d}.example.com",
                    "inventory": random.randint(1, 6),  # NOSONAR
                    "enabled": True,
                }
            )
        return {"count": len(hosts), "next": None, "previous": None, "results": hosts[:25]}  # First page only

    def _get_execution_environments(self) -> Dict[str, Any]:
        """Get execution environments"""
        exec_envs = [
            {"id": 1, "name": "ee-29-rhel8", "image": "quay.io/ansible/ee-29-rhel8:latest"},
            {"id": 2, "name": "ee-minimal", "image": "quay.io/ansible/ee-minimal:latest"},
            {"id": 3, "name": "ee-network", "image": "quay.io/ansible/ee-network:latest"},
            {"id": 4, "name": "ee-supported", "image": "quay.io/ansible/ee-supported:latest"},
            {"id": 5, "name": "custom-ee", "image": "registry.example.com/custom-ee:v2.1"},
        ]
        return {"count": len(exec_envs), "next": None, "previous": None, "results": exec_envs}

    def _get_credentials(self) -> Dict[str, Any]:
        """Get credentials"""
        credentials = [
            {"id": 1, "name": "SSH Key - Prod", "credential_type": 1, "kind": "ssh"},
            {"id": 2, "name": "SSH Key - Dev", "credential_type": 1, "kind": "ssh"},
            {"id": 3, "name": "AWS Credentials", "credential_type": 2, "kind": "cloud"},
            {"id": 4, "name": "Vault Password", "credential_type": 3, "kind": "vault"},
            {"id": 5, "name": "GitHub PAT", "credential_type": 4, "kind": "scm"},
            {"id": 6, "name": "Network Credentials", "credential_type": 1, "kind": "ssh"},
            {"id": 7, "name": "Container Registry", "credential_type": 5, "kind": "registry"},
            {"id": 8, "name": "Azure Service Principal", "credential_type": 2, "kind": "cloud"},
        ]
        return {"count": len(credentials), "next": None, "previous": None, "results": credentials}

    def _get_job_events(self) -> Dict[str, Any]:
        """Get job events (for count only)"""
        # Large count to simulate real AWX environment
        return {"count": 45678, "next": None, "previous": None, "results": []}

    def _launch_job_template(self, template_id: int, launch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Launch a job template and return the created job"""
        # Find the template
        templates = self._get_job_templates()["results"]
        template = None
        for t in templates:
            if t["id"] == template_id:
                template = t
                break

        if not template:
            raise ValueError(f"Job template {template_id} not found")

        # Generate a new job ID (use a high number to avoid conflicts)
        new_job_id = 6000 + random.randint(1, 9999)  # NOSONAR

        # Create job from template
        job = generate_job_data(
            job_id=new_job_id,
            name=template["name"],
            status="pending",
            launch_type="manual",
            template_name=template["name"],
            project_name=template["summary_fields"]["project"]["name"],
            inventory_name=template["summary_fields"]["inventory"]["name"],
            exec_env_name=template["summary_fields"]["execution_environment"]["name"],
            created_by="admin",
            minutes_ago=0,
        )

        # Override playbook from template
        job["playbook"] = template["playbook"]
        job["job_template"] = template_id

        # Add to running jobs
        self.mock_data["running_jobs"].insert(0, job)

        return job

    def _sync_project(self, project_id: int) -> Dict[str, Any]:
        """Trigger project sync and return the created project_update job"""
        # Find the project
        projects = self._get_projects()["results"]
        project = None
        for p in projects:
            if p["id"] == project_id:
                project = p
                break

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Generate a new job ID for project_update
        new_job_id = 7000 + random.randint(1, 9999)  # NOSONAR

        # Create project_update job
        now = datetime.now()
        job = {
            "id": new_job_id,
            "type": "project_update",
            "url": f"/api/v2/project_updates/{new_job_id}/",
            "name": f'{project["name"]} - Sync',
            "description": "",
            "status": "pending",
            "failed": False,
            "started": None,
            "finished": None,
            "canceled_on": None,
            "elapsed": 0.0,
            "job_explanation": "",
            "created": now.isoformat() + "Z",
            "modified": now.isoformat() + "Z",
            "launch_type": "manual",
            "scm_type": project["scm_type"],
            "scm_url": project["scm_url"],
            "scm_branch": project["scm_branch"],
            "scm_revision": project.get("scm_revision", ""),
            "project": project_id,
            "summary_fields": {
                "project": {
                    "id": project_id,
                    "name": project["name"],
                    "description": project.get("description", ""),
                },
                "organization": project["summary_fields"]["organization"],
                "created_by": {"id": 1, "username": "admin", "first_name": "", "last_name": ""},
            },
        }

        # Add to running jobs
        self.mock_data["running_jobs"].insert(0, job)

        return job

    def _relaunch_job(self, job_id: int, relaunch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Relaunch a job and return the created job"""
        # Find the original job (search in both running and recent jobs)
        all_jobs = self.mock_data.get("running_jobs", []) + self.mock_data.get("recent_jobs", [])
        original_job = None
        for j in all_jobs:
            if j["id"] == job_id:
                original_job = j
                break

        if not original_job:
            raise ValueError(f"Job {job_id} not found")

        # Check relaunch mode (all hosts or failed hosts only)
        hosts_mode = relaunch_data.get("hosts", "all")

        # Generate a new job ID (use 8000+ range for relaunched jobs)
        new_job_id = 8000 + random.randint(1, 9999)  # NOSONAR

        # Create new job based on original job
        # Copy most fields from original, but reset status and timestamps
        new_job = generate_job_data(
            job_id=new_job_id,
            name=original_job["name"],
            status="pending",
            launch_type="relaunch",
            template_name=original_job.get("summary_fields", {}).get("job_template", {}).get("name", "Unknown"),
            project_name=original_job.get("summary_fields", {}).get("project", {}).get("name", "Unknown"),
            inventory_name=original_job.get("summary_fields", {}).get("inventory", {}).get("name", "Unknown"),
            exec_env_name=original_job.get("summary_fields", {})
            .get("execution_environment", {})
            .get("name", "Unknown"),
            created_by="admin",
            minutes_ago=0,
        )

        # Copy additional fields from original job
        new_job["playbook"] = original_job.get("playbook", "N/A")
        new_job["job_template"] = original_job.get("job_template")
        new_job["job_type"] = original_job.get("job_type", "run")
        new_job["extra_vars"] = original_job.get("extra_vars", "{}")
        new_job["limit"] = original_job.get("limit", "")
        new_job["job_tags"] = original_job.get("job_tags", "")
        new_job["skip_tags"] = original_job.get("skip_tags", "")

        # If relaunching failed hosts only, set limit to failed hosts
        if hosts_mode == "failed":
            # In a real implementation, this would limit to actual failed hosts
            # For mock, we'll just note it in the job explanation
            new_job["job_explanation"] = "Relaunched with failed hosts only"
            new_job["limit"] = "failed_hosts"  # Mock indication

        # Add to running jobs
        self.mock_data["running_jobs"].insert(0, new_job)

        return new_job

    def _cancel_job(self, job_id: int) -> Dict[str, Any]:
        """Cancel a running job and return the updated job"""
        # Find the job (search in running jobs primarily)
        job_to_cancel = None
        job_location = None  # Track which list contains the job

        for j in self.mock_data.get("running_jobs", []):
            if j["id"] == job_id:
                job_to_cancel = j
                job_location = "running_jobs"
                break

        if not job_to_cancel:
            # Check recent jobs too (in case it just finished)
            for j in self.mock_data.get("recent_jobs", []):
                if j["id"] == job_id:
                    job_to_cancel = j
                    job_location = "recent_jobs"
                    break

        if not job_to_cancel:
            raise ValueError(f"Job {job_id} not found")

        # Verify job is cancellable (only running/pending/waiting jobs)
        if job_to_cancel["status"] not in ("pending", "waiting", "running"):
            raise ValueError(f"Cannot cancel {job_to_cancel['status']} job - only running jobs can be cancelled")

        # Update job status to canceled
        job_to_cancel["status"] = "canceled"
        job_to_cancel["failed"] = False

        # Set finished timestamp to now
        from datetime import datetime, timezone

        job_to_cancel["finished"] = datetime.now(timezone.utc).isoformat()

        # Calculate elapsed time if job was started
        if job_to_cancel.get("started"):
            try:
                started_dt = datetime.fromisoformat(job_to_cancel["started"].replace("Z", "+00:00"))
                finished_dt = datetime.fromisoformat(job_to_cancel["finished"].replace("Z", "+00:00"))
                elapsed = (finished_dt - started_dt).total_seconds()
                job_to_cancel["elapsed"] = elapsed
            except:
                job_to_cancel["elapsed"] = 0

        # Add cancellation explanation
        job_to_cancel["job_explanation"] = "Job was manually cancelled by user"

        # Move from running_jobs to recent_jobs if it's in running_jobs
        if job_location == "running_jobs":
            self.mock_data["running_jobs"].remove(job_to_cancel)
            self.mock_data["recent_jobs"].insert(0, job_to_cancel)

        return job_to_cancel

    def _get_unified_templates(self) -> Dict[str, Any]:
        """Get unified job templates (all launchable template types)

        Returns all "launchable" template types that can trigger jobs:
        - job_template: Regular job templates (run playbooks)
        - workflow_job_template: Workflow templates (multi-step workflows)
        - project: Projects (can be launched to trigger git sync)
        - system_job_template: System maintenance templates
        - inventory_source: Inventory sources (can be synced)

        IMPORTANT: These are TEMPLATE types, not JOB types.
        Job types like system_job, inventory_update, project_update are excluded
        because they are job results, not launchable templates.
        """
        job_templates = self._get_job_templates()["results"]
        workflow_templates = self._get_workflow_templates()["results"]
        projects = self._get_projects()["results"]
        # system_job_templates would go here if we add them
        # inventory_sources would go here if we add them

        all_templates = job_templates + workflow_templates + projects

        # Filter to only template types (not job result types)
        # This is defensive - ensures we only show launchable templates
        all_templates = [
            t
            for t in all_templates
            if t.get("type")
            in ("job_template", "workflow_job_template", "project", "system_job_template", "inventory_source")
        ]

        # Sort by modified (newest first)
        all_templates.sort(key=lambda t: t.get("modified", ""), reverse=True)

        return {"count": len(all_templates), "next": None, "previous": None, "results": all_templates}

    # Other HTTP methods
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock POST request"""
        await asyncio.sleep(random.uniform(0.05, 0.2))  # NOSONAR

        # Handle job template launch
        if "/job_templates/" in endpoint and endpoint.endswith("/launch/"):
            # Extract template ID from endpoint: /api/v2/job_templates/{id}/launch/
            template_id = int(endpoint.split("/")[-3])
            return self._launch_job_template(template_id, data or {})

        # Handle project sync
        if "/projects/" in endpoint and endpoint.endswith("/update/"):
            # Extract project ID from endpoint: /api/v2/projects/{id}/update/
            project_id = int(endpoint.split("/")[-3])
            return self._sync_project(project_id)

        # Handle job relaunch
        if "/jobs/" in endpoint and endpoint.endswith("/relaunch/"):
            # Extract job ID from endpoint: /api/v2/jobs/{id}/relaunch/
            job_id = int(endpoint.split("/")[-3])
            return self._relaunch_job(job_id, data or {})

        # Handle job cancellation
        if endpoint.endswith("/cancel/"):
            # Extract job ID from endpoint: /api/v2/jobs/{id}/cancel/ (or project_updates, etc.)
            job_id = int(endpoint.split("/")[-3])
            return self._cancel_job(job_id)

        return {"detail": "Mock POST not implemented"}

    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock PUT request"""
        await asyncio.sleep(random.uniform(0.05, 0.2))  # NOSONAR
        return {"detail": "Mock PUT not implemented"}

    async def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock PATCH request"""
        await asyncio.sleep(random.uniform(0.05, 0.2))  # NOSONAR
        return {"detail": "Mock PATCH not implemented"}

    async def delete(self, endpoint: str) -> None:
        """Mock DELETE request"""
        await asyncio.sleep(random.uniform(0.05, 0.2))  # NOSONAR
        pass
