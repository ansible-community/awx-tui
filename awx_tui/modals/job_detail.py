"""
AWX TUI - Job Detail Modal

Displays detailed job information with live output tailing.

Layout:
- Top 3-4 lines: Job info header (full width)
- Tabbed content area: "Job Events" and "STDOUT" tabs
"""

from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, RichLog, Static, TabbedContent, TabPane


class JobInfoHeader(Static):
    """Compact job info header (3-4 lines across full width)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.job_data = None

    def update_job_info(self, job_data: dict, last_updated: datetime = None):
        """Update displayed job information

        Args:
            job_data: Job data from API
            last_updated: Timestamp of last update (only shown for running jobs)
        """
        self.job_data = job_data

        if not job_data:
            self.update("No job data available")
            return

        # Extract job details
        job_id = job_data.get("id", "Unknown")
        name = job_data.get("name", "Unknown")
        status = job_data.get("status", "unknown")
        job_type = job_data.get("type", "job")

        # Get summary fields
        summary = job_data.get("summary_fields", {})
        user = summary.get("created_by", {}).get("username", "N/A")
        project = summary.get("project", {}).get("name", "N/A")
        template = summary.get("job_template", {}).get("name", "N/A")
        inventory = summary.get("inventory", {}).get("name", "N/A")

        playbook = job_data.get("playbook", "N/A")
        launch_type = job_data.get("launch_type", "manual")

        # Execution parameters
        forks = job_data.get("forks", "N/A")
        job_slice_count = job_data.get("job_slice_count", "N/A")

        # Timestamps
        started = job_data.get("started")
        finished = job_data.get("finished")
        elapsed = job_data.get("elapsed", 0)

        # Format timestamps
        started_str = "Not started"
        if started:
            try:
                started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                started_str = started_dt.strftime("%H:%M:%S")
            except:
                started_str = started

        finished_str = "Running..."
        if finished:
            try:
                finished_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                finished_str = finished_dt.strftime("%H:%M:%S")
            except:
                finished_str = finished

        # Duration/Elapsed
        duration_str = f"{elapsed:.1f}s" if elapsed else "N/A"

        # Status emoji
        status_emoji = {
            "successful": "[green]✓[/green]",
            "failed": "[red]✗[/red]",
            "running": "🏃",
            "pending": "⏳",
            "waiting": "⏳",
            "canceled": "⚠",
            "error": "‼",
        }.get(status, "❓")

        # Job type emoji
        type_emoji = {
            "job": "🚀",
            "project_update": "🔄",
            "inventory_update": "📥",
            "workflow_job": "🔗",
            "system_job": "🔧",
            "ad_hoc_command": "⚡",
        }.get(job_type, "❓")

        # Launch type emoji
        launch_emoji = {"manual": "👤", "scheduled": "📅", "relaunch": "🔃", "workflow": "🔗"}.get(launch_type, "❓")

        # Status with Last Updated for running jobs
        status_text = f"{status_emoji} {status.upper()}"
        if status in ("running", "pending", "waiting") and last_updated:
            status_text += f" (Updated: {last_updated.strftime('%H:%M:%S')})"

        # Build compact 4-line header
        info_text = f"""Job #{job_id} {type_emoji} {name[:60]} | {status_text} | Launched via: {launch_emoji} {launch_type.title()}
👤 {user} | 📦 {project[:30]} | 🎯 {template[:30]} | 📋 {inventory[:25]}
📄 {playbook[:40]} | 🧵 {forks} | 🍕 {job_slice_count} | ⏱ {started_str} → 🏁 {finished_str} | ⌛ {duration_str}"""

        self.update(info_text)


class JobDetailModal(ModalScreen):
    """
    Job detail modal with compact header and tabbed content

    Layout:
    - Top 3-4 lines: Job info header (full width)
    - Tabbed content area: "Job Events" and "STDOUT" tabs
    """

    CSS = """
    JobDetailModal {
        align: center middle;
    }

    #job-detail-container {
        width: 95%;
        height: 90%;
        border: solid $primary;
        background: $surface;
    }

    #job-info-header {
        dock: top;
        height: auto;
        background: $boost;
        padding: 1;
        border-bottom: solid $primary;
    }

    #job-content-tabs {
        height: 1fr;
    }

    #job-events-table {
        height: 1fr;
    }

    #job-stdout-log {
        height: 1fr;
        background: $surface;
        border: none;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Quit"),
        Binding("f", "toggle_follow", "Toggle Follow", show=True),
        # Binding("w", "toggle_wrap", "Toggle Wrap", show=True),  # Disabled - widget doesn't support dynamic wrap toggle
        Binding("r", "refresh", "Refresh"),
        Binding("f5", "refresh", "Refresh"),
        Binding("ctrl+k", "cancel_job", "Cancel", show=True),
    ]

    def __init__(self, job_id: int, job_type: str = "job", **kwargs):
        super().__init__(**kwargs)
        self.job_id = job_id
        self.job_type = job_type
        self.job_data = None
        self._auto_follow = True  # Auto-scroll to bottom by default
        self._refresh_timer = None  # Timer object for one-shot refresh scheduling
        self._refresh_interval = 2  # Refresh interval in seconds
        self._refresh_enabled = True  # Flag to stop refresh loop
        self._last_event_counter = 0  # Track last seen event for incremental fetching
        self._refreshing = False
        self._last_updated = None  # Track when job data was last refreshed

        # Map job type to API endpoint
        self._job_endpoint_map = {
            "job": "/api/v2/jobs",
            "project_update": "/api/v2/project_updates",
            "inventory_update": "/api/v2/inventory_updates",
            "workflow_job": "/api/v2/workflow_jobs",
            "system_job": "/api/v2/system_jobs",
            "ad_hoc_command": "/api/v2/ad_hoc_commands",
        }

    def compose(self) -> ComposeResult:
        """Create job detail layout"""
        with Vertical(id="job-detail-container"):
            yield Header()

            # Top: Compact job info header
            yield JobInfoHeader(id="job-info-header")

            # Bottom: Tabbed content area
            with TabbedContent(id="job-content-tabs"):
                with TabPane("STDOUT", id="tab-stdout"):
                    # Configurable word wrap for STDOUT (default: True for better readability)
                    wrap_stdout = self.app.app_config.preferences.get("job_detail_stdout_wrap", True)
                    yield RichLog(id="job-stdout-log", wrap=wrap_stdout, highlight=False, markup=False)

                with TabPane("Job Events", id="tab-events"):
                    events_table = DataTable(id="job-events-table", show_cursor=False)
                    events_table.add_columns("Counter", "Event", "Play", "Role", "Task", "Host", "Duration", "Status")
                    yield events_table

            yield Footer()

    async def on_mount(self) -> None:
        """Initialize job detail view"""
        self.title = f"Job Detail - #{self.job_id}"

        # Get refresh interval from config
        refresh_interval = self.app.app_config.preferences.get("job_detail_refresh_active", 2)
        if refresh_interval > 0:
            self._refresh_interval = refresh_interval

        # Initial data load - timer will be started if job is active
        self.run_worker(self._load_job_data())

    async def _load_job_data(self, incremental=False) -> None:
        """Load job data and events"""
        if self._refreshing:
            return

        self._refreshing = True
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    await self._fetch_and_display(client, incremental=incremental)
            else:
                await self._fetch_and_display(client, incremental=incremental)

        except Exception as e:
            import traceback

            self.app.log.error(f"Job detail load error: {e}\n{traceback.format_exc()}")
            self.notify(f"Error loading job: {e}", severity="error")
        finally:
            self._refreshing = False

    async def _fetch_and_display(self, client, incremental=False) -> None:
        """Fetch job data and display"""
        # Get correct endpoint for this job type
        endpoint_base = self._job_endpoint_map.get(self.job_type, "/api/v2/jobs")

        # Fetch job details (always get fresh status)
        job_resp = await client.get(f"{endpoint_base}/{self.job_id}/")
        self.job_data = job_resp
        self._last_updated = datetime.now()

        # Update job info header with last updated timestamp
        job_info_header = self.query_one("#job-info-header", JobInfoHeader)
        job_info_header.update_job_info(self.job_data, last_updated=self._last_updated)
        self.app.log.debug(f"Updated job info header for {self.job_id} (status: {self.job_data.get('status')})")

        # On initial load, start auto-refresh timer if job is active
        if not incremental and self._refresh_timer is None and self._refresh_interval > 0:
            status = self.job_data.get("status", "").lower()
            if status in ("pending", "waiting", "running"):
                self._schedule_next_refresh()
                self.app.log.debug(f"Started auto-refresh timer for active job {self.job_id} (status: {status})")

        # Fetch job events (available for job and project_update types)
        # Workflow jobs use workflow_nodes instead, so skip those
        if self.job_type in ("job", "project_update", "inventory_update", "system_job"):
            try:
                # Build events endpoint based on job type
                # job uses /job_events/, others use /events/
                if self.job_type == "job":
                    events_endpoint = f"{endpoint_base}/{self.job_id}/job_events/"
                else:
                    events_endpoint = f"{endpoint_base}/{self.job_id}/events/"

                if incremental and self._last_event_counter > 0:
                    # Fetch only new events
                    events_resp = await client.get(
                        events_endpoint, params={"counter__gt": self._last_event_counter, "order_by": "counter"}
                    )
                else:
                    # Fetch all events (initial load)
                    events_resp = await client.get(events_endpoint, params={"page_size": 200, "order_by": "counter"})

                events = events_resp.get("results", [])

                # Update events table
                if events:
                    self.app.log.debug(
                        f"Fetched {len(events)} new events for job {self.job_id} (incremental: {incremental})"
                    )
                    self._update_events_table(events, append=incremental)
                else:
                    self.app.log.debug(f"No new events for job {self.job_id}")

                # Update stdout
                self._update_stdout(events, append=incremental)

                # Update last seen counter
                if events:
                    max_counter = max(event.get("counter", 0) for event in events)
                    if max_counter > self._last_event_counter:
                        self._last_event_counter = max_counter
            except Exception as e:
                # If events endpoint doesn't exist for this job type, show message
                self.app.log.warning(f"Job events not available for {self.job_type}: {e}")
                table = self.query_one("#job-events-table", DataTable)
                table.clear()
                stdout_log = self.query_one("#job-stdout-log", RichLog)
                stdout_log.clear()
                stdout_log.write(f"[STDOUT not available for {self.job_type}]")
        else:
            # For workflow_job and other types without events
            table = self.query_one("#job-events-table", DataTable)
            table.clear()
            stdout_log = self.query_one("#job-stdout-log", RichLog)
            stdout_log.clear()
            if self.job_type == "workflow_job":
                stdout_log.write("[Workflow jobs display workflow nodes, not job events. Feature coming soon.]")
            else:
                stdout_log.write(f"[STDOUT not available for {self.job_type}]")

    def _update_events_table(self, events: list, append=False) -> None:
        """Update job events table"""
        table = self.query_one("#job-events-table", DataTable)

        if not append:
            table.clear()

        for event in events:
            counter = event.get("counter", 0)
            event_type = event.get("event", "unknown")
            play = event.get("play", "N/A")
            role = event.get("role", "N/A")
            task = event.get("task", "N/A")
            host = event.get("host_name", "N/A")
            failed = event.get("failed", False)
            changed = event.get("changed", False)

            # Duration (from event_data if available)
            event_data = event.get("event_data", {})
            duration = event_data.get("duration")
            if duration is not None:
                duration_str = f"{duration:.2f}s"
            else:
                duration_str = ""

            # Status emoji only (no text)
            if failed:
                status_emoji = "[red]✗[/red]"
            elif changed:
                status_emoji = "🔀"
            elif event_type == "runner_on_skipped":
                status_emoji = "⏭"
            else:
                status_emoji = "[green]✓[/green]"

            table.add_row(
                str(counter),
                event_type,
                play if play != "N/A" else "N/A",
                role[:20] if role != "N/A" else "N/A",
                task[:25] if task != "N/A" else "N/A",
                host[:15] if host != "N/A" else "N/A",
                duration_str,
                status_emoji,
            )

        # Auto-scroll to bottom if following
        if self._auto_follow and table.row_count > 0:
            table.cursor_coordinate = (table.row_count - 1, 0)

    def _update_stdout(self, events: list, append=False) -> None:
        """Update stdout log"""
        stdout_log = self.query_one("#job-stdout-log", RichLog)

        if not append:
            stdout_log.clear()

        for event in events:
            stdout = event.get("stdout", "")
            if stdout:
                # Convert ANSI codes to Rich Text for proper color rendering
                rich_text = Text.from_ansi(stdout)
                stdout_log.write(rich_text)

    def _schedule_next_refresh(self) -> None:
        """Schedule the next auto-refresh using set_timer (recursive pattern)"""
        if self._refresh_enabled and self._refresh_interval > 0:
            self._refresh_timer = self.set_timer(self._refresh_interval, self._timer_callback)

    def _timer_callback(self) -> None:
        """Timer callback - auto-refresh job data"""
        # If no job data yet, wait for initial load and schedule next attempt
        if not self.job_data:
            self._schedule_next_refresh()
            return

        status = self.job_data.get("status")
        status_lower = status.lower() if status else "unknown"

        # Only refresh if job is still active (case-insensitive check)
        if status_lower in ("pending", "waiting", "running"):
            self.run_worker(self._load_job_data(incremental=True))
            # Schedule next refresh
            self._schedule_next_refresh()
        else:
            # Job completed, stop auto-refresh
            self._refresh_enabled = False
            self.notify(f"Job {status} - auto-refresh stopped", timeout=3)

    def action_refresh(self) -> None:
        """Manual refresh"""
        self.run_worker(self._load_job_data(incremental=True))
        self.notify("Refreshing job data...", timeout=1)

    def action_toggle_follow(self) -> None:
        """Toggle auto-follow mode"""
        self._auto_follow = not self._auto_follow

        status = "ON" if self._auto_follow else "OFF"
        self.notify(f"Auto-follow: {status}", timeout=2)

    # def action_toggle_wrap(self) -> None:
    #     """Toggle word wrap in STDOUT tab (DISABLED - doesn't work dynamically)"""
    #     stdout_log = self.query_one("#job-stdout-log", RichLog)
    #
    #     # Toggle the wrap property
    #     new_wrap = not stdout_log.wrap
    #     stdout_log.wrap = new_wrap
    #
    #     # Force refresh by clearing and reloading
    #     stdout_log.clear()
    #     self.run_worker(self._reload_stdout())
    #
    #     status = "ON" if new_wrap else "OFF"
    #     self.notify(f"Word wrap: {status}", timeout=2)
    #
    # async def _reload_stdout(self) -> None:
    #     """Reload STDOUT content after wrap toggle"""
    #     # Trigger a full refresh to reload all events
    #     await self._load_job_data(incremental=False)

    def action_cancel_job(self) -> None:
        """Cancel the job (Ctrl+K)"""
        # Only allow canceling running jobs
        if not self.job_data:
            self.notify("No job data loaded", severity="warning")
            return

        status = self.job_data.get("status", "unknown")
        if status not in ("pending", "waiting", "running"):
            self.notify(
                f"Cannot cancel {status} job - only running jobs can be cancelled", severity="warning", timeout=5
            )
            return

        # Show confirmation modal
        self.run_worker(self._show_cancel_confirmation())

    async def _show_cancel_confirmation(self) -> None:
        """Show cancel confirmation modal and handle result"""
        from awx_tui.modals.confirm_cancel import ConfirmCancelModal

        # Show confirmation modal
        confirmed = await self.app.push_screen_wait(ConfirmCancelModal(self.job_data))

        if not confirmed:
            self.notify("Job cancellation cancelled", timeout=2)
            return

        # Cancel the job
        job_id = self.job_data.get("id")
        job_name = self.job_data.get("name", "Unknown")

        self.notify(f"Canceling job #{job_id} '{job_name}'...", timeout=3)

        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            # Get correct endpoint for this job type
            endpoint_base = self._job_endpoint_map.get(self.job_type, "/api/v2/jobs")

            if isinstance(client, AWXClient):
                async with client:
                    await client.post(f"{endpoint_base}/{job_id}/cancel/", data={})
                    self.notify(f"[green]✓[/green] Job #{job_id} '{job_name}' cancelled successfully!", timeout=5)
            else:
                # Mock client
                await client.post(f"{endpoint_base}/{job_id}/cancel/", data={})
                self.notify(f"[green]✓[/green] Job #{job_id} '{job_name}' cancelled successfully!", timeout=5)

            # Refresh job data to show new status
            await self._load_job_data(incremental=False)

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to cancel job: {e}\n{traceback.format_exc()}")
            self.notify(f"[red]✗[/red] Failed to cancel job: {e}", severity="error", timeout=5)

    def action_close(self) -> None:
        """Close the modal"""
        # Stop refresh loop by disabling flag (timer will not reschedule)
        self._refresh_enabled = False
        self.dismiss()
