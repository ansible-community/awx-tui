"""
AWX TUI - Main Application Class

The Textual App that manages screens, navigation, and global state.
"""

import random
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from awx_tui import ROTATING_NAMES
from awx_tui.config import AppConfig, ConfigManager
from awx_tui.instance_manager import InstanceManager
from awx_tui.reload import HotReloadManager

# Title rotation interval (seconds) - random between 5-10 minutes
TITLE_ROTATION_MIN = 300  # 5 minutes
TITLE_ROTATION_MAX = 600  # 10 minutes


class AWXTUIApp(App):
    """
    Main AWX TUI application

    Manages screens, navigation, instance switching, and global keybindings.
    """

    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+d", "toggle_debug", "Debug", priority=True),
        Binding("ctrl+o", "the_loaf", "Loaf", priority=True),
        Binding("ctrl+t", "advanced_api_mode", "API Mode", priority=True),
        Binding("ctrl+n", "the_network_queue", "Net Queue", priority=True),
        Binding("c", "create_mode", "Create", priority=True),
        Binding("i", "show_info", "Info"),
        Binding("?", "show_info", "Help"),
    ]

    def __init__(self, config_path: Optional[Path] = None, mock_mode: bool = False, cli_args=None, **kwargs):
        """
        Initialize AWX TUI application

        Args:
            config_path: Path to config file (default: ~/.config/awx-tui/config.yaml)
            mock_mode: If True, use mock data instead of real AWX
            cli_args: Command-line arguments for creating @cli-args instance
        """
        super().__init__(**kwargs)

        # When run via 'textual run', parse sys.argv for our flags
        # This handles: textual run --dev awx_tui.app:AWXTUIApp -- --mock --dashboard sleek
        if cli_args is None:
            import sys

            cli_args = self._parse_textual_run_args(sys.argv)
            if cli_args:
                mock_mode = cli_args.mock
                config_path = cli_args.config

        # Also check AWX_MOCK environment variable as fallback
        import os

        if not mock_mode and os.environ.get("AWX_MOCK", "").lower() in ("true", "1", "yes"):
            mock_mode = True

        self.config_path = config_path
        self.mock_mode = mock_mode
        self.cli_args = cli_args

        # Will be initialized in on_mount
        self.config_manager: Optional[ConfigManager] = None
        self.app_config: Optional[AppConfig] = None
        self.instance_manager: Optional[InstanceManager] = None
        self.hot_reload: Optional[HotReloadManager] = None

        # API call log for debug console
        self.api_call_log = []

        # Notification log for The Loaf
        self.notification_log = []

        # Connection event log for The Network Queue
        self.connection_event_log = []

        # Create mode state - persists form data until app close
        self.create_mode_state = {
            "project": {},
            "job_template": {},
            "inventory": {},
            "credential": {},
        }

        # Add some mock API calls for testing debug console
        if mock_mode:
            from datetime import datetime

            self.api_call_log.extend(
                [
                    {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "method": "GET",
                        "instance": "mock-prod",
                        "instance_name": "mock-prod",
                        "endpoint": "/api/v2/ping/",
                        "url": "https://mock-prod.example.com/api/v2/ping/",
                        "status_code": 200,
                        "duration_ms": 234,
                        "size_bytes": 1024,
                        "request_headers": {
                            "User-Agent": "awx-tui/0.1.0-beta",
                            "Accept": "application/json",
                            "X-Request-ID": "abc123-def456-ghi789",
                        },
                        "response_headers": {
                            "Content-Type": "application/json",
                            "X-API-Time": "0.234s",
                            "X-RateLimit-Remaining": "4999",
                            "X-AWX-Version": "23.1.0",
                            "Server": "nginx/1.20.1",
                        },
                        "content_preview": '{"ha": true, "version": "23.1.0", "active_node": "mock-controller-001.local", ...}',
                        "response_content_full": '{"ha": true, "version": "23.1.0", "active_node": "mock-controller-001.local", "install_uuid": "e8f9a7b5-1234-5678-9abc-def012345678", "instances": [{"node": "mock-controller-001.local", "node_type": "control", "capacity": 136}]}',
                    },
                    {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "method": "GET",
                        "instance": "mock-prod",
                        "instance_name": "mock-prod",
                        "endpoint": "/api/v2/instances/",
                        "url": "https://mock-prod.example.com/api/v2/instances/",
                        "status_code": 200,
                        "duration_ms": 456,
                        "size_bytes": 2048,
                        "request_headers": {
                            "User-Agent": "awx-tui/0.1.0-beta",
                            "Accept": "application/json",
                            "X-Request-ID": "xyz789-uvw012-rst345",
                        },
                        "response_headers": {
                            "Content-Type": "application/json",
                            "X-API-Time": "0.456s",
                            "X-RateLimit-Remaining": "4998",
                            "X-AWX-Version": "23.1.0",
                            "Server": "nginx/1.20.1",
                            "X-API-Node": "mock-controller-001",
                        },
                        "content_preview": '{"count": 2, "results": [{"node": "mock-controller-001.local", "capacity": 136, ...}]}',
                        "response_content_full": '{"count": 2, "next": null, "previous": null, "results": [{"node": "mock-controller-001.local", "node_type": "control", "node_state": "ready", "capacity": 136, "consumed_capacity": 0, "percent_capacity_remaining": 100.0, "jobs_running": 0, "jobs_total": 203}, {"node": "mock-controller-002.local", "node_type": "control", "node_state": "ready", "capacity": 136, "consumed_capacity": 0, "percent_capacity_remaining": 100.0, "jobs_running": 0, "jobs_total": 189}]}',
                    },
                    {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "method": "GET",
                        "instance": "mock-dev",
                        "endpoint": "/api/v2/jobs/",
                        "url": "https://mock-dev.example.com/api/v2/jobs/",
                        "status_code": 200,
                        "duration_ms": 2300,
                        "size_bytes": 4096,
                        "request_headers": {
                            "User-Agent": "awx-tui/0.1.0-beta",
                            "Accept": "application/json",
                            "X-Request-ID": "lmn456-opq789-rst012",
                        },
                        "response_headers": {
                            "Content-Type": "application/json",
                            "X-API-Time": "2.300s",
                            "X-RateLimit-Remaining": "4997",
                            "X-AWX-Version": "23.1.0",
                            "Server": "nginx/1.20.1",
                            "X-API-Query-Count": "15",
                            "X-API-Total-Count": "156",
                        },
                        "content_preview": '{"count": 15, "results": [{"id": 1, "name": "Deploy Webserver", "status": "running", ...}]}',
                        "response_content_full": '{"count": 15, "next": "/api/v2/jobs/?page=2", "previous": null, "results": [{"id": 1, "type": "job", "name": "Deploy Webserver", "status": "running", "started": "2025-11-20T10:15:00Z", "finished": null, "elapsed": 45.2, "job_template": 5, "inventory": 2, "project": 3, "playbook": "webserver.yml", "execution_environment": 1, "created_by": {"username": "admin"}}]}',
                    },
                ]
            )

        # Pick a random app name for this session
        self.current_app_name = random.choice(ROTATING_NAMES)  # NOSONAR
        self.title = self.current_app_name
        # self.sub_title = TAGLINE

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header(show_clock=True)
        yield Footer()

    async def on_mount(self) -> None:
        """Called when app is mounted - initialize everything"""
        # Load configuration
        self.config_manager = ConfigManager(config_path=self.config_path)

        try:
            self.app_config = self.config_manager.load(cli_args=self.cli_args)
        except Exception as e:
            # If config fails to load, start with empty config and notify user
            self.log.error(f"Failed to load config: {e}")
            self.app_config = AppConfig()
            self.notify(f"Config error: {e}", severity="error", timeout=10)

        # Initialize instance manager
        self.instance_manager = InstanceManager(
            self.app_config,
            mock_mode=self.mock_mode,
            api_call_log=self.api_call_log,
            connection_event_log=self.connection_event_log,
        )

        # Update title with current instance
        self._update_title()

        # Start title rotation timer
        self._schedule_title_rotation()

        # Initialize hot reload manager (auto-starts in dev mode)
        self.hot_reload = HotReloadManager(self)

        # Push initial screen
        await self._push_initial_screen()

    def _parse_textual_run_args(self, argv: list):
        """Parse arguments when run via 'textual run'.

        When run with: textual run --dev awx_tui.app:AWXTUIApp -- --mock --dashboard sleek
        The '--' separates textual's args from our app's args.

        Returns:
            Parsed args namespace, or None if parsing fails
        """
        import argparse

        # Find our args (after '--' separator if present)
        try:
            separator_idx = argv.index("--")
            our_args = argv[separator_idx + 1 :]
        except ValueError:
            # No separator - might be running directly, check for our flags
            our_args = [arg for arg in argv if arg in ("--mock", "--dashboard", "sleek", "classic")]
            if not our_args:
                return None

        # Parse just the args we care about
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--mock", action="store_true", default=False)
        parser.add_argument("--dashboard", type=str, default=None)
        parser.add_argument("--config", type=Path, default=None)

        try:
            args, _ = parser.parse_known_args(our_args)
            return args
        except Exception:
            return None

    def _update_title(self) -> None:
        """Update app title"""
        self.title = self.current_app_name

    def _rotate_title(self) -> None:
        """Rotate to a new app name (must be different from current)"""
        # Get list of names that aren't the current one
        available_names = [name for name in ROTATING_NAMES if name != self.current_app_name]

        # Pick a random new name
        self.current_app_name = random.choice(available_names)  # NOSONAR

        # Update title display
        self._update_title()

        # Schedule next rotation
        self._schedule_title_rotation()

    def _schedule_title_rotation(self) -> None:
        """Schedule the next title rotation at a random interval (5-10 minutes)"""
        interval = random.uniform(TITLE_ROTATION_MIN, TITLE_ROTATION_MAX)  # NOSONAR
        self.set_timer(interval, self._rotate_title)

    def get_dashboard_class(self):
        """Get the dashboard class based on CLI args, instance config, or default.

        Priority: CLI --dashboard arg > instance config > default 'classic'
        """
        from awx_tui.dashboards import get_dashboard

        # Check for CLI override first
        dashboard_name = None
        if self.cli_args and hasattr(self.cli_args, "dashboard"):
            dashboard_name = self.cli_args.dashboard

        # Fall back to instance config
        if not dashboard_name and self.instance_manager:
            instance_name = self.instance_manager.current_instance
            if instance_name and self.app_config and self.app_config.instances:
                instance_config = self.app_config.instances.get(instance_name)
                if instance_config:
                    dashboard_name = getattr(instance_config, "dashboard", None)

        # Default to classic
        if not dashboard_name:
            dashboard_name = "classic"

        return get_dashboard(dashboard_name, self.app_config)

    async def _push_initial_screen(self) -> None:
        """Push the initial screen - Instance Selection or restored screen from hot reload"""
        from awx_tui.screens.instance_selection import InstanceSelectionScreen

        try:
            await self.push_screen(InstanceSelectionScreen())
        except ImportError as e:
            self.notify(f"Failed to load instance selection: {e}", severity="error")
            return

        # Hot reload manager will restore the previous screen if in dev mode
        await self.hot_reload.try_restore_screen()

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()

    async def on_unmount(self) -> None:
        """Clean up persistent sessions on app shutdown"""
        if hasattr(self, "instance_manager") and self.instance_manager:
            await self.instance_manager.close_all_clients()

    def action_toggle_debug(self) -> None:
        """Toggle debug console - do nothing if already open"""
        from awx_tui.screens.debug_console import DebugConsoleScreen

        # If debug console is already the topmost screen, do nothing
        if isinstance(self.screen, DebugConsoleScreen):
            return

        # Otherwise, open debug console
        self.push_screen(DebugConsoleScreen())

    def action_show_info(self) -> None:
        """Show info/about modal"""
        from awx_tui.modals.info import InfoModal

        self.push_screen(InfoModal(self.current_app_name))

    def action_the_loaf(self) -> None:
        """Open The Loaf - notification history debugger - do nothing if already open"""
        from awx_tui.screens.the_loaf import TheLoafScreen

        # If The Loaf is already the topmost screen, do nothing
        if isinstance(self.screen, TheLoafScreen):
            return

        # Otherwise, open The Loaf
        self.push_screen(TheLoafScreen())

    def action_the_network_queue(self) -> None:
        """Open The Network Queue - connection pool debugger - do nothing if already open"""
        from awx_tui.screens.the_network_queue import TheNetworkQueueScreen

        # If The Network Queue is already the topmost screen, do nothing
        if isinstance(self.screen, TheNetworkQueueScreen):
            return

        # Otherwise, open The Network Queue
        self.push_screen(TheNetworkQueueScreen())

    def notify(
        self,
        message: str,
        *,
        title: str = "",
        severity: str = "information",
        timeout: float = 2.0,
        markup: bool = True,
    ) -> None:
        """
        Override notify to capture all notifications in The Loaf

        Args:
            message: Notification message
            title: Optional notification title
            severity: Severity level (information, warning, error, success)
            timeout: How long to show the notification
            markup: Whether to parse markup in the message
        """
        from datetime import datetime

        # Get source screen
        current_screen = self.screen
        source = current_screen.__class__.__name__ if current_screen else "App"

        # Log notification
        self.notification_log.append(
            {
                "timestamp": datetime.now(),
                "severity": severity,
                "message": message,
                "title": title,
                "source": source,
                "timeout": timeout,
            }
        )

        # Cap notifications (configurable, default 1000)
        max_entries = 1000
        if self.app_config:
            max_entries = self.app_config.preferences.get("loaf_max_entries", 1000)

        if max_entries > 0 and len(self.notification_log) > max_entries:
            # Keep only the most recent entries
            self.notification_log[:] = self.notification_log[-max_entries:]

        # Call parent notify to actually show the toast
        super().notify(
            message,
            title=title,
            severity=severity,
            timeout=timeout,
            markup=markup,
        )

    def action_create_mode(self) -> None:
        """Open Create Mode menu (context-aware)"""
        from awx_tui.screens.create_menu import CreateMenuScreen

        current_screen = self.screen
        screen_class_name = current_screen.__class__.__name__

        # Pass context to Create Menu for intelligent pre-selection
        self.push_screen(CreateMenuScreen(context_screen=screen_class_name))

    def action_advanced_api_mode(self) -> None:
        """Open Advanced API Mode screen (context-aware) - do nothing if already open"""
        from awx_tui.screens.advanced_api_mode import AdvancedAPIModeScreen

        # If Advanced API Mode is already the topmost screen, do nothing
        if isinstance(self.screen, AdvancedAPIModeScreen):
            return

        prepopulate_data = None
        current_screen = self.screen

        # Check which screen we're on and extract context
        screen_class_name = current_screen.__class__.__name__

        if screen_class_name == "DebugConsoleScreen":
            # Debug console - pre-populate from selected API call
            prepopulate_data = self._get_debug_console_prepopulation(current_screen)
        elif screen_class_name == "InstanceSelectionScreen":
            # Instance selection - pre-populate with ping endpoint
            prepopulate_data = {"method": "GET", "endpoint": "ping/"}
        elif screen_class_name in ("ClassicDashboard", "SleekDashboard"):
            # Dashboard - pre-populate with instances endpoint
            prepopulate_data = {"method": "GET", "endpoint": "instances/"}
        elif screen_class_name == "TemplatesScreen":
            # Templates screen - pre-populate with job templates endpoint
            prepopulate_data = {"method": "GET", "endpoint": "job_templates/"}
        elif screen_class_name == "ProjectsScreen":
            # Projects screen - pre-populate with projects endpoint
            prepopulate_data = {"method": "GET", "endpoint": "projects/"}
        elif screen_class_name == "ActiveJobsScreen":
            # Active jobs screen - pre-populate with running jobs endpoint
            prepopulate_data = {"method": "GET", "endpoint": "unified_jobs/?status__in=pending,waiting,running"}
        elif screen_class_name == "HistoricJobsScreen":
            # Historic jobs screen - pre-populate with jobs endpoint
            prepopulate_data = {"method": "GET", "endpoint": "jobs/"}
        elif screen_class_name == "InventoriesScreen":
            # Inventories screen - pre-populate with inventories endpoint
            prepopulate_data = {"method": "GET", "endpoint": "inventories/"}
        elif screen_class_name == "UpdateInventoryScreen":
            # Update inventory screen - pre-populate with PATCH and current form data
            if hasattr(current_screen, "inventory_id") and hasattr(current_screen, "_build_inventory_data_for_preview"):
                import json

                inv_id = current_screen.inventory_id
                inventory_data, notes = current_screen._build_inventory_data_for_preview()
                prepopulate_data = {
                    "method": "PATCH",
                    "endpoint": f"inventories/{inv_id}/",
                    "request_body": json.dumps(inventory_data, indent=2),
                }
            elif hasattr(current_screen, "inventory_id"):
                inv_id = current_screen.inventory_id
                prepopulate_data = {"method": "PATCH", "endpoint": f"inventories/{inv_id}/"}
            else:
                prepopulate_data = {"method": "PATCH", "endpoint": "inventories/"}
        elif screen_class_name == "UpdateProjectScreen":
            # Update project screen - pre-populate with PATCH and current form data
            if hasattr(current_screen, "project_id") and hasattr(current_screen, "_build_project_data_for_preview"):
                import json

                project_id = current_screen.project_id
                project_data, notes = current_screen._build_project_data_for_preview()
                prepopulate_data = {
                    "method": "PATCH",
                    "endpoint": f"projects/{project_id}/",
                    "request_body": json.dumps(project_data, indent=2),
                }
            elif hasattr(current_screen, "project_id"):
                project_id = current_screen.project_id
                prepopulate_data = {"method": "PATCH", "endpoint": f"projects/{project_id}/"}
            else:
                prepopulate_data = {"method": "PATCH", "endpoint": "projects/"}
        elif screen_class_name == "UpdateJobTemplateScreen":
            # Update job template screen - pre-populate with PATCH and current form data
            if hasattr(current_screen, "template_id") and hasattr(
                current_screen, "_build_job_template_data_for_preview"
            ):
                import json

                template_id = current_screen.template_id
                template_data, notes = current_screen._build_job_template_data_for_preview()
                prepopulate_data = {
                    "method": "PATCH",
                    "endpoint": f"job_templates/{template_id}/",
                    "request_body": json.dumps(template_data, indent=2),
                }
            elif hasattr(current_screen, "template_id"):
                template_id = current_screen.template_id
                prepopulate_data = {"method": "PATCH", "endpoint": f"job_templates/{template_id}/"}
            else:
                prepopulate_data = {"method": "PATCH", "endpoint": "job_templates/"}
        elif screen_class_name == "HostEditModal":
            # Host edit modal - pre-populate based on mode
            if hasattr(current_screen, "_build_host_data_for_preview"):
                import json

                host_data, notes = current_screen._build_host_data_for_preview()

                if hasattr(current_screen, "is_edit_mode") and current_screen.is_edit_mode:
                    # Edit mode - PATCH host with current form data
                    if hasattr(current_screen, "host_data") and current_screen.host_data:
                        host_id = current_screen.host_data.get("id")
                        if host_id:
                            prepopulate_data = {
                                "method": "PATCH",
                                "endpoint": f"hosts/{host_id}/",
                                "request_body": json.dumps(host_data, indent=2),
                            }
                        else:
                            prepopulate_data = {"method": "PATCH", "endpoint": "hosts/"}
                    else:
                        prepopulate_data = {"method": "PATCH", "endpoint": "hosts/"}
                elif hasattr(current_screen, "inventory_id"):
                    # Create mode - POST new host to inventory with current form data
                    inv_id = current_screen.inventory_id
                    prepopulate_data = {
                        "method": "POST",
                        "endpoint": f"inventories/{inv_id}/hosts/",
                        "request_body": json.dumps(host_data, indent=2),
                    }
                else:
                    prepopulate_data = {"method": "GET", "endpoint": "hosts/"}
            elif hasattr(current_screen, "is_edit_mode") and current_screen.is_edit_mode:
                # Fallback for edit mode without preview method
                if hasattr(current_screen, "host_data") and current_screen.host_data:
                    host_id = current_screen.host_data.get("id")
                    if host_id:
                        prepopulate_data = {"method": "PATCH", "endpoint": f"hosts/{host_id}/"}
                    else:
                        prepopulate_data = {"method": "PATCH", "endpoint": "hosts/"}
                else:
                    prepopulate_data = {"method": "PATCH", "endpoint": "hosts/"}
            elif hasattr(current_screen, "inventory_id"):
                # Fallback for create mode without preview method
                inv_id = current_screen.inventory_id
                prepopulate_data = {"method": "POST", "endpoint": f"inventories/{inv_id}/hosts/"}
            else:
                prepopulate_data = {"method": "GET", "endpoint": "hosts/"}
        elif screen_class_name == "JobDetailModal":
            # Job detail modal - pre-populate with job endpoint
            if hasattr(current_screen, "job_id"):
                job_id = current_screen.job_id
                prepopulate_data = {"method": "GET", "endpoint": f"jobs/{job_id}/"}
            else:
                prepopulate_data = {"method": "GET", "endpoint": "jobs/"}
        elif screen_class_name == "ConfirmLaunchModal":
            # Confirm launch modal - pre-populate with launch endpoint
            if hasattr(current_screen, "template") and current_screen.template:
                template_id = current_screen.template.get("id")
                if template_id:
                    prepopulate_data = {"method": "POST", "endpoint": f"job_templates/{template_id}/launch/"}
                else:
                    prepopulate_data = {"method": "GET", "endpoint": "job_templates/"}
            else:
                prepopulate_data = {"method": "GET", "endpoint": "job_templates/"}
        elif screen_class_name == "ConfirmRelaunchModal":
            # Confirm relaunch modal - pre-populate with relaunch endpoint
            if hasattr(current_screen, "job_id"):
                job_id = current_screen.job_id
                prepopulate_data = {"method": "POST", "endpoint": f"jobs/{job_id}/relaunch/"}
            else:
                prepopulate_data = {"method": "GET", "endpoint": "jobs/"}
        elif screen_class_name == "ConfirmSyncModal":
            # Confirm sync modal - pre-populate with project update endpoint
            if hasattr(current_screen, "project") and current_screen.project:
                project_id = current_screen.project.get("id")
                if project_id:
                    prepopulate_data = {"method": "POST", "endpoint": f"projects/{project_id}/update/"}
                else:
                    prepopulate_data = {"method": "GET", "endpoint": "projects/"}
            else:
                prepopulate_data = {"method": "GET", "endpoint": "projects/"}
        elif screen_class_name == "ConfirmCancelModal":
            # Confirm cancel modal - pre-populate with cancel endpoint
            if hasattr(current_screen, "job_id"):
                job_id = current_screen.job_id
                prepopulate_data = {"method": "POST", "endpoint": f"unified_jobs/{job_id}/cancel/"}
            else:
                prepopulate_data = {"method": "GET", "endpoint": "unified_jobs/"}
        elif screen_class_name == "JsonPreviewModal":
            # JSON preview modal - pre-populate with the endpoint being previewed
            if hasattr(current_screen, "endpoint"):
                endpoint = current_screen.endpoint
                method = getattr(current_screen, "method", "POST")
                json_data = getattr(current_screen, "json_data", None)
                prepopulate_data = {"method": method, "endpoint": endpoint}
                if json_data:
                    import json

                    prepopulate_data["request_body"] = json.dumps(json_data, indent=2)
            else:
                prepopulate_data = None
        elif screen_class_name == "CreateProjectScreen":
            # Create project screen - pre-populate with current form data
            if hasattr(current_screen, "_build_project_data_for_preview"):
                import json

                project_data, notes = current_screen._build_project_data_for_preview()
                prepopulate_data = {
                    "method": "POST",
                    "endpoint": "projects/",
                    "request_body": json.dumps(project_data, indent=2),
                }
            else:
                prepopulate_data = {"method": "POST", "endpoint": "projects/"}
        elif screen_class_name == "CreateJobTemplateScreen":
            # Create job template screen - pre-populate with current form data
            if hasattr(current_screen, "_build_job_template_data_for_preview"):
                import json

                template_data, notes = current_screen._build_job_template_data_for_preview()
                prepopulate_data = {
                    "method": "POST",
                    "endpoint": "job_templates/",
                    "request_body": json.dumps(template_data, indent=2),
                }
            else:
                prepopulate_data = {"method": "POST", "endpoint": "job_templates/"}
        elif screen_class_name == "CreateInventoryScreen":
            # Create inventory screen - pre-populate with current form data
            if hasattr(current_screen, "_build_inventory_data_for_preview"):
                import json

                inventory_data, notes = current_screen._build_inventory_data_for_preview()
                prepopulate_data = {
                    "method": "POST",
                    "endpoint": "inventories/",
                    "request_body": json.dumps(inventory_data, indent=2),
                }
            else:
                prepopulate_data = {"method": "POST", "endpoint": "inventories/"}
        elif screen_class_name == "CreateCredentialScreen":
            # Create credential screen - pre-populate with current form data
            if hasattr(current_screen, "_build_credential_data_for_preview"):
                import json

                credential_data, notes = current_screen._build_credential_data_for_preview()
                prepopulate_data = {
                    "method": "POST",
                    "endpoint": "credentials/",
                    "request_body": json.dumps(credential_data, indent=2),
                }
            else:
                prepopulate_data = {"method": "POST", "endpoint": "credentials/"}

        # Open Advanced API Mode with context-aware pre-population
        self.push_screen(AdvancedAPIModeScreen(prepopulate_data=prepopulate_data))

    def _get_debug_console_prepopulation(self, debug_screen) -> dict:
        """Extract pre-population data from debug console's selected API call"""
        try:
            # Check if debug console has a selected API call
            if not hasattr(debug_screen, "api_call_data"):
                return None

            api_table = debug_screen.query_one("#api_call_list")
            if not hasattr(api_table, "cursor_coordinate") or not api_table.cursor_coordinate:
                return None

            row_index = api_table.cursor_coordinate[0]
            if not (0 <= row_index < len(debug_screen.api_call_data)):
                return None

            # Get selected API call
            call_data = debug_screen.api_call_data[row_index]

            # Extract pre-population data (includes instance_name for temporary override)
            return debug_screen._extract_prepopulate_data(call_data)
        except Exception as e:
            self.log.error(f"Failed to extract debug console prepopulation: {e}")
            return None

    def _switch_to_highlighted_instance(self, instance_screen) -> None:
        """Switch to the highlighted instance on the instances screen"""
        try:
            # Check if there's a selected instance
            if not hasattr(instance_screen, "selected_instance"):
                return

            selected_instance = instance_screen.selected_instance
            if not selected_instance:
                return

            # Get the instance name
            instance_name = selected_instance.get("name")
            if not instance_name:
                return

            # Check if it's different from current instance
            current_instance = self.instance_manager.current_instance
            if instance_name != current_instance:
                # Switch to the highlighted instance
                self.instance_manager.switch_to(instance_name)
                self.notify(f"Switched to instance: {instance_name}", timeout=2)
        except Exception as e:
            self.log.error(f"Failed to switch to highlighted instance: {e}")
