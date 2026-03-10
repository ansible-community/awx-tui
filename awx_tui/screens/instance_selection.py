"""
AWX TUI - Instance Selection Screen

The first screen shown to users - allows selecting which AWX instance to connect to.
Follows container-registry-card-catalog pattern with 60/40 split.
"""

import time

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static


class InstanceDetailsPanel(Vertical):
    """Right panel showing detailed instance information with action buttons"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance_info = None
        self.parent_screen = None

    def compose(self) -> ComposeResult:
        """Create the layout with details and buttons"""
        yield Static("Select an instance to view details", id="instance_details_text")
        with Horizontal(id="instance_action_buttons"):
            yield Button("Connect", id="connect_button", variant="primary")
            # yield Button("Edit", id="edit_button")  # Instances from config/env, not managed in TUI
            yield Button("Test", id="test_button")
            # yield Button("Delete", id="delete_button", variant="error")  # Instances from config/env, not managed in TUI

    def update_instance_info(self, instance_info: dict):
        """Update the displayed instance information"""
        self.instance_info = instance_info
        details_text = self.query_one("#instance_details_text", Static)

        if instance_info:
            name = instance_info.get("name", "Unknown")
            url = instance_info.get("url", "Unknown")
            description = instance_info.get("description", "No description")
            username = instance_info.get("username", "N/A")
            auth_method = instance_info.get("auth_method", "Unknown")
            status = instance_info.get("status", "unknown")
            last_checked = instance_info.get("last_checked", "Never")
            response_time = instance_info.get("response_time", "N/A")
            version = instance_info.get("version", "Unknown")
            verify_ssl = instance_info.get("verify_ssl", True)

            # Status emoji
            status_emoji = {
                "online": "[green]✓[/green]",
                "slow": "⚠",
                "very_slow": "🐌",
                "offline": "✗",
                "error": "[red]✗[/red]",
                "unknown": "❓",
                "ready": "[green]✓[/green]",  # For mock instances
            }.get(status, "❓")

            # Get API base path
            api_base_path = instance_info.get("api_base_path", "/api/v2")

            # Build details display with emoji indicators
            details = f"""📡 Instance: {name}
🌐 Endpoint: {url}
🔗 API Path: {api_base_path}
📝 Description: {description}
👤 User: {username}
🔐 Auth: {auth_method}
{status_emoji} Status: {status.replace('_', ' ').title()}
🕐 Last Checked: {last_checked}
⚡ Response Time: {response_time}
📦 Version: {version}
🔒 SSL Verify: {'Enabled' if verify_ssl else 'Disabled'}"""

            # Add special indicators for mock/env instances
            if instance_info.get("is_mock"):
                details += "\n⚠️  Note: Mock mode - no real API calls"
            elif instance_info.get("is_env"):
                details += "\n⚠️  Note: Temporary instance - not saved to config"

            details_text.update(details)

            # Update button states
            connect_button = self.query_one("#connect_button", Button)
            # edit_button = self.query_one("#edit_button", Button)  # Button removed
            test_button = self.query_one("#test_button", Button)
            # delete_button = self.query_one("#delete_button", Button)  # Button removed

            # Connect: enabled if status allows connection
            connect_button.disabled = status in ("offline", "error")

            # Test: disabled for mock instances
            is_mock = instance_info.get("is_mock", False)
            test_button.disabled = is_mock

            # Edit/Delete buttons removed - instances managed via config files, not TUI
            # edit_button.disabled = is_mock
            # is_env = instance_info.get('is_env', False)
            # delete_button.disabled = is_env
        else:
            details_text.update("Select an instance to view details")
            # Disable all buttons when nothing selected
            self.query_one("#connect_button", Button).disabled = True
            # self.query_one("#edit_button", Button).disabled = True  # Button removed
            self.query_one("#test_button", Button).disabled = True
            # self.query_one("#delete_button", Button).disabled = True  # Button removed

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action button presses"""
        if not self.parent_screen:
            return

        button_id = event.button.id
        if button_id == "connect_button":
            self.parent_screen.action_connect_instance()
        # elif button_id == "edit_button":  # Button removed - instances from config/env
        #     self.parent_screen.action_edit_instance()
        elif button_id == "test_button":
            self.parent_screen.action_test_instance()
        # elif button_id == "delete_button":  # Button removed - instances from config/env
        #     self.parent_screen.action_delete_instance()


class InstanceSelectionScreen(Screen):
    """
    Instance Selection Screen - first screen shown to users

    60% left: DataTable with instances
    40% right: Details panel with instance info and action buttons
    """

    CSS = """
    Screen {
        layout: horizontal;
    }

    #instance_list {
        width: 60%;
        border: solid $primary;
        margin: 1;
    }

    #instance_details_panel {
        width: 40%;
        border: solid $secondary;
        margin: 1;
        padding: 1;
        layout: vertical;
    }

    #instance_details_text {
        height: 1fr;
    }

    #instance_action_buttons {
        height: 3;
        margin-top: 1;
        dock: bottom;
    }

    #instance_action_buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("enter", "connect_instance", "Connect"),
        # ("a", "add_instance", "Add"),  # Instances loaded from config/env, not managed in TUI
        # ("e", "edit_instance", "Edit"),  # Instances loaded from config/env, not managed in TUI
        # ("d", "delete_instance", "Delete"),  # Instances loaded from config/env, not managed in TUI
        ("t", "test_instance", "Test"),
        ("r", "refresh", "Refresh"),
        ("f5", "refresh", "Refresh"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+d", "debug_console", "Debug"),
        ("i", "show_info", "Info"),
        ("?", "show_info", "Help"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance_data = []
        self.selected_instance = None
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        """Create the instance selection layout"""
        yield Header()
        with Horizontal():
            # Left panel - Instance list
            instance_table = DataTable(id="instance_list", cursor_type="row")
            instance_table.add_columns("  ", "Name", "URL", "Auth", "Version", "Response")
            yield instance_table

            # Right panel - Instance details
            details_panel = InstanceDetailsPanel(id="instance_details_panel")
            details_panel.parent_screen = self
            yield details_panel

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the instance selection screen and start auto-refresh"""
        self.title = "AWX TUI - Select Instance"

        # Load instances with cached status immediately (non-blocking)
        self.load_instances_cached()

        # Trigger background refresh to ping instances
        self.set_timer(0.1, lambda: self.run_worker(self.load_instances()))

        # Auto-refresh using configured interval (default 5 seconds)
        refresh_interval = self.app.app_config.preferences.get("instance_selection_refresh_interval", 5)
        if refresh_interval > 0:
            self._refresh_timer = self.set_interval(refresh_interval, self.action_refresh)

    def load_instances_cached(self) -> None:
        """Load instances with cached status (no ping) - fast initial display"""
        instance_table = self.query_one("#instance_list", DataTable)
        instance_table.clear()
        self.instance_data = []

        if not hasattr(self.app, "instance_manager"):
            return

        instance_manager = self.app.instance_manager
        instance_names = instance_manager.get_instance_names()

        for name in instance_names:
            config = self.app.app_config.instances.get(name)
            if not config:
                continue

            # Use cached status from config (or 'unknown' if never checked)
            status = config.last_status or "unknown"
            response_time = config.last_response_time or "N/A"
            version = "Unknown"

            if name.startswith("mock-"):
                from awx_tui.mock_data import MOCK_INSTANCES

                mock_data = MOCK_INSTANCES.get(name, {})
                response_time = mock_data.get("response_time", "N/A")
                version = mock_data.get("ping", {}).get("version", "Unknown")
                status = mock_data.get("status", "unknown")

            # Build instance info dict
            instance_info = {
                "name": name,
                "url": config.url,
                "api_base_path": config.api_base_path,
                "username": config.username or "N/A",
                "auth_method": config.auth_method.title() if config.auth_method else "None",
                "verify_ssl": config.verify_ssl,
                "description": config.description or "",
                "status": status,
                "last_checked": config.last_checked or "Never",
                "response_time": response_time,
                "version": version,
                "is_mock": name.startswith("mock-"),
                "is_env": name.startswith("@"),  # @env-vars, @cli-args, etc.
            }

            self.instance_data.append(instance_info)

            # Determine status emoji
            status_emoji_map = {
                "online": "[green]✓[/green]",
                "slow": "⚠",
                "very_slow": "🐌",
                "offline": "✗",
                "error": "[red]✗[/red]",
                "unknown": "❓",
                "ready": "[green]✓[/green]",
                "disabled": "⏸",
            }
            status_emoji = status_emoji_map.get(status, "❓")

            # Add mock/env indicator
            if instance_info["is_mock"]:
                emoji_display = f"{status_emoji} 🎭"
            elif instance_info["is_env"]:
                emoji_display = f"{status_emoji} 🌍"
            else:
                emoji_display = status_emoji

            instance_table.add_row(
                emoji_display,
                instance_info["name"],
                instance_info["url"],
                instance_info["auth_method"],
                instance_info["version"],
                instance_info["response_time"],
            )

        # Auto-select first instance if available
        if self.instance_data and instance_table.row_count > 0:
            instance_table.cursor_coordinate = (0, 0)
            self.update_details_for_row(0)
            instance_table.focus()

    async def load_instances(self) -> None:
        """Load instances from instance manager"""
        import asyncio

        instance_table = self.query_one("#instance_list", DataTable)

        # Remember currently selected instance (if any)
        previously_selected_name = None
        if self.selected_instance:
            previously_selected_name = self.selected_instance.get("name")

        if not hasattr(self.app, "instance_manager"):
            return

        instance_manager = self.app.instance_manager

        # Get all instance names
        instance_names = instance_manager.get_instance_names()

        # Ping all instances in parallel
        async def ping_instance(name):
            """Ping a single instance and return its info"""

            # Get config from app config
            config = self.app.app_config.instances.get(name)
            if not config:
                return None

            # Check if this is a mock instance or real instance
            response_time = "N/A"
            version = "Unknown"
            status = "unknown"

            if name.startswith("mock-"):
                # Mock instance - use mock data
                from awx_tui.mock_data import MOCK_INSTANCES

                mock_data = MOCK_INSTANCES.get(name, {})
                response_time = mock_data.get("response_time", "N/A")
                version = mock_data.get("ping", {}).get("version", "Unknown")
                status = mock_data.get("status", "unknown")

                # Update config with mock status and response time
                config.last_status = status
                config.last_checked = time.strftime("%Y-%m-%d %H:%M:%S")
                config.last_response_time = response_time
            else:
                # Real instance - ping using the instance's own AWXClient session
                from awx_tui.client import AWXClient
                from awx_tui.ping_checker import check_instance_ping

                instance_session = None
                if hasattr(self.app, "instance_manager") and self.app.instance_manager:
                    client = self.app.instance_manager.get_client(name)
                    if isinstance(client, AWXClient):
                        async with client:
                            instance_session = client.session

                ping_result = await check_instance_ping(
                    url=config.url,
                    api_base_path=config.api_base_path,
                    verify_ssl=config.verify_ssl,
                    timeout=10.0,
                    api_call_log=self.app.api_call_log if hasattr(self.app, "api_call_log") else None,
                    instance_name=name,
                    max_log_entries=self.app.app_config.preferences.get("debug_console_max_entries", 1000),
                    connection_event_log=getattr(self.app, "connection_event_log", None),
                    instance_client=instance_session,
                )

                status = ping_result["status"]
                version = ping_result["version"]
                response_time = ping_result["response_time"]

                # Update config with latest status and response time
                config.last_status = status
                config.last_checked = time.strftime("%Y-%m-%d %H:%M:%S")
                config.last_response_time = response_time

                # Show notification if there was an error
                if ping_result.get("error"):
                    self.notify(f"{name}: {ping_result['error']}", severity="warning", timeout=3)

            # Build instance info dict
            instance_info = {
                "name": name,
                "url": config.url,
                "api_base_path": config.api_base_path,
                "username": config.username or "N/A",
                "auth_method": config.auth_method.title() if config.auth_method else "None",
                "verify_ssl": config.verify_ssl,
                "description": config.description or "",
                "status": status,
                "last_checked": config.last_checked or "Never",
                "response_time": response_time,
                "version": version,
                "is_mock": name.startswith("mock-"),
                "is_env": name.startswith("@"),  # @env-vars, @cli-args, etc.
            }

            return instance_info

        # Ping all instances concurrently
        ping_tasks = [ping_instance(name) for name in instance_names]
        instance_infos = await asyncio.gather(*ping_tasks)

        # Clear table and rebuild
        instance_table.clear()
        self.instance_data = []

        for instance_info in instance_infos:
            if instance_info is None:
                continue

            self.instance_data.append(instance_info)

            # Determine status emoji for first column
            status = instance_info["status"]
            status_emoji_map = {
                "online": "[green]✓[/green]",
                "slow": "⚠",
                "very_slow": "🐌",
                "offline": "✗",
                "error": "[red]✗[/red]",
                "unknown": "❓",
                "ready": "[green]✓[/green]",
                "disabled": "⏸",
            }
            status_emoji = status_emoji_map.get(status, "❓")

            # Add mock/env indicator to emoji column if applicable
            if instance_info["is_mock"]:
                emoji_display = f"{status_emoji} 🎭"
                instance_info["status"] = "ready"
                status = "ready"
            elif instance_info["is_env"]:
                emoji_display = f"{status_emoji} 🌍"
            else:
                emoji_display = status_emoji

            instance_table.add_row(
                emoji_display,
                instance_info["name"],
                instance_info["url"],
                instance_info["auth_method"],
                instance_info["version"],
                instance_info["response_time"],
            )

        # Restore selection or select first instance
        if instance_table.row_count > 0:
            # Try to restore previous selection
            if previously_selected_name:
                for idx, inst in enumerate(self.instance_data):
                    if inst["name"] == previously_selected_name:
                        instance_table.cursor_coordinate = (idx, 0)
                        self.update_details_for_row(idx)
                        break
                else:
                    # Previously selected instance not found, select first
                    instance_table.cursor_coordinate = (0, 0)
                    self.update_details_for_row(0)
            else:
                # No previous selection, select first
                instance_table.cursor_coordinate = (0, 0)
                self.update_details_for_row(0)

    def update_details_for_row(self, row_index: int) -> None:
        """Update the details panel for the selected row"""
        if 0 <= row_index < len(self.instance_data):
            self.selected_instance = self.instance_data[row_index]
            details_panel = self.query_one("#instance_details_panel", InstanceDetailsPanel)
            details_panel.update_instance_info(self.selected_instance)
        else:
            self.selected_instance = None

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row selection in instance table"""
        self.update_details_for_row(event.cursor_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on instance table row"""
        self.action_connect_instance()

    def action_connect_instance(self) -> None:
        """Connect to the selected instance"""
        if not self.selected_instance:
            self.notify("No instance selected", severity="warning")
            return

        instance_name = self.selected_instance["name"]

        # Switch to this instance
        if hasattr(self.app, "instance_manager"):
            self.app.instance_manager.switch_to(instance_name)
            self.app._update_title()

        # Load dashboard from registry using centralized helper
        dashboard_class = self.app.get_dashboard_class()
        self.app.push_screen(dashboard_class())

    # Instances are loaded from config files and environment variables
    # Add/Edit/Delete don't make sense in the TUI - manage via config files instead
    # def action_add_instance(self) -> None:
    #     """Add a new instance"""
    #     self.notify("Add instance not yet implemented", severity="information")

    # def action_edit_instance(self) -> None:
    #     """Edit the selected instance"""
    #     if not self.selected_instance:
    #         self.notify("No instance selected", severity="warning")
    #         return
    #     self.notify("Edit instance not yet implemented", severity="information")

    # def action_delete_instance(self) -> None:
    #     """Delete the selected instance"""
    #     if not self.selected_instance:
    #         self.notify("No instance selected", severity="warning")
    #         return
    #     self.notify("Delete instance not yet implemented", severity="information")

    def action_test_instance(self) -> None:
        """Test connection to the selected instance"""
        if not self.selected_instance:
            self.notify("No instance selected", severity="warning")
            return

        # Refresh just this instance
        self.notify(f"Testing connection to {self.selected_instance['name']}...", timeout=2)
        self.run_worker(self.load_instances())

    def action_refresh(self) -> None:
        """Refresh instance list"""
        # Only refresh if this screen is currently visible (on top of stack)
        if self.app.screen is self:
            self.run_worker(self.load_instances())

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()

    def action_debug_console(self) -> None:
        """Open debug console"""
        self.app.action_toggle_debug()

    def action_show_info(self) -> None:
        """Show info modal"""
        self.app.action_show_info()

    def on_screen_suspend(self) -> None:
        """Stop auto-refresh when screen is hidden (navigated away)"""
        if self._refresh_timer:
            self._refresh_timer.stop()

    def on_screen_resume(self) -> None:
        """Resume auto-refresh when screen is shown again"""
        refresh_interval = self.app.app_config.preferences.get("instance_selection_refresh_interval", 5)
        if refresh_interval > 0:
            self._refresh_timer = self.set_interval(refresh_interval, self.action_refresh)
