"""
AWX TUI - Classic Dashboard

Full-featured dashboard per DASHBOARD.md specification.
Supports admin persona with comprehensive metrics and job monitoring.
"""

from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from awx_tui.dashboards import register_dashboard
from awx_tui.dashboards.base import BaseDashboard
from awx_tui.utils import format_playbook_path


class TopPanel(Static):
    """Top panel with rotating title, instance health, running jobs, and last refresh time."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_refresh_time = None
        self.running_jobs_count = 0
        self.capacity_pct = 0
        self.instance_status = "unknown"
        self.instance_name = "No instance"
        self.response_time = "N/A"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="top-panel-layout"):
            # Column 1 (50%) - Rotating title @ instance + health + response time
            yield Static("Loading...", classes="top-title")

            # Column 2 (25%) - Running jobs + capacity
            yield Static("🚀 -- | Cap: --%", classes="top-jobs")

            # Column 3 (25%) - Last refresh timestamp
            yield Static("⏱️ LOADING", classes="top-refresh")

    def on_mount(self) -> None:
        """Initial display update and start auto-refresh timer."""
        self.update_display()
        # Auto-update every second (for rotating title and timestamp)
        self.set_interval(1.0, self.update_display)

    def update_display(self):
        """Update top panel display with current data."""
        # Get current app name from rotating titles
        if hasattr(self.app, "current_app_name"):
            app_name = self.app.current_app_name
        else:
            app_name = "AWX TUI"

        # Get current instance info
        if hasattr(self.app, "instance_manager"):
            instance_manager = self.app.instance_manager
            current_instance = instance_manager.current_instance
            if current_instance:
                self.instance_name = current_instance

                # Get instance config for status and response time
                config = self.app.app_config.instances.get(current_instance)
                if config:
                    if hasattr(config, "last_status"):
                        self.instance_status = config.last_status or "unknown"
                    # Get response time from last ping check (stored during instance selection)
                    if hasattr(config, "last_response_time"):
                        self.response_time = config.last_response_time or "N/A"

        # Instance health with emoji
        status_emoji_map = {
            "online": "[green]✓[/green]",
            "slow": "⚠",
            "very_slow": "🐌",
            "offline": "✗",
            "error": "[red]✗[/red]",
            "unknown": "❓",
            "ready": "[green]✓[/green]",
        }
        status_emoji = status_emoji_map.get(self.instance_status, "❓")
        status_text = self.instance_status.replace("_", " ").title()

        # Column 1: Title - Screen @ Instance + Status (response time)
        title_text = (
            f"{app_name} - Dashboard @ {self.instance_name} {status_emoji} {status_text} ({self.response_time})"
        )

        # Column 2: Running jobs + capacity bar
        bar = self.screen._build_capacity_bar(self.capacity_pct)
        jobs_text = f"🚀 {self.running_jobs_count} | {bar} {self.capacity_pct}%"

        # Column 3: Last refresh timestamp (24hr format)
        if self.last_refresh_time:
            refresh_text = f"⏱️ {self.last_refresh_time.strftime('%H:%M:%S')}"
        else:
            refresh_text = "⏱️ LOADING"

        # Update the three columns
        try:
            self.query_one(".top-title", Static).update(title_text)
            self.query_one(".top-jobs", Static).update(jobs_text)
            self.query_one(".top-refresh", Static).update(refresh_text)
        except:
            pass  # Ignore if widgets not found during startup

    def update_metrics(self, running_jobs: int = 0, capacity_pct: int = 0):
        """Update running jobs count and capacity percentage."""
        self.running_jobs_count = running_jobs
        self.capacity_pct = capacity_pct
        self.last_refresh_time = datetime.now()
        self.update_display()


@register_dashboard("classic")
class ClassicDashboard(BaseDashboard):
    """
    Classic full-featured dashboard per DASHBOARD.md:

    Row 1: INSTANCES | INSTANCE GROUPS (side by side)
    Row 2: SUCCESS GRAPH (40%) | FAILED GRAPH (40%) | STATS (20%)
    Row 3: RUNNING JOBS table (full width)
    Row 4: RECENT JOBS table (full width)
    """

    CSS_PATH = "classic.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("escape", "back_to_instances", "Back"),
        ("1", "goto_dashboard", "Dashboard"),
        ("2", "goto_historic_jobs", "Historic Jobs"),
        ("3", "goto_active_jobs", "Active Jobs"),
        ("4", "goto_projects", "Projects"),
        ("5", "goto_templates", "Templates"),
        ("6", "goto_inventories", "Inventories"),
        ("ctrl+d", "debug_console", "Debug"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._running_jobs_data = []  # Store running jobs for job type lookup
        self._recent_jobs_data = []  # Store recent jobs for job type lookup

    def compose(self) -> ComposeResult:
        """Create dashboard layout per DASHBOARD.md"""
        yield Header()
        yield TopPanel().add_class("top-panel")
        with Container(id="dashboard-container", classes="classic-dashboard"):
            # Row 1: INSTANCES | INSTANCE GROUPS
            with Horizontal(id="instances-row"):
                with Vertical(id="instances-panel"):
                    yield Static("INSTANCES (0)", id="instances-header", classes="section-header")
                    yield DataTable(id="instances-table", show_cursor=False)

                with Vertical(id="groups-panel"):
                    yield Static("INSTANCE GROUPS (0)", id="groups-header", classes="section-header")
                    yield DataTable(id="groups-table", show_cursor=False)

            # Row 2: SUCCESS GRAPH | FAILED GRAPH | STATS
            with Horizontal(id="graphs-row"):
                with Vertical(classes="graph-box"):
                    yield DataTable(id="success-table", show_cursor=False)

                with Vertical(classes="graph-box"):
                    yield DataTable(id="failed-table", show_cursor=False)

                with Vertical(classes="stats-box"):
                    yield Static("STATS", id="stats-header", classes="section-header")
                    yield Static("", id="stats-content")

            # Row 3: RUNNING JOBS
            with Container(id="running-jobs-panel"):
                yield Static("RUNNING JOBS (0)", id="running-jobs-header", classes="table-header")
                yield DataTable(id="running-jobs-table", cursor_type="row")

            # Row 4: RECENT JOBS
            with Container(id="recent-jobs-panel"):
                yield Static("RECENT JOBS (0)", id="recent-jobs-header", classes="table-header")
                yield DataTable(id="recent-jobs-table", cursor_type="row")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize tables and load data"""
        # Set up Instances table
        instances_table = self.query_one("#instances-table", DataTable)
        instances_table.add_columns("Hostname", "Capacity", "Forks", "Jobs", "Total")

        # Set up Instance Groups table
        groups_table = self.query_one("#groups-table", DataTable)
        groups_table.add_columns("Name", "Capacity", "Forks", "Jobs", "Total")

        # Set up Success graph table
        success_table = self.query_one("#success-table", DataTable)
        success_table.add_columns("Date", "Graph", "Successful Jobs")

        # Set up Failed graph table
        failed_table = self.query_one("#failed-table", DataTable)
        failed_table.add_columns("Date", "Graph", "Failed Jobs")

        # Set up Running Jobs table
        running_table = self.query_one("#running-jobs-table", DataTable)
        running_table.add_columns(
            "ID",
            "",
            "",
            "Name",
            "User",
            "Project",
            "Playbook",
            "Template",
            "Inventory",
            "Execution Environment",
            "Forks",
            "Job Slices",
            "Started",
        )

        # Set up Recent Jobs table
        recent_table = self.query_one("#recent-jobs-table", DataTable)
        recent_table.add_columns(
            "ID",
            "",
            "",
            "Name",
            "User",
            "Project",
            "Playbook",
            "Template",
            "Inventory",
            "Execution Environment",
            "Forks",
            "Job Slices",
            "Finished",
        )

        # Call parent on_mount to trigger initial data load and start auto-refresh timer
        await super().on_mount()

    async def fetch_data(self, client):
        """
        Fetch all data for classic dashboard.

        Returns:
            dict: Dashboard data with keys:
                - running_jobs: List of running/pending jobs
                - recent_jobs: List of recent completed jobs
                - graph_jobs: List of jobs from last 7 days for graphs
                - instances: List of AWX instances
                - groups: List of instance groups
                - ping: Ping response (version, license, etc.)
                - counts: Dict of resource counts (orgs, projects, etc.)
                - metrics: Dict with running_jobs_count and capacity_pct for TopPanel
        """
        import asyncio

        # Calculate date 7 days ago for graphs
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # Define all API calls to run in parallel
        async def safe_get(endpoint, params=None, description=""):
            """Wrapper to catch exceptions per-endpoint"""
            try:
                return await client.get(endpoint, params=params)
            except Exception as e:
                self.app.log.error(f"Failed to fetch {description}: {e}")
                return {}

        # Fetch all data in parallel using asyncio.gather()
        results = await asyncio.gather(
            safe_get(
                "/api/v2/unified_jobs/", {"status__in": "pending,waiting,running", "page_size": 200}, "running jobs"
            ),
            safe_get(
                "/api/v2/unified_jobs/",
                {"status__in": "successful,failed,error,canceled", "page_size": 25, "order_by": "-finished"},
                "recent jobs",
            ),
            safe_get(
                "/api/v2/unified_jobs/",
                {"finished__gte": seven_days_ago, "page_size": 500, "order_by": "-finished"},
                "graph data",
            ),
            safe_get("/api/v2/instances/", None, "instances"),
            safe_get("/api/v2/instance_groups/", None, "instance groups"),
            safe_get("/api/v2/ping/", None, "ping"),
            safe_get("/api/v2/unified_jobs/", {"page_size": 1}, "unified jobs count"),
            safe_get("/api/v2/organizations/", {"page_size": 1}, "organizations count"),
            safe_get("/api/v2/projects/", {"page_size": 1}, "projects count"),
            safe_get("/api/v2/job_templates/", {"page_size": 1}, "job templates count"),
            safe_get("/api/v2/workflow_job_templates/", {"page_size": 1}, "workflow templates count"),
            safe_get("/api/v2/inventories/", {"page_size": 1}, "inventories count"),
            safe_get("/api/v2/hosts/", {"page_size": 1}, "hosts count"),
            safe_get("/api/v2/execution_environments/", {"page_size": 1}, "execution environments count"),
            safe_get("/api/v2/credentials/", {"page_size": 1}, "credentials count"),
        )

        # Unpack results
        (
            running_resp,
            recent_resp,
            graph_resp,
            instances_resp,
            groups_resp,
            ping_resp,
            unified_jobs_resp,
            orgs_resp,
            projects_resp,
            templates_resp,
            workflows_resp,
            inventories_resp,
            hosts_resp,
            exec_envs_resp,
            credentials_resp,
        ) = results

        # Calculate metrics for TopPanel
        running_jobs = running_resp.get("results", [])
        running_jobs_count = len(running_jobs)

        # Calculate overall capacity percentage from instances
        instances = instances_resp.get("results", [])
        total_capacity = sum(inst.get("capacity", 0) for inst in instances)
        total_consumed = sum(inst.get("consumed_capacity", 0) for inst in instances)
        capacity_pct = int(((total_capacity - total_consumed) / total_capacity * 100) if total_capacity > 0 else 0)

        # Return all fetched data
        return {
            "running_jobs": running_resp.get("results", []),
            "recent_jobs": recent_resp.get("results", []),
            "graph_jobs": graph_resp.get("results", []),
            "instances": instances_resp.get("results", []),
            "groups": groups_resp.get("results", []),
            "ping": ping_resp,
            "counts": {
                "unified_jobs": unified_jobs_resp,
                "orgs": orgs_resp,
                "projects": projects_resp,
                "templates": templates_resp,
                "workflows": workflows_resp,
                "inventories": inventories_resp,
                "hosts": hosts_resp,
                "exec_envs": exec_envs_resp,
                "credentials": credentials_resp,
            },
            "metrics": {
                "running_jobs_count": running_jobs_count,
                "capacity_pct": capacity_pct,
            },
        }

    def update_display(self, data):
        """
        Update dashboard UI with fetched data.

        Args:
            data: Dict returned from fetch_data()
        """
        # Update TopPanel with current metrics
        try:
            top_panel = self.query_one(TopPanel)
            metrics = data["metrics"]
            top_panel.update_metrics(running_jobs=metrics["running_jobs_count"], capacity_pct=metrics["capacity_pct"])
        except:
            pass  # TopPanel not found or not ready

        # Update all dashboard sections
        self._update_instances(data["instances"])
        self._update_groups(data["groups"])
        self._update_graphs(data["graph_jobs"])

        counts = data["counts"]
        self._update_stats(
            counts["unified_jobs"],
            data["ping"],
            counts["orgs"],
            counts["projects"],
            counts["templates"],
            counts["workflows"],
            counts["inventories"],
            counts["hosts"],
            counts["exec_envs"],
            counts["credentials"],
        )

        self._update_running_jobs(data["running_jobs"])
        self._update_recent_jobs(data["recent_jobs"])

    def _build_capacity_bar(self, capacity_pct: int) -> str:
        """Build colored capacity bar with 10 blocks and dithering"""
        full_blocks = capacity_pct // 10
        remainder = capacity_pct % 10

        # Determine color based on capacity level
        if capacity_pct >= 60:
            color = "green"
        elif capacity_pct > 30:
            color = "yellow"
        elif capacity_pct >= 10:
            color = "orange1"
        else:
            color = "red"

        # Build capacity bar with 10 blocks total
        bar = ""
        for i in range(10):
            if i < full_blocks:
                bar += "█"
            elif i == full_blocks and remainder > 0:
                if remainder >= 7:
                    bar += "▓"
                elif remainder >= 4:
                    bar += "▒"
                else:
                    bar += "░"
            else:
                bar += "░"

        return f"[{color}]{bar}[/{color}]"

    def _update_instances(self, instances: list) -> None:
        """Update INSTANCES DataTable"""
        # Update header count
        self.query_one("#instances-header").update(f"INSTANCES ({len(instances)})")

        # Get table
        table = self.query_one("#instances-table", DataTable)
        table.clear()

        for inst in instances:
            hostname = inst.get("hostname", "unknown")
            capacity = inst.get("capacity", 0)
            consumed = inst.get("consumed_capacity", 0)
            jobs_running = inst.get("jobs_running", 0)
            jobs_total = inst.get("jobs_total", 0)

            pct = int(((capacity - consumed) / capacity * 100) if capacity > 0 else 0)
            bar = self._build_capacity_bar(pct)

            table.add_row(
                hostname, f"{bar} {pct}%", f"{consumed:>3}/{capacity:<3}", f"{jobs_running:>4}", f"{jobs_total:>5}"
            )

    def _update_groups(self, groups: list) -> None:
        """Update INSTANCE GROUPS DataTable"""
        # Update header count
        self.query_one("#groups-header").update(f"INSTANCE GROUPS ({len(groups)})")

        # Get table
        table = self.query_one("#groups-table", DataTable)
        table.clear()

        for group in groups:
            name = group.get("name", "unknown")
            capacity = group.get("capacity", 0)
            consumed = group.get("consumed_capacity", 0)
            jobs_running = group.get("jobs_running", 0)
            jobs_total = group.get("jobs_total", 0)
            inst_count = group.get("instances", 0)

            pct = int(((capacity - consumed) / capacity * 100) if capacity > 0 else 0)
            bar = self._build_capacity_bar(pct)

            table.add_row(
                f"{name} ({inst_count})",
                f"{bar} {pct}%",
                f"{consumed:>3}/{capacity:<3}",
                f"{jobs_running:>4}",
                f"{jobs_total:>5}",
            )

    def _update_graphs(self, jobs: list) -> None:
        """Update SUCCESS and FAILED DataTables with last 7 days data"""
        # Initialize counters for last 7 days (today = day 0, yesterday = day 1, etc.)
        success_counts = [0] * 7
        failed_counts = [0] * 7
        dates = []

        # Get current date (ignore time)
        today = datetime.now().date()

        # Build date list (7 days ago to today)
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            dates.append(date)

        # Count jobs by day
        for job in jobs:
            finished = job.get("finished")
            if not finished:
                continue

            try:
                # Parse finished timestamp (ISO 8601 format from AWX API)
                job_date = datetime.fromisoformat(finished.replace("Z", "+00:00")).date()

                # Calculate days ago
                days_ago = (today - job_date).days

                # Only count jobs from last 7 days
                if 0 <= days_ago < 7:
                    status = job.get("status", "")
                    if status == "successful":
                        success_counts[6 - days_ago] += 1  # Reverse index
                    elif status == "failed":
                        failed_counts[6 - days_ago] += 1  # Reverse index
            except (ValueError, AttributeError):
                # Skip jobs with invalid timestamps
                continue

        # Find max count and determine scale (per DASHBOARD.md spec)
        max_success = max(success_counts) if success_counts else 0
        max_failed = max(failed_counts) if failed_counts else 0

        # Determine Y-axis increment based on max value (threshold-based scaling)
        def get_y_increment(max_val):
            if max_val <= 50:
                return 10
            elif max_val <= 500:
                return 100
            elif max_val <= 5000:
                return 1000
            elif max_val <= 50000:
                return 10000
            else:
                return 100000

        success_increment = get_y_increment(max_success)
        failed_increment = get_y_increment(max_failed)

        # Update Success table (most recent first)
        success_table = self.query_one("#success-table", DataTable)
        success_table.clear()

        for i in range(len(dates) - 1, -1, -1):  # Reverse order (today first)
            date = dates[i]
            count = success_counts[i]
            # Build threshold-based bar
            bar = self._build_threshold_bar(count, success_increment, "green")

            # Format date as "Mon 2025-11-18"
            date_str = date.strftime("%a %Y-%m-%d")

            success_table.add_row(date_str, bar, f"{count:>4}")

        # Update Failed table (most recent first)
        failed_table = self.query_one("#failed-table", DataTable)
        failed_table.clear()

        for i in range(len(dates) - 1, -1, -1):  # Reverse order (today first)
            date = dates[i]
            count = failed_counts[i]
            # Build threshold-based bar
            bar = self._build_threshold_bar(count, failed_increment, "red")

            # Format date as "Mon 2025-11-18"
            date_str = date.strftime("%a %Y-%m-%d")

            failed_table.add_row(date_str, bar, f"{count:>4}")

    def _build_threshold_bar(self, count: int, increment: int, color: str) -> str:
        """
        Build threshold-based bar per DASHBOARD.md spec

        Each block represents 0.5 * increment (so 10 blocks = 5 thresholds)
        - SOLID (█): Value meets or exceeds this threshold
        - DITHERED (▒): Value is in threshold range but doesn't reach it
        - EMPTY (░): Value is below this threshold
        """
        # Max scale is 5 increments (matching DASHBOARD.md: 0, 10, 20, 30, 40, 50 for 10s)
        max_scale = increment * 5

        # Calculate percentage of max scale
        pct = (count / max_scale * 100) if max_scale > 0 else 0

        # Build bar with 10 blocks
        full_blocks = int(pct / 10)  # Each block = 10% of scale
        remainder = int(pct % 10)

        bar = ""
        for i in range(10):
            if i < full_blocks:
                bar += "█"  # Solid - threshold met
            elif i == full_blocks and remainder > 0:
                # Dithered - in threshold range but not fully met
                if remainder >= 7:
                    bar += "▓"
                elif remainder >= 4:
                    bar += "▒"
                else:
                    bar += "░"
            else:
                bar += "░"  # Empty - below threshold

        return f"[{color}]{bar}[/{color}]"

    def _build_capacity_bar_custom(self, pct: int, color: str) -> str:
        """Build capacity bar with custom color"""
        full_blocks = pct // 10
        remainder = pct % 10

        bar = ""
        for i in range(10):
            if i < full_blocks:
                bar += "█"
            elif i == full_blocks and remainder > 0:
                if remainder >= 7:
                    bar += "▓"
                elif remainder >= 4:
                    bar += "▒"
                else:
                    bar += "░"
            else:
                bar += "░"

        return f"[{color}]{bar}[/{color}]"

    def _update_stats(
        self,
        unified_jobs_resp: dict,
        ping_resp: dict,
        orgs_resp: dict,
        projects_resp: dict,
        templates_resp: dict,
        workflows_resp: dict,
        inventories_resp: dict,
        hosts_resp: dict,
        exec_envs_resp: dict,
        credentials_resp: dict,
    ) -> None:
        """Update STATS section with real counts"""
        total_jobs = unified_jobs_resp.get("count", 0)

        # Get counts from responses
        orgs_count = orgs_resp.get("count", 0)
        projects_count = projects_resp.get("count", 0)
        templates_count = templates_resp.get("count", 0)
        workflows_count = workflows_resp.get("count", 0)
        inventories_count = inventories_resp.get("count", 0)
        hosts_count = hosts_resp.get("count", 0)
        exec_envs_count = exec_envs_resp.get("count", 0)
        credentials_count = credentials_resp.get("count", 0)

        # Calculate success/failed from jobs (we could also query API for this)
        # For now, showing placeholder - we can calculate from graph_resp if needed

        stats = f"""Jobs: {total_jobs:,}

{'Orgs:':15} {orgs_count:>6,}  {'Execution Envs':15} {exec_envs_count:>6,}
{'Hosts:':15} {hosts_count:>6,}  {'Inventories:':15} {inventories_count:>6,}
{'Projects:':15} {projects_count:>6,}  {'Credentials:':15} {credentials_count:>6,}
{'Job Tmplts:':15} {templates_count:>6,}
{'Wrkflw Tmplts:':15} {workflows_count:>6,}  """

        self.query_one("#stats-content").update(stats)

    def _update_running_jobs(self, jobs: list) -> None:
        """Update RUNNING JOBS DataTable"""
        self._running_jobs_data = jobs  # Store for job type lookup
        self.query_one("#running-jobs-header").update(f"RUNNING JOBS ({len(jobs)})")

        table = self.query_one("#running-jobs-table", DataTable)

        # Save current job ID (from first column) to restore position
        selected_job_id = None
        cursor_row = 0
        if table.cursor_coordinate and table.row_count > 0:
            cursor_row = table.cursor_coordinate[0]
            try:
                selected_job_id = table.get_row_at(cursor_row)[0]  # First column is job ID
            except:
                pass

        table.clear()

        new_cursor_row = 0
        for idx, job in enumerate(jobs):
            jid = str(job.get("id", 0))
            name = job.get("name", "Unknown")[:25]
            user = job.get("summary_fields", {}).get("created_by", {}).get("username", "N/A")[:8]
            summary = job.get("summary_fields", {})
            status = job.get("status", "unknown")[:10]

            # Job type emoji
            job_type = job.get("type", "job")
            type_emoji = {
                "job": "🚀",
                "project_update": "🔄",
                "inventory_update": "📥",
                "workflow_job": "🔗",
                "system_job": "🔧",
                "ad_hoc_command": "⚡",
            }.get(job_type, "❓")

            # Status emoji
            status_emoji = {
                "successful": "[green]✓[/green]",
                "failed": "[red]✗[/red]",
                "running": "🏃",
                "pending": "⏳",
                "waiting": "⏳",
                "canceled": "⚠",
                "error": "❗",
            }.get(status, "❓")

            # Type-specific field display
            if job_type == "project_update":
                project_data = summary.get("project", {})
                project = project_data.get("name", "N/A")[:21]
                playbook = "GIT Sync"
                template = project
                scm_url = job.get("scm_url", "")
                if scm_url:
                    try:
                        from urllib.parse import urlparse

                        parsed = urlparse(scm_url)
                        inventory = parsed.netloc[:17] if parsed.netloc else "N/A"
                    except:
                        inventory = "N/A"
                else:
                    inventory = "N/A"
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            elif job_type == "inventory_update":
                source = job.get("source", "N/A")
                project = source[:21]
                playbook = "(inventory sync)"
                inventory_data = summary.get("inventory", {})
                inventory = inventory_data.get("name", "N/A")[:17]
                inv_source = summary.get("inventory_source", {})
                template = inv_source.get("name", "N/A")[:21]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            elif job_type == "workflow_job":
                project = "N/A"
                playbook = "(workflow)"
                workflow_template = summary.get("workflow_job_template", {})
                template = workflow_template.get("name", "N/A")[:21]
                inventory = "N/A"
                exec_env = "N/A"

            elif job_type == "system_job":
                project = "system"
                system_job_type = job.get("job_type", "N/A")
                playbook = system_job_type[:20]
                system_template = summary.get("system_job_template", {})
                template = system_template.get("name", "N/A")[:21]
                inventory = "AWX"
                exec_env = "N/A"

            elif job_type == "ad_hoc_command":
                project = "N/A"
                module_name = job.get("module_name", "N/A")
                playbook = module_name[:20]
                template = "N/A"
                inventory = summary.get("inventory", {}).get("name", "N/A")[:17]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            else:
                # Regular job
                project = summary.get("project", {}).get("name", "N/A")[:21]
                playbook_raw = job.get("playbook", "N/A")
                playbook = format_playbook_path(playbook_raw, max_length=20)
                template = summary.get("job_template", {}).get("name", "N/A")[:21]
                inventory = summary.get("inventory", {}).get("name", "N/A")[:17]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            # Get execution parameters
            forks = str(job.get("forks", "N/A"))
            job_slice_count = str(job.get("job_slice_count", "N/A"))

            # Format started timestamp
            started_str = "N/A"
            started = job.get("started")
            if started:
                try:
                    job_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    started_str = job_time.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    started_str = "N/A"

            # Track if this is the previously selected job
            if selected_job_id and jid == selected_job_id:
                new_cursor_row = idx

            table.add_row(
                jid,
                type_emoji,
                status_emoji,
                name,
                user,
                project,
                playbook,
                template,
                inventory,
                exec_env,
                forks,
                job_slice_count,
                started_str,
            )

        # Restore cursor to same job ID if found, otherwise use same row number
        if table.row_count > 0:
            # Check if we found the same job in the new list
            found_same_job = False
            if selected_job_id:
                try:
                    if table.get_row_at(new_cursor_row)[0] == selected_job_id:
                        found_same_job = True
                except:
                    pass

            if found_same_job:
                table.cursor_coordinate = (new_cursor_row, 0)
            else:
                # Fall back to same row number (clamped to table size)
                table.cursor_coordinate = (min(cursor_row, table.row_count - 1), 0)

    def _update_recent_jobs(self, jobs: list) -> None:
        """Update RECENT JOBS DataTable"""
        self._recent_jobs_data = jobs  # Store for job type lookup
        self.query_one("#recent-jobs-header").update(f"RECENT JOBS ({len(jobs)})")

        table = self.query_one("#recent-jobs-table", DataTable)

        # Save current job ID (from first column) to restore position
        selected_job_id = None
        cursor_row = 0
        if table.cursor_coordinate and table.row_count > 0:
            cursor_row = table.cursor_coordinate[0]
            try:
                selected_job_id = table.get_row_at(cursor_row)[0]  # First column is job ID
            except:
                pass

        table.clear()

        new_cursor_row = 0
        for idx, job in enumerate(jobs):
            jid = str(job.get("id", 0))
            name = job.get("name", "Unknown")[:25]
            user = job.get("summary_fields", {}).get("created_by", {}).get("username", "N/A")[:8]
            summary = job.get("summary_fields", {})
            status = job.get("status", "unknown")[:10]

            # Job type emoji
            job_type = job.get("type", "job")
            type_emoji = {
                "job": "🚀",
                "project_update": "🔄",
                "inventory_update": "📥",
                "workflow_job": "🔗",
                "system_job": "🔧",
                "ad_hoc_command": "⚡",
            }.get(job_type, "❓")

            # Status emoji
            status_emoji = {
                "successful": "[green]✓[/green]",
                "failed": "[red]✗[/red]",
                "running": "🏃",
                "pending": "⏳",
                "canceled": "⚠",
                "error": "❗",
            }.get(status, "❓")

            # Type-specific field display
            if job_type == "project_update":
                project_data = summary.get("project", {})
                project = project_data.get("name", "N/A")[:21]
                playbook = "GIT Sync"
                template = project
                scm_url = job.get("scm_url", "")
                if scm_url:
                    try:
                        from urllib.parse import urlparse

                        parsed = urlparse(scm_url)
                        inventory = parsed.netloc[:17] if parsed.netloc else "N/A"
                    except:
                        inventory = "N/A"
                else:
                    inventory = "N/A"
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            elif job_type == "inventory_update":
                source = job.get("source", "N/A")
                project = source[:21]
                playbook = "(inventory sync)"
                inventory_data = summary.get("inventory", {})
                inventory = inventory_data.get("name", "N/A")[:17]
                inv_source = summary.get("inventory_source", {})
                template = inv_source.get("name", "N/A")[:21]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            elif job_type == "workflow_job":
                project = "N/A"
                playbook = "(workflow)"
                workflow_template = summary.get("workflow_job_template", {})
                template = workflow_template.get("name", "N/A")[:21]
                inventory = "N/A"
                exec_env = "N/A"

            elif job_type == "system_job":
                project = "system"
                system_job_type = job.get("job_type", "N/A")
                playbook = system_job_type[:20]
                system_template = summary.get("system_job_template", {})
                template = system_template.get("name", "N/A")[:21]
                inventory = "AWX"
                exec_env = "N/A"

            elif job_type == "ad_hoc_command":
                project = "N/A"
                module_name = job.get("module_name", "N/A")
                playbook = module_name[:20]
                template = "N/A"
                inventory = summary.get("inventory", {}).get("name", "N/A")[:17]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            else:
                # Regular job
                project = summary.get("project", {}).get("name", "N/A")[:21]
                playbook_raw = job.get("playbook", "N/A")
                playbook = format_playbook_path(playbook_raw, max_length=20)
                template = summary.get("job_template", {}).get("name", "N/A")[:21]
                inventory = summary.get("inventory", {}).get("name", "N/A")[:17]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            # Get execution parameters
            forks = str(job.get("forks", "N/A"))
            job_slice_count = str(job.get("job_slice_count", "N/A"))

            # Format finished timestamp
            finished_str = "?"
            finished = job.get("finished")
            if finished:
                try:
                    job_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                    finished_str = job_time.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    finished_str = "?"

            # Track if this is the previously selected job
            if selected_job_id and jid == selected_job_id:
                new_cursor_row = idx

            table.add_row(
                jid,
                type_emoji,
                status_emoji,
                name,
                user,
                project,
                playbook,
                template,
                inventory,
                exec_env,
                forks,
                job_slice_count,
                finished_str,
            )

        # Restore cursor to same job ID if found, otherwise use same row number
        if table.row_count > 0:
            # Check if we found the same job in the new list
            found_same_job = False
            if selected_job_id:
                try:
                    if table.get_row_at(new_cursor_row)[0] == selected_job_id:
                        found_same_job = True
                except:
                    pass

            if found_same_job:
                table.cursor_coordinate = (new_cursor_row, 0)
            else:
                # Fall back to same row number (clamped to table size)
                table.cursor_coordinate = (min(cursor_row, table.row_count - 1), 0)

    def action_refresh(self) -> None:
        """Manual refresh dashboard data (shows notifications)"""
        self.app.notify("Refreshing dashboard...", timeout=1)
        # Call parent class refresh which triggers fetch_data() and update_display()
        super().action_refresh()

    def action_debug_console(self) -> None:
        """Open debug console"""
        self.app.action_toggle_debug()

    def action_goto_dashboard(self) -> None:
        """Go to dashboard (already here, do nothing)"""
        pass

    def action_goto_historic_jobs(self) -> None:
        """Navigate to Historic Jobs screen"""
        from awx_tui.screens.historic_jobs import HistoricJobsScreen

        self.app.push_screen(HistoricJobsScreen())

    def action_goto_active_jobs(self) -> None:
        """Navigate to Active Jobs screen"""
        from awx_tui.screens.active_jobs import ActiveJobsScreen

        self.app.push_screen(ActiveJobsScreen())

    def action_goto_projects(self) -> None:
        """Navigate to Projects screen"""
        from awx_tui.screens.projects import ProjectsScreen

        self.app.push_screen(ProjectsScreen())

    def action_goto_templates(self) -> None:
        """Navigate to templates (key: 5)"""
        from awx_tui.screens.templates import TemplatesScreen

        self.app.pop_screen()
        self.app.push_screen(TemplatesScreen())

    def action_goto_inventories(self) -> None:
        """Navigate to inventories (key: 6)"""
        from awx_tui.screens.inventories import InventoriesScreen

        self.app.pop_screen()
        self.app.push_screen(InventoriesScreen())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on job table row - open job detail"""
        if event.data_table.id not in ("running-jobs-table", "recent-jobs-table"):
            return

        # Get job ID from first column
        try:
            job_id = int(event.data_table.get_row_at(event.cursor_row)[0])

            # Find job type from appropriate data source
            job_type = "job"  # Default
            if event.data_table.id == "running-jobs-table":
                jobs_data = self._running_jobs_data
            else:  # recent-jobs-table
                jobs_data = self._recent_jobs_data

            for job in jobs_data:
                if job.get("id") == job_id:
                    job_type = job.get("type", "job")
                    break

            from awx_tui.modals.job_detail import JobDetailModal

            self.app.push_screen(JobDetailModal(job_id, job_type))
        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to open job detail: {e}")
            self.notify("Error opening job detail", severity="error")
