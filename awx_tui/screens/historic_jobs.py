"""
AWX TUI - Historic Jobs Screen

Browse completed job history with full-width table and TopPanel.
"""

import re
from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

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
            f"{app_name} - Historic Jobs @ {self.instance_name} {status_emoji} {status_text} ({self.response_time})"
        )

        # Column 2: Running jobs + capacity bar
        bar = self._build_capacity_bar(self.capacity_pct)
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


class HistoricJobsScreen(Screen):
    """
    Historic Jobs screen - browse completed jobs

    Layout:
    - Header
    - TopPanel (rotating title, instance status, metrics, refresh time)
    - Full-width jobs table
    - Footer
    """

    CSS_PATH = "historic_jobs.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("escape", "back_to_dashboard_esc", "Back"),
        ("1", "back_to_dashboard", "Dashboard"),
        ("2", "goto_historic_jobs", "Historic Jobs"),
        ("3", "goto_active_jobs", "Active Jobs"),
        ("4", "goto_projects", "Projects"),
        ("5", "goto_templates", "Templates"),
        ("6", "goto_inventories", "Inventories"),
        ("m", "load_more", "Load More"),
        ("ctrl+r", "relaunch_job", "Relaunch"),
        ("ctrl+f", "focus_filter", "Filter"),
        ("ctrl+d", "debug_console", "Debug"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._refreshing = False
        self._refresh_start_time = None
        self._refresh_timer = None  # TopPanel metrics refresh timer
        self._table_refresh_timer = None  # Table refresh timer (optional)
        self._jobs_data = []  # Store all loaded jobs
        self._filtered_jobs_data = []  # Filtered jobs for display
        self._current_offset = 0  # Track pagination offset for load-more
        self._table_last_updated = None  # Track when jobs table was last refreshed

    def compose(self) -> ComposeResult:
        """Create historic jobs layout"""
        yield Header()
        yield TopPanel().add_class("top-panel")
        yield Input(
            placeholder="Filter: status:successful user:admin within:2d org:myorg project:deploy playbook:site.yml (Ctrl+F)",
            id="filter-input",
        )
        with Container(id="historic-jobs-container"):
            yield Static("HISTORIC JOBS (0)", id="jobs-header", classes="table-header")
            yield DataTable(id="jobs-table", cursor_type="row")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize tables and load data"""
        # Update title to show screen context
        self.app._update_title()

        # Set up Jobs table
        jobs_table = self.query_one("#jobs-table", DataTable)
        jobs_table.add_columns(
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

        # Focus the table by default (not the filter input)
        jobs_table.focus()

        # Trigger initial data load
        self.set_timer(0.1, lambda: self.run_worker(self._load_data()))

        # Start TopPanel metrics auto-refresh (always enabled, default 5 seconds)
        # This refreshes running jobs count and capacity, NOT the historic jobs table
        top_panel_refresh = self.app.app_config.preferences.get("historic_jobs_top_panel_refresh", 5)
        if top_panel_refresh > 0:
            self._refresh_timer = self.set_interval(top_panel_refresh, self.auto_refresh_top_panel)

        # Historic jobs table refresh (disabled by default - manual refresh only)
        # Press 'r' to manually refresh, or configure historic_jobs_table_refresh_interval > 0
        table_refresh = self.app.app_config.preferences.get("historic_jobs_table_refresh_interval", 0)
        if table_refresh > 0:
            self._table_refresh_timer = self.set_interval(table_refresh, self.auto_refresh_table)

    async def _load_data(self, append=False) -> None:
        """Load historic jobs data

        Args:
            append: If True, append to existing data. If False, replace all data.
        """
        # Skip if already refreshing (with timeout check)
        if self._refreshing:
            timeout = self.app.app_config.preferences.get("dashboard_refresh_timeout", 30)
            if self._refresh_start_time:
                elapsed = (datetime.now() - self._refresh_start_time).total_seconds()
                if elapsed > timeout:
                    self.app.log.warning(f"Refresh stuck for {elapsed}s (timeout: {timeout}s), resetting lock")
                    self._refreshing = False
                    self._refresh_start_time = None
                else:
                    return
            else:
                return

        self._refreshing = True
        self._refresh_start_time = datetime.now()
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    await self._fetch_and_display(client, append=append)
            else:
                await self._fetch_and_display(client, append=append)

        except Exception as e:
            import traceback

            self.app.log.error(f"Historic jobs load error: {e}\n{traceback.format_exc()}")
            self.app.notify(f"Error loading historic jobs: {e}", severity="error")
        finally:
            self._refreshing = False
            self._refresh_start_time = None

    async def _fetch_and_display(self, client, append=False) -> None:
        """Fetch and display all data

        Args:
            append: If True, append to existing jobs. If False, replace all jobs.
        """
        # Get configured page sizes
        initial_size = self.app.app_config.preferences.get("historic_jobs_initial_page_size", 50)
        load_more_size = self.app.app_config.preferences.get("historic_jobs_load_more_size", 50)

        # Determine page number and page_size based on mode
        if append:
            # Load more: calculate next page
            # AWX uses 1-based page numbers
            page_size = load_more_size
            # Calculate which page we need based on current data
            self._current_offset += 1  # Increment page number
            page = self._current_offset + 1  # Pages are 1-based
        else:
            # Fresh load: reset to page 1
            page_size = initial_size
            self._current_offset = 0
            page = 1
            self._jobs_data = []  # Clear existing data

        try:
            # Fetch historic jobs (completed only)
            jobs_resp = await client.get(
                "/api/v2/unified_jobs/",
                params={
                    "status__in": "successful,failed,error,canceled",
                    "page_size": page_size,
                    "page": page,
                    "order_by": "-finished",
                },
            )
        except Exception as e:
            raise Exception(f"Failed to fetch historic jobs: {e}") from e

        try:
            # Fetch running jobs for TopPanel metrics
            running_resp = await client.get(
                "/api/v2/unified_jobs/", params={"status__in": "pending,waiting,running", "page_size": 200}
            )
        except Exception as e:
            raise Exception(f"Failed to fetch running jobs: {e}") from e

        # Calculate metrics for TopPanel
        running_jobs = running_resp.get("results", [])
        running_jobs_count = len(running_jobs)

        # Try to fetch instances for capacity calculation (optional)
        capacity_pct = 0
        try:
            instances_resp = await client.get("/api/v2/instances/")
            instances = instances_resp.get("results", [])
            total_capacity = sum(inst.get("capacity", 0) for inst in instances)
            total_consumed = sum(inst.get("consumed_capacity", 0) for inst in instances)
            capacity_pct = int(((total_capacity - total_consumed) / total_capacity * 100) if total_capacity > 0 else 0)
        except Exception as e:
            # Log but don't fail - capacity metrics are nice-to-have
            self.app.log.warning(f"Failed to fetch instances for capacity: {e}")

        # Update TopPanel with current metrics
        try:
            top_panel = self.query_one(TopPanel)
            top_panel.update_metrics(running_jobs=running_jobs_count, capacity_pct=capacity_pct)
        except:
            pass  # TopPanel not found or not ready

        # Store fetched jobs
        new_jobs = jobs_resp.get("results", [])
        if append:
            self._jobs_data.extend(new_jobs)
        else:
            self._jobs_data = new_jobs

        # Update table last refreshed timestamp
        self._table_last_updated = datetime.now()

        # Re-apply current filter if any
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value:
            self._filter_jobs(filter_input.value)
        else:
            # No filter, show all jobs
            self._filtered_jobs_data = self._jobs_data.copy()
            self._update_jobs_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes"""
        if event.input.id == "filter-input":
            self._filter_jobs(event.value)

    def _filter_jobs(self, search_term: str) -> None:
        """Filter jobs based on search term with advanced filtering"""
        if not search_term.strip():
            # No filter, show all jobs
            self._filtered_jobs_data = self._jobs_data.copy()
            self._update_jobs_table()
            return

        search_term = search_term.lower().strip()
        filtered = []

        # Parse filter terms
        # Extract special filters: status:, user:, org:, project:, playbook:, template:, inventory:, ee:, type:, within:, extra_vars:
        filter_patterns = {
            "status": r"status:([^\s]+)",
            "user": r"user:([^\s]+)",
            "org": r"org:([^\s]+)",
            "project": r"project:([^\s]+)",
            "playbook": r"playbook:([^\s]+)",
            "template": r"template:([^\s]+)",
            "inventory": r"inventory:([^\s]+)",
            "ee": r"ee:([^\s]+)",
            "type": r"type:([^\s]+)",
            "within": r"within:([^\s]+)",
            "extra_vars": r"extra_vars:([^\s]+)",
        }

        # Extract negation filters (! prefix)
        negation_patterns = {
            "status": r"!status:([^\s]+)",
            "user": r"!user:([^\s]+)",
            "org": r"!org:([^\s]+)",
            "project": r"!project:([^\s]+)",
            "playbook": r"!playbook:([^\s]+)",
            "template": r"!template:([^\s]+)",
            "inventory": r"!inventory:([^\s]+)",
            "ee": r"!ee:([^\s]+)",
            "type": r"!type:([^\s]+)",
            "extra_vars": r"!extra_vars:([^\s]+)",
        }

        # Parse all filters
        filters = {}
        negations = {}

        for key, pattern in filter_patterns.items():
            match = re.search(pattern, search_term)
            if match:
                # Split by comma for OR logic
                filters[key] = [v.strip() for v in match.group(1).split(",")]

        for key, pattern in negation_patterns.items():
            match = re.search(pattern, search_term)
            if match:
                negations[key] = [v.strip() for v in match.group(1).split(",")]
                # Debug: Log what we matched
                self.app.log.info(f"Negation filter matched - {key}: {negations[key]}")

        # Parse within: time filter
        within_seconds = None
        if "within" in filters:
            time_spec = filters["within"][0]
            match = re.match(r"(\d+)([smhd])", time_spec)
            if match:
                amount, unit = int(match.group(1)), match.group(2)
                multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
                within_seconds = amount * multipliers.get(unit, 1)

        # Remove filter keywords from search term to get plain text search
        plain_search = search_term
        for pattern in list(filter_patterns.values()) + list(negation_patterns.values()):
            plain_search = re.sub(pattern, "", plain_search)
        plain_search = plain_search.strip()

        # Filter jobs
        for job in self._jobs_data:
            # Apply time filter first (most restrictive)
            if within_seconds:
                finished = job.get("finished")
                if finished:
                    try:
                        job_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                        cutoff_time = datetime.now(job_time.tzinfo) - timedelta(seconds=within_seconds)
                        if job_time < cutoff_time:
                            continue  # Skip jobs older than cutoff
                    except (ValueError, AttributeError):
                        continue  # Skip if can't parse time

            # Get job fields for filtering
            status = job.get("status", "").lower()
            user = job.get("summary_fields", {}).get("created_by", {}).get("username", "").lower()
            org = job.get("summary_fields", {}).get("organization", {}).get("name", "").lower()
            project = job.get("summary_fields", {}).get("project", {}).get("name", "").lower()
            playbook = job.get("playbook", "").lower()
            template = job.get("summary_fields", {}).get("job_template", {}).get("name", "").lower()
            inventory = job.get("summary_fields", {}).get("inventory", {}).get("name", "").lower()
            ee = job.get("summary_fields", {}).get("execution_environment", {}).get("name", "").lower()
            job_type = job.get("type", "").lower()
            job_name = job.get("name", "").lower()
            extra_vars = str(job.get("extra_vars", "")).lower()

            # Check inclusion filters (AND logic between different filter types)
            matches = True

            if "status" in filters:
                if not any(s in status for s in filters["status"]):
                    matches = False

            if "user" in filters:
                if not any(u in user for u in filters["user"]):
                    matches = False

            if "org" in filters:
                if not any(o in org for o in filters["org"]):
                    matches = False

            if "project" in filters:
                if not any(p in project for p in filters["project"]):
                    matches = False

            if "playbook" in filters:
                if not any(p in playbook for p in filters["playbook"]):
                    matches = False

            if "template" in filters:
                if not any(t in template for t in filters["template"]):
                    matches = False

            if "inventory" in filters:
                if not any(i in inventory for i in filters["inventory"]):
                    matches = False

            if "ee" in filters:
                if not any(e in ee for e in filters["ee"]):
                    matches = False

            if "type" in filters:
                if not any(t in job_type for t in filters["type"]):
                    matches = False

            if "extra_vars" in filters:
                if not any(e in extra_vars for e in filters["extra_vars"]):
                    matches = False

            # Check negation filters (exclude if any match)
            if "status" in negations:
                if any(s in status for s in negations["status"]):
                    self.app.log.info(
                        f"Excluding job {job.get('id')} with status '{status}' due to negation filter {negations['status']}"
                    )
                    matches = False

            if "user" in negations:
                if any(u in user for u in negations["user"]):
                    matches = False

            if "org" in negations:
                if any(o in org for o in negations["org"]):
                    matches = False

            if "project" in negations:
                if any(p in project for p in negations["project"]):
                    matches = False

            if "playbook" in negations:
                if any(p in playbook for p in negations["playbook"]):
                    matches = False

            if "template" in negations:
                if any(t in template for t in negations["template"]):
                    matches = False

            if "inventory" in negations:
                if any(i in inventory for i in negations["inventory"]):
                    matches = False

            if "ee" in negations:
                if any(e in ee for e in negations["ee"]):
                    matches = False

            if "type" in negations:
                if any(t in job_type for t in negations["type"]):
                    matches = False

            if "extra_vars" in negations:
                if any(e in extra_vars for e in negations["extra_vars"]):
                    matches = False

            # Plain text search (searches across multiple fields)
            if plain_search and matches:
                text_match = (
                    plain_search in job_name
                    or plain_search in user
                    or plain_search in org
                    or plain_search in project
                    or plain_search in playbook
                    or plain_search in template
                    or plain_search in inventory
                    or plain_search in ee
                )
                if not text_match:
                    matches = False

            if matches:
                filtered.append(job)

        self._filtered_jobs_data = filtered
        self._update_jobs_table()

    def _update_jobs_table(self) -> None:
        """Update historic jobs DataTable from self._filtered_jobs_data"""
        # Use filtered jobs data
        jobs = self._filtered_jobs_data if self._filtered_jobs_data else self._jobs_data

        # Build header with count (show X/Y when filtering)
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value and len(self._filtered_jobs_data) != len(self._jobs_data):
            # Filtering active - show filtered/total
            header_text = f"HISTORIC JOBS ({len(self._filtered_jobs_data)}/{len(self._jobs_data)})"
        else:
            # No filter or filter matches all - show just count
            header_text = f"HISTORIC JOBS ({len(jobs)})"

        if self._table_last_updated:
            header_text += f" - Last Updated: {self._table_last_updated.strftime('%H:%M:%S')}"

        self.query_one("#jobs-header").update(header_text)

        table = self.query_one("#jobs-table", DataTable)

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

            # Type-specific field display (like Templates screen)
            if job_type == "project_update":
                # Project updates: sync Git repos
                project_data = summary.get("project", {})
                project = project_data.get("name", "N/A")[:21]
                playbook = "GIT Sync"
                template = project  # Show project name in template column
                # Parse SCM URL to show Git host in inventory
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
                # Inventory updates: sync inventory from source
                source = job.get("source", "N/A")
                project = source[:21]  # Show source type in project
                playbook = "(inventory sync)"
                inventory_data = summary.get("inventory", {})
                inventory = inventory_data.get("name", "N/A")[:17]
                # Inventory source name in template column
                inv_source = summary.get("inventory_source", {})
                template = inv_source.get("name", "N/A")[:21]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            elif job_type == "workflow_job":
                # Workflow jobs: orchestrate multiple jobs
                project = "N/A"
                playbook = "(workflow)"
                workflow_template = summary.get("workflow_job_template", {})
                template = workflow_template.get("name", "N/A")[:21]
                inventory = "N/A"  # Workflows can use multiple inventories
                exec_env = "N/A"

            elif job_type == "system_job":
                # System jobs: AWX maintenance tasks
                project = "system"
                system_job_type = job.get("job_type", "N/A")
                playbook = system_job_type[:20]
                system_template = summary.get("system_job_template", {})
                template = system_template.get("name", "N/A")[:21]
                inventory = "AWX"
                exec_env = "N/A"

            elif job_type == "ad_hoc_command":
                # Ad hoc commands: one-off module execution
                project = "N/A"
                module_name = job.get("module_name", "N/A")
                playbook = module_name[:20]  # Show module (shell, command, ping, etc.)
                template = "N/A"
                inventory = summary.get("inventory", {}).get("name", "N/A")[:17]
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")[:21]

            else:
                # Regular job (playbook run)
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

    def auto_refresh_top_panel(self) -> None:
        """Auto-refresh TopPanel metrics only (silent, no table reload)"""
        # Only refresh if this screen is currently visible (on top of stack)
        if self.app.screen is self:
            self.run_worker(self._refresh_top_panel_metrics())

    def auto_refresh_table(self) -> None:
        """Auto-refresh table data (silent, resets to initial page size)"""
        # Only refresh if this screen is currently visible (on top of stack)
        if self.app.screen is self:
            self.run_worker(self._load_data(append=False))

    async def _refresh_top_panel_metrics(self) -> None:
        """Refresh only TopPanel metrics (running jobs, capacity)"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    # Fetch only running jobs and instances for metrics
                    running_resp = await client.get(
                        "/api/v2/unified_jobs/", params={"status__in": "pending,waiting,running", "page_size": 200}
                    )
                    instances_resp = await client.get("/api/v2/instances/")

                    # Calculate and update metrics
                    running_jobs_count = len(running_resp.get("results", []))
                    instances = instances_resp.get("results", [])
                    total_capacity = sum(inst.get("capacity", 0) for inst in instances)
                    total_consumed = sum(inst.get("consumed_capacity", 0) for inst in instances)
                    capacity_pct = int(
                        ((total_capacity - total_consumed) / total_capacity * 100) if total_capacity > 0 else 0
                    )

                    top_panel = self.query_one(TopPanel)
                    top_panel.update_metrics(running_jobs=running_jobs_count, capacity_pct=capacity_pct)
        except Exception as e:
            self.app.log.error(f"Failed to refresh TopPanel metrics: {e}")

    def action_refresh(self) -> None:
        """Manual refresh - resets table to initial page size"""
        initial_size = self.app.app_config.preferences.get("historic_jobs_initial_page_size", 50)
        self.app.notify(f"Refreshing... (resets to {initial_size} jobs)", timeout=2)
        self.run_worker(self._load_data(append=False))

    def action_load_more(self) -> None:
        """Load more jobs (appends to existing data)"""
        load_more_size = self.app.app_config.preferences.get("historic_jobs_load_more_size", 50)
        self.app.notify(f"Loading {load_more_size} more jobs...", timeout=2)
        self.run_worker(self._load_data(append=True))

    def action_relaunch_job(self) -> None:
        """Relaunch selected job (Ctrl+R)"""
        table = self.query_one("#jobs-table", DataTable)
        if not table.cursor_coordinate or table.row_count == 0:
            self.notify("No job selected", severity="warning")
            return

        try:
            cursor_row = table.cursor_coordinate[0]
            job_id = int(table.get_row_at(cursor_row)[0])

            # Find job data
            jobs_data = self._filtered_jobs_data if self._filtered_jobs_data else self._jobs_data
            job = None
            for j in jobs_data:
                if j.get("id") == job_id:
                    job = j
                    break

            if not job:
                self.notify("Job not found", severity="error")
                return

            # Check if job is relaunchable (must be completed)
            job_status = job.get("status", "")
            if job_status not in ("successful", "failed", "error", "canceled"):
                self.notify(
                    f"Cannot relaunch {job_status} job - only completed jobs can be relaunched",
                    severity="warning",
                    timeout=5,
                )
                return

            # Show confirmation modal
            self.run_worker(self._show_relaunch_confirmation(job))

        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to relaunch job: {e}")
            self.notify("Error relaunching job", severity="error")

    async def _show_relaunch_confirmation(self, job: dict) -> None:
        """Show relaunch confirmation modal and handle result"""
        from awx_tui.modals.confirm_relaunch import ConfirmRelaunchModal

        # Show confirmation modal
        relaunch_mode = await self.app.push_screen_wait(ConfirmRelaunchModal(job))

        if not relaunch_mode:
            self.notify("Relaunch cancelled", timeout=2)
            return

        # Relaunch the job
        job_id = job.get("id")
        job_name = job.get("name", "Unknown")

        if relaunch_mode == "all":
            self.notify(f"Relaunching job #{job_id} '{job_name}' (all hosts)...", timeout=3)
        else:  # "failed"
            self.notify(f"Relaunching job #{job_id} '{job_name}' (failed hosts only)...", timeout=3)

        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            # POST to job relaunch endpoint with mode
            relaunch_data = {"hosts": relaunch_mode}

            if isinstance(client, AWXClient):
                async with client:
                    response = await client.post(f"/api/v2/jobs/{job_id}/relaunch/", data=relaunch_data)
                    new_job_id = response.get("id")
                    new_job_name = response.get("name", "Unknown")
                    self.notify(
                        f"[green]✓[/green] Job #{new_job_id} '{new_job_name}' relaunched successfully!", timeout=5
                    )
            else:
                # Mock client
                response = await client.post(f"/api/v2/jobs/{job_id}/relaunch/", data=relaunch_data)
                new_job_id = response.get("id")
                new_job_name = response.get("name", "Unknown")
                self.notify(f"[green]✓[/green] Job #{new_job_id} '{new_job_name}' relaunched successfully!", timeout=5)

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to relaunch job: {e}\n{traceback.format_exc()}")
            self.notify(f"[red]✗[/red] Failed to relaunch job: {e}", severity="error", timeout=5)

    def action_back_to_dashboard_esc(self) -> None:
        """Return to dashboard screen (escape key)"""
        self.app.pop_screen()

    def action_back_to_dashboard(self) -> None:
        """Return to dashboard screen (1 key)"""
        self.app.pop_screen()

    def action_debug_console(self) -> None:
        """Open debug console"""
        self.app.action_toggle_debug()

    def action_focus_filter(self) -> None:
        """Focus the filter input"""
        self.query_one("#filter-input", Input).focus()

    def action_goto_historic_jobs(self) -> None:
        """Go to historic jobs (already here, do nothing)"""
        pass

    def action_goto_active_jobs(self) -> None:
        """Navigate to Active Jobs screen - replace current screen"""
        from awx_tui.screens.active_jobs import ActiveJobsScreen

        # Pop current screen, then push new screen (replace, don't stack)
        self.app.pop_screen()
        self.app.push_screen(ActiveJobsScreen())

    def action_goto_projects(self) -> None:
        """Navigate to Projects screen - replace current screen"""
        from awx_tui.screens.projects import ProjectsScreen

        # Pop current screen, then push new screen (replace, don't stack)
        self.app.pop_screen()
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
        if event.data_table.id != "jobs-table":
            return

        # Get job ID from first column
        try:
            job_id = int(event.data_table.get_row_at(event.cursor_row)[0])

            # Find job type from our data
            job_type = "job"  # Default
            jobs_data = self._filtered_jobs_data if self._filtered_jobs_data else self._jobs_data
            for job in jobs_data:
                if job.get("id") == job_id:
                    job_type = job.get("type", "job")
                    break

            from awx_tui.modals.job_detail import JobDetailModal

            self.app.push_screen(JobDetailModal(job_id, job_type))
        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to open job detail: {e}")
            self.notify("Error opening job detail", severity="error")

    def on_screen_suspend(self) -> None:
        """Stop auto-refresh timers when screen is hidden (navigated away)"""
        if self._refresh_timer:
            self._refresh_timer.stop()
        if self._table_refresh_timer:
            self._table_refresh_timer.stop()

    def on_screen_resume(self) -> None:
        """Resume auto-refresh timers when screen is shown again"""
        # Resume TopPanel metrics refresh (always enabled by default)
        top_panel_refresh = self.app.app_config.preferences.get("historic_jobs_top_panel_refresh", 5)
        if top_panel_refresh > 0:
            self._refresh_timer = self.set_interval(top_panel_refresh, self.auto_refresh_top_panel)

        # Resume table refresh (disabled by default)
        table_refresh = self.app.app_config.preferences.get("historic_jobs_table_refresh_interval", 0)
        if table_refresh > 0:
            self._table_refresh_timer = self.set_interval(table_refresh, self.auto_refresh_table)
