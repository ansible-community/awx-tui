"""
AWX TUI - Templates Screen

Browse and manage AWX job templates.
"""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from awx_tui.utils import format_playbook_path, format_time_ago


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
            yield Static("⏱ LOADING", classes="top-refresh")

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
            f"{app_name} - Templates @ {self.instance_name} {status_emoji} {status_text} ({self.response_time})"
        )

        # Column 2: Running jobs + capacity bar
        bar = self._build_capacity_bar(self.capacity_pct)
        jobs_text = f"🚀 {self.running_jobs_count} | {bar} {self.capacity_pct}%"

        # Column 3: Last refresh timestamp (24hr format)
        if self.last_refresh_time:
            refresh_text = f"⏱ {self.last_refresh_time.strftime('%H:%M:%S')}"
        else:
            refresh_text = "⏱ LOADING"

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


class TemplatesScreen(Screen):
    """
    Templates screen - browse and launch job templates

    Layout:
    - Header
    - TopPanel (rotating title, instance status, metrics, refresh time)
    - Filter input
    - Full-width templates table
    - Footer
    """

    CSS_PATH = "templates.tcss"

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
        ("ctrl+l", "launch_template", "Launch"),
        ("ctrl+f", "focus_filter", "Filter"),
        ("ctrl+d", "debug_console", "Debug"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._refreshing = False
        self._refresh_start_time = None
        self._refresh_timer = None  # TopPanel metrics refresh timer
        self._table_refresh_timer = None  # Table refresh timer
        self._templates_data = []  # Store all loaded templates
        self._filtered_templates_data = []  # Filtered templates for display
        self._table_last_updated = None  # Track when templates table was last refreshed

    def compose(self) -> ComposeResult:
        """Create templates layout"""
        yield Header()
        yield TopPanel().add_class("top-panel")
        yield Input(
            placeholder="Filter: name:deploy type:job,workflow,project,system org:myorg (Ctrl+F)", id="filter-input"
        )
        with Container(id="templates-container"):
            yield Static("TEMPLATES (0)", id="templates-header", classes="table-header")
            yield DataTable(id="templates-table", cursor_type="row")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize tables and load data"""
        # Update title to show screen context
        self.app._update_title()

        # Set up Templates table
        templates_table = self.query_one("#templates-table", DataTable)
        templates_table.add_columns(
            "ID", "", "", "Name", "Last Run", "Inventory", "Project", "Playbook", "Org", "Execution Environment"
        )

        # Focus the table by default (not the filter input)
        templates_table.focus()

        # Trigger initial data load
        self.set_timer(0.1, lambda: self.run_worker(self._load_data()))

        # Start TopPanel metrics auto-refresh (always enabled, default 5 seconds)
        top_panel_refresh = self.app.app_config.preferences.get("templates_top_panel_refresh", 5)
        if top_panel_refresh > 0:
            self._refresh_timer = self.set_interval(top_panel_refresh, self.auto_refresh_top_panel)

        # Templates table refresh (disabled by default - manual refresh only)
        # Press 'r' to manually refresh, or configure templates_table_refresh_interval > 0
        table_refresh = self.app.app_config.preferences.get("templates_table_refresh_interval", 0)
        if table_refresh > 0:
            self._table_refresh_timer = self.set_interval(table_refresh, self.auto_refresh_table)

    async def _load_data(self) -> None:
        """Load templates data"""
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
                    await self._fetch_and_display(client)
            else:
                await self._fetch_and_display(client)

        except Exception as e:
            import traceback

            self.app.log.error(f"Templates load error: {e}\n{traceback.format_exc()}")
            self.notify(f"Error loading templates: {e}", severity="error")
        finally:
            self._refreshing = False
            self._refresh_start_time = None

    async def _fetch_and_display(self, client) -> None:
        """Fetch templates data and display"""
        # Get configured page size (default 200)
        page_size = self.app.app_config.preferences.get("templates_page_size", 200)

        # Fetch unified templates (both job and workflow templates)
        templates_resp = await client.get("/api/v2/unified_job_templates/", params={"page_size": page_size})
        self._templates_data = templates_resp.get("results", [])
        self._filtered_templates_data = self._templates_data.copy()

        # Apply current filter if any
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value:
            self._apply_filter(filter_input.value)

        # Update table
        self._table_last_updated = datetime.now()
        self._update_templates_table()

        # Fetch capacity metrics for TopPanel
        ping_resp = await client.get("/api/v2/ping/")
        running_jobs = ping_resp.get("active_jobs", 0)
        capacity_pct = 100 - int(ping_resp.get("capacity", {}).get("percent_capacity_remaining", 0))

        # Update top panel
        top_panel = self.query_one(TopPanel)
        top_panel.update_metrics(running_jobs=running_jobs, capacity_pct=capacity_pct)

    def _update_templates_table(self) -> None:
        """Update templates DataTable from self._filtered_templates_data"""
        # Use filtered templates data
        templates = self._filtered_templates_data if self._filtered_templates_data else self._templates_data

        # Sort templates by multiple criteria
        # 1. Type priority (job > workflow > project > inventory > system)
        # 2. Organization
        # 3. Project name
        # 4. Playbook name
        # 5. Inventory name
        # 6. Last run (most recent first, never-run to end)
        type_priority = {
            "job_template": 1,
            "workflow_job_template": 2,
            "project": 3,
            "inventory_source": 4,
            "system_job_template": 5,
        }

        def sort_key(t):
            summary = t.get("summary_fields", {})
            last_run = t.get("last_job_run", "")

            # For last run: invert timestamp so most recent sorts first
            # Templates without runs go to end
            if last_run:
                # Invert ISO timestamp by subtracting each digit from 9
                # '2025-11-26' becomes '7974-88-73' which sorts in reverse
                try:
                    inverted = "".join(str(9 - int(c)) if c.isdigit() else c for c in last_run)
                    last_run_sort = f"0{inverted}"  # Prefix 0 so it sorts before no-run (1)
                except:
                    last_run_sort = f"0{last_run}"
            else:
                last_run_sort = "1"  # No run goes to end

            return (
                type_priority.get(t.get("type", "job_template"), 99),
                summary.get("organization", {}).get("name", "ZZZ").lower(),
                summary.get("project", {}).get("name", "ZZZ").lower(),
                t.get("playbook", "ZZZ").lower(),
                summary.get("inventory", {}).get("name", "ZZZ").lower(),
                last_run_sort,
            )

        templates = sorted(templates, key=sort_key)

        # Build header with count (show X/Y when filtering)
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.value and len(self._filtered_templates_data) != len(self._templates_data):
            # Filtering active - show filtered/total
            header_text = f"TEMPLATES ({len(self._filtered_templates_data)}/{len(self._templates_data)})"
        else:
            # No filter or filter matches all - show just count
            header_text = f"TEMPLATES ({len(templates)})"

        if self._table_last_updated:
            header_text += f" - Last Updated: {self._table_last_updated.strftime('%H:%M:%S')}"

        self.query_one("#templates-header").update(header_text)

        table = self.query_one("#templates-table", DataTable)

        # Save current template ID (from first column) to restore position
        selected_template_id = None
        cursor_row = 0
        if table.cursor_coordinate and table.row_count > 0:
            cursor_row = table.cursor_coordinate[0]
            try:
                selected_template_id = table.get_row_at(cursor_row)[0]  # First column is template ID
            except:
                pass

        table.clear()

        new_cursor_row = 0
        for idx, template in enumerate(templates):
            tid = str(template.get("id", 0))
            name = template.get("name", "Unknown")[:40]
            template_type = template.get("type", "job_template")

            # Type emoji
            type_emoji = {
                "job_template": "🚀",
                "workflow_job_template": "🔀",
                "project": "📦",
                "system_job_template": "🔧",
                "inventory_source": "📥",
            }.get(template_type, "❓")

            # Get summary fields
            summary = template.get("summary_fields", {})
            org = summary.get("organization", {}).get("name", "N/A")[:15]

            # Check for prompt-on-launch flags
            ask_inventory = template.get("ask_inventory_on_launch", False)
            ask_ee = template.get("ask_execution_environment_on_launch", False)

            # Handle different template types
            if template_type == "workflow_job_template":
                # Workflows don't have inventory/project/playbook
                inventory = "N/A"
                project = "N/A"
                playbook = "(workflow)"
                exec_env = "N/A"
            elif template_type == "project":
                # Projects: split SCM URL into domain (inventory) and path (project)
                scm_url = template.get("scm_url", "N/A")
                if scm_url != "N/A":
                    # Parse URL: https://github.com/example/repo.git
                    # -> inventory: github.com, project: /example/repo.git
                    try:
                        from urllib.parse import urlparse

                        parsed = urlparse(scm_url)
                        inventory = parsed.netloc[:20] if parsed.netloc else "N/A"
                        project = parsed.path[:25] if parsed.path else "N/A"
                    except:
                        inventory = "N/A"
                        project = scm_url[:25]
                else:
                    inventory = "N/A"
                    project = "N/A"
                playbook = "GIT Project Sync"
                exec_env = summary.get("default_environment", {}).get("name", "N/A")[:20]
            elif template_type == "system_job_template":
                # System jobs: inventory=AWX, project=system, playbook=job type
                inventory = "AWX"
                project = "system"
                job_type = template.get("job_type", "N/A")
                playbook = job_type[:30] if job_type != "N/A" else "N/A"
                exec_env = "N/A"
            elif template_type == "inventory_source":
                # Inventory sources show source type
                inventory = summary.get("inventory", {}).get("name", "N/A")[:20]
                project = "N/A"
                source = template.get("source", "N/A")
                playbook = f"(source: {source})"[:30]
                exec_env = "N/A"
            else:
                # Job templates have all fields
                inventory = summary.get("inventory", {}).get("name", "N/A")[:20]
                project = summary.get("project", {}).get("name", "N/A")
                # Format playbook: show as much of the path as possible from right to left
                playbook_raw = template.get("playbook", "N/A")
                playbook = format_playbook_path(playbook_raw, max_length=30)
                exec_env = summary.get("execution_environment", {}).get("name", "N/A")

            # Handle exec env: N/A means use project default
            if exec_env == "N/A":
                exec_env = "PROJECT DEFAULT"

            # Override with PROMPT if ask_*_on_launch is true
            # (prompt on launch means user MUST provide value, regardless of default)
            if ask_inventory:
                inventory = "PROMPT"
            if ask_ee:
                exec_env = "PROMPT"

            # Format last run timestamp and status
            last_job = summary.get("last_job", {})
            last_run_str = "Never"
            status_emoji = "❓"  # Default for templates that have never run
            if last_job:
                # Get last job status
                last_status = last_job.get("status", "unknown")
                status_emoji = {
                    "successful": "[green]✓[/green]",
                    "failed": "[red]✗[/red]",
                    "running": "🏃",
                    "error": "❗",
                    "canceled": "⚠",
                }.get(last_status, "❓")

                # Get last run time
                last_finished = last_job.get("finished")
                if last_finished:
                    last_run_str = format_time_ago(last_finished)

            # Track if this is the previously selected template
            if selected_template_id and tid == selected_template_id:
                new_cursor_row = idx

            table.add_row(
                tid, type_emoji, status_emoji, name, last_run_str, inventory, project, playbook, org, exec_env
            )

        # Restore cursor position
        if table.row_count > 0:
            if new_cursor_row < table.row_count:
                table.cursor_coordinate = (new_cursor_row, 0)

    def _apply_filter(self, filter_text: str) -> None:
        """Apply filter to templates list"""
        if not filter_text.strip():
            self._filtered_templates_data = self._templates_data.copy()
            return

        # Parse filter tokens
        tokens = filter_text.lower().split()
        filtered = []

        for template in self._templates_data:
            match = True

            # Extract searchable fields
            tid = str(template.get("id", ""))
            name = template.get("name", "").lower()
            template_type = template.get("type", "").lower()
            playbook = template.get("playbook", "").lower()

            summary = template.get("summary_fields", {})
            inventory = summary.get("inventory", {}).get("name", "").lower()
            project = summary.get("project", {}).get("name", "").lower()
            org = summary.get("organization", {}).get("name", "").lower()
            exec_env = summary.get("execution_environment", {}).get("name", "").lower()

            # Normalize template type for filtering (job/workflow/project/system/inventory)
            if template_type == "job_template":
                type_short = "job"
            elif template_type == "workflow_job_template":
                type_short = "workflow"
            elif template_type == "project":
                type_short = "project"
            elif template_type == "system_job_template":
                type_short = "system"
            elif template_type == "inventory_source":
                type_short = "inventory"
            else:
                type_short = template_type

            # Check each filter token
            for token in tokens:
                token_match = False

                # Field-specific filters
                if ":" in token:
                    field, value = token.split(":", 1)
                    # Handle comma-separated values (OR logic)
                    values = [v.strip() for v in value.split(",")]

                    if field == "name":
                        token_match = any(v in name for v in values)
                    elif field == "type":
                        token_match = any(v in type_short or v in template_type for v in values)
                    elif field == "inventory":
                        token_match = any(v in inventory for v in values)
                    elif field == "project":
                        token_match = any(v in project for v in values)
                    elif field == "playbook":
                        token_match = any(v in playbook for v in values)
                    elif field == "org":
                        token_match = any(v in org for v in values)
                    elif field == "ee":
                        token_match = any(v in exec_env for v in values)
                    elif field == "id":
                        token_match = any(v in tid for v in values)
                else:
                    # Plain text search across all fields
                    if (
                        token in name
                        or token in inventory
                        or token in project
                        or token in playbook
                        or token in org
                        or token in exec_env
                        or token in tid
                        or token in type_short
                    ):
                        token_match = True

                if not token_match:
                    match = False
                    break

            if match:
                filtered.append(template)

        self._filtered_templates_data = filtered

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes"""
        if event.input.id == "filter-input":
            self._apply_filter(event.value)
            self._update_templates_table()

    def auto_refresh_top_panel(self) -> None:
        """Auto-refresh top panel metrics only (running jobs, capacity)"""
        self.run_worker(self._refresh_top_panel_only())

    async def _refresh_top_panel_only(self) -> None:
        """Refresh only top panel metrics, not the templates table"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    ping_resp = await client.get("/api/v2/ping/")
            else:
                ping_resp = await client.get("/api/v2/ping/")

            running_jobs = ping_resp.get("active_jobs", 0)
            capacity_pct = 100 - int(ping_resp.get("capacity", {}).get("percent_capacity_remaining", 0))

            top_panel = self.query_one(TopPanel)
            top_panel.update_metrics(running_jobs=running_jobs, capacity_pct=capacity_pct)

        except Exception as e:
            self.app.log.error(f"Top panel refresh error: {e}")

    def auto_refresh_table(self) -> None:
        """Auto-refresh templates table"""
        self.run_worker(self._load_data())

    def action_refresh(self) -> None:
        """Manual refresh"""
        self.run_worker(self._load_data())
        self.notify("Refreshing templates...", timeout=1)

    def action_focus_filter(self) -> None:
        """Focus the filter input"""
        filter_input = self.query_one("#filter-input", Input)
        filter_input.focus()

    def action_launch_template(self) -> None:
        """Launch selected template (Ctrl+L)"""
        table = self.query_one("#templates-table", DataTable)
        if not table.cursor_coordinate or table.row_count == 0:
            self.notify("No template selected", severity="warning")
            return

        try:
            cursor_row = table.cursor_coordinate[0]
            template_id = int(table.get_row_at(cursor_row)[0])

            # Find template data
            templates_data = self._filtered_templates_data if self._filtered_templates_data else self._templates_data
            template = None
            for t in templates_data:
                if t.get("id") == template_id:
                    template = t
                    break

            if not template:
                self.notify("Template not found", severity="error")
                return

            # Check if template is launchable
            template_type = template.get("type", "")

            # Only job templates and workflow templates can be launched
            if template_type not in ("job_template", "workflow_job_template"):
                type_names = {
                    "project": "project",
                    "system_job_template": "system job",
                    "inventory_source": "inventory source",
                }
                type_display = type_names.get(template_type, template_type)
                self.notify(
                    f"Cannot launch {type_display} - only job and workflow templates can be launched",
                    severity="warning",
                    timeout=5,
                )
                return

            # Template is launchable - show confirmation or prompt modal
            self.run_worker(self._show_launch_confirmation(template))

        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to launch template: {e}")
            self.notify("Error launching template", severity="error")

    async def _show_launch_confirmation(self, template: dict) -> None:
        """Show launch confirmation (or prompt-on-launch) modal and launch template"""
        from awx_tui.client import AWXClient
        from awx_tui.modals.confirm_launch import ConfirmLaunchModal
        from awx_tui.modals.launch_prompt import LaunchPromptModal
        from awx_tui.utils.launch_prompts import get_active_prompt_fields

        template_name = template.get("name", "Unknown")
        template_type = template.get("type", "job_template")
        is_workflow = template_type == "workflow_job_template"
        template_id = template.get("id")
        endpoint_base = (
            f"/api/v2/workflow_job_templates/{template_id}" if is_workflow else f"/api/v2/job_templates/{template_id}"
        )
        launch_endpoint = f"{endpoint_base}/launch/"
        launch_label = "workflow template" if is_workflow else "job template"
        result_label = "Workflow Job" if is_workflow else "Job"

        active_prompts = get_active_prompt_fields(template)
        launch_payload: dict = {}

        if active_prompts:
            # Fetch launch metadata, survey spec (if enabled), and inventories (if prompted)
            launch_info: dict = {}
            survey_spec: dict | None = None
            inventories: list = []

            try:
                client = self.app.instance_manager.get_current_client()

                async def _fetch_prompt_metadata(c):
                    nonlocal launch_info, survey_spec, inventories
                    try:
                        launch_info = await c.get(launch_endpoint)
                    except Exception as err:
                        self.app.log.warning(f"Could not fetch launch info from {launch_endpoint}: {err}")

                    survey_enabled = launch_info.get("survey_enabled", template.get("survey_enabled", False))
                    if survey_enabled:
                        try:
                            survey_spec = await c.get(f"{endpoint_base}/survey_spec/")
                        except Exception as err:
                            self.app.log.warning(f"Could not fetch survey_spec for {endpoint_base}: {err}")

                    ask_inv = launch_info.get("ask_inventory_on_launch", template.get("ask_inventory_on_launch", False))
                    if ask_inv:
                        try:
                            inv_resp = await c.get("/api/v2/inventories/", params={"page_size": 200})
                            inventories = inv_resp.get("results", [])
                        except Exception as err:
                            self.app.log.warning(f"Could not fetch inventories for launch prompt: {err}")

                if isinstance(client, AWXClient):
                    async with client:
                        await _fetch_prompt_metadata(client)
                else:
                    await _fetch_prompt_metadata(client)
            except Exception as e:
                self.app.log.error(f"Error preparing launch prompts: {e}")

            result = await self.app.push_screen_wait(
                LaunchPromptModal(
                    template_data=template,
                    launch_info=launch_info,
                    survey_spec=survey_spec,
                    inventories=inventories,
                )
            )
            if result is None:
                self.notify("Launch cancelled", timeout=2)
                return
            launch_payload = result
        else:
            # No prompts required - show simple confirmation modal
            confirmed = await self.app.push_screen_wait(ConfirmLaunchModal(template))
            if not confirmed:
                self.notify("Launch cancelled", timeout=2)
                return

        # Launch the job or workflow
        self.notify(f"Launching {launch_label} '{template_name}'...", timeout=3)

        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            if isinstance(client, AWXClient):
                async with client:
                    response = await client.post(launch_endpoint, data=launch_payload)
            else:
                # Mock client
                response = await client.post(launch_endpoint, data=launch_payload)

            job_id = response.get("id")
            job_name = response.get("name", "Unknown")

            self.notify(f"[green]✓[/green] {result_label} #{job_id} '{job_name}' launched successfully!", timeout=5)

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to launch {launch_label}: {e}\n{traceback.format_exc()}")
            self.notify(f"[red]✗[/red] Failed to launch {launch_label}: {e}", severity="error", timeout=5)

    # Navigation actions
    def action_back_to_dashboard(self) -> None:
        """Navigate to dashboard (key: 1)"""
        dashboard_class = self.app.get_dashboard_class()
        self.app.pop_screen()
        self.app.push_screen(dashboard_class())

    def action_back_to_dashboard_esc(self) -> None:
        """Navigate to dashboard (ESC)"""
        dashboard_class = self.app.get_dashboard_class()
        self.app.pop_screen()
        self.app.push_screen(dashboard_class())

    def action_goto_historic_jobs(self) -> None:
        """Navigate to historic jobs (key: 2)"""
        from awx_tui.screens.historic_jobs import HistoricJobsScreen

        self.app.pop_screen()
        self.app.push_screen(HistoricJobsScreen())

    def action_goto_active_jobs(self) -> None:
        """Navigate to active jobs (key: 3)"""
        from awx_tui.screens.active_jobs import ActiveJobsScreen

        self.app.pop_screen()
        self.app.push_screen(ActiveJobsScreen())

    def action_goto_projects(self) -> None:
        """Navigate to projects (key: 4)"""
        from awx_tui.screens.projects import ProjectsScreen

        self.app.pop_screen()
        self.app.push_screen(ProjectsScreen())

    def action_goto_templates(self) -> None:
        """Navigate to templates (key: 5) - Already here"""
        pass

    def action_goto_inventories(self) -> None:
        """Navigate to inventories (key: 6)"""
        from awx_tui.screens.inventories import InventoriesScreen

        self.app.pop_screen()
        self.app.push_screen(InventoriesScreen())

    def action_debug_console(self) -> None:
        """Open debug console (Ctrl+D)"""
        self.app.push_screen("debug_console")

    def on_screen_resume(self) -> None:
        """Trigger immediate refresh when screen is shown again (e.g., after closing update screen)"""
        # Refresh data to show any changes made in update screen
        self.run_worker(self._load_data())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle template selection - open update screen for job templates"""
        table = self.query_one("#templates-table", DataTable)
        if table.row_count == 0:
            return

        try:
            row_index = event.cursor_row
            template_id = int(table.get_row_at(row_index)[0])

            # Find template data from filtered list
            templates_data = self._filtered_templates_data if self._filtered_templates_data else self._templates_data
            template = None
            for t in templates_data:
                if t.get("id") == template_id:
                    template = t
                    break

            if not template:
                self.notify("Template not found", severity="error")
                return

            # Check template type - only support job templates for updates
            template_type = template.get("type", "unknown")
            template_name = template.get("name", "Unknown")

            if template_type == "job_template":
                # Check for prompt-on-launch fields - cannot edit templates with prompts
                prompt_fields = [
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
                ]

                has_prompts = any(template.get(field, False) for field in prompt_fields)

                if has_prompts:
                    self.notify(
                        f"Cannot edit '{template_name}' - template has prompt-on-launch fields enabled",
                        severity="warning",
                        timeout=5,
                    )
                    return

                # Open update job template screen
                from awx_tui.screens.update_job_template import UpdateJobTemplateScreen

                self.app.push_screen(UpdateJobTemplateScreen(template_id))
            elif template_type == "workflow_job_template":
                # Open read-only workflow structure preview modal
                self.run_worker(self._show_workflow_structure(template))
            else:
                # Show warning for unsupported template types
                self.notify(f"Template updates for '{template_type}' not implemented", severity="warning", timeout=3)

        except (ValueError, IndexError) as e:
            self.app.log.error(f"Failed to select template: {e}")

    async def _show_workflow_structure(self, template: dict) -> None:
        """Show workflow template structure preview modal; launch if requested"""
        from awx_tui.modals.workflow_structure import WorkflowStructureModal

        result = await self.app.push_screen_wait(WorkflowStructureModal(template))
        if result == "launch":
            await self._show_launch_confirmation(template)
