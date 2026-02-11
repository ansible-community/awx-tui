"""
AWX TUI - Create Hosts Screen

Full-screen form for creating new AWX hosts.
Part of Create Mode - access via 'C' key -> '5' or select Hosts from menu.
"""

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Input, Select, Static, TextArea


class CreateHostsScreen(Screen):
    """
    Create Hosts - Form for creating new AWX host

    Features:
    - Basic host creation (name, description, inventory, enabled)
    - Variables (JSON format)
    - State persistence (survives navigation to other create screens)
    - Number keys (1-5) to navigate to other create screens
    """

    CSS = """
    CreateHostsScreen {
        layout: vertical;
    }

    #top_panel {
        height: 3;
        border: solid $accent;
        padding: 0 1;
        background: $boost;
    }

    #form_container {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }

    #top_sections {
        height: auto;
        width: 100%;
        margin-bottom: 1;
    }

    .form_section {
        border: solid $accent;
        padding: 0 1;
        margin-bottom: 1;
    }

    .form_section_half {
        width: 1fr;
        height: 13;
        overflow-y: auto;
        margin-right: 1;
    }

    .form_section_half:last-child {
        margin-right: 0;
    }

    .form_section_half .section_title {
        margin-bottom: 0;
    }

    .section_title {
        text-style: bold;
        color: $primary;
        margin-top: 0;
        margin-bottom: 1;
    }

    .field_label {
        width: 25;
        padding-right: 2;
        text-align: right;
    }

    .field_input {
        width: 1fr;
    }

    Input {
        margin: 0;
        padding: 0 1;
        border: none;
        height: 1;
        background: $boost;
    }

    Select {
        margin: 0;
        padding: 0;
        background: $boost;
    }

    TextArea {
        margin: 0;
        padding: 0 1;
    }

    Horizontal {
        height: auto;
        align: left middle;
    }

    #variables_section {
        height: auto;
        margin-bottom: 1;
    }

    #variables_section .section_title {
        margin-bottom: 0;
    }

    #variables_area {
        height: 8;
    }

    #button_container {
        height: 3;
        dock: bottom;
        align: center middle;
        margin-bottom: 2;
    }

    Button {
        margin: 0 1;
    }

    .options_row {
        height: auto;
        padding-left: 25;
        margin: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True, priority=True),
        Binding("1", "navigate_create('project')", "Project", show=True, priority=True),
        Binding("2", "navigate_create('job_template')", "Template", show=True, priority=True),
        Binding("3", "navigate_create('credential')", "Credential", show=True, priority=True),
        Binding("4", "navigate_create('inventory')", "Inventory", show=True, priority=True),
        Binding("5", "navigate_create('hosts')", "Hosts", show=True, priority=True),
        Binding("i", "show_info", "Info", show=True),
        Binding("ctrl+r", "reload_dropdowns", "Reload", show=True),
        Binding("ctrl+s", "submit", "Submit", show=True),
        Binding("ctrl+l", "clear_form", "Clear", show=True),
        Binding("ctrl+j", "preview_json", "Preview JSON", show=True),
        Binding("ctrl+e", "export_task", "Export AP Task", show=True),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_type = "hosts"

    def compose(self) -> ComposeResult:
        """Create the form layout"""
        # Top panel with app and instance info
        yield Static("", id="top_panel")

        with ScrollableContainer(id="form_container"):
            # Top row: Basic Info and Host Configuration
            with Horizontal(id="top_sections"):
                # Basic Information Section (left half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Basic Information", classes="section_title")

                    with Horizontal():
                        yield Static("Name *:", classes="field_label")
                        yield Input(placeholder="Hostname or IP address (required)", id="name", classes="field_input")

                    with Horizontal():
                        yield Static("Description:", classes="field_label")
                        yield Input(placeholder="Optional description", id="description", classes="field_input")

                # Host Configuration Section (right half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Host Configuration", classes="section_title")

                    with Horizontal():
                        yield Static("Inventory *:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="inventory", classes="field_input", allow_blank=True
                        )

                    with Horizontal(classes="options_row"):
                        yield Checkbox("Enabled", id="enabled", value=True)

            # Variables Section (full width)
            with Container(classes="form_section", id="variables_section"):
                yield Static("Variables (JSON)", classes="section_title")
                yield TextArea(id="variables_area", language="json", text="{\n  \n}")

        # Action buttons
        with Horizontal(id="button_container"):
            yield Button("Submit", variant="primary", id="submit_button")
            yield Button("Clear Form", variant="warning", id="clear_button")
            yield Button("Cancel", variant="default", id="cancel_button")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize screen and load saved state if available"""
        # Update title with app name and instance info
        app_name = self.app.current_app_name if hasattr(self.app, "current_app_name") else "AWX TUI"
        instance_manager = self.app.instance_manager
        instance_name = instance_manager.current_instance if instance_manager else "No Instance"
        self.title = f"{app_name} - Create Host for {instance_name}"

        # Update top panel (single line, accent colored)
        top_panel = self.query_one("#top_panel", Static)
        top_panel.update(f"[bold]{app_name}[/bold] - [bold $accent]Create Host for {instance_name}[/bold $accent]")

        # Fetch and populate inventories
        await self._populate_inventories()

        # Load saved state from app
        self._load_state()

    async def _populate_inventories(self) -> None:
        """Fetch inventories from API and populate dropdown"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            inventory_select = self.query_one("#inventory", Select)
            current_value = inventory_select.value

            async with client:
                # Fetch inventories
                response = await client.get("inventories/")
                inventories = response.get("results", [])

                # Build options: (display_name, inventory_id)
                options = [(inv["name"], inv["id"]) for inv in inventories]

                # Populate select
                inventory_select.set_options(options)

                # Restore previous selection if it still exists
                if current_value is not None:
                    option_ids = [opt[1] for opt in options]
                    if current_value in option_ids:
                        inventory_select.value = current_value

        except Exception as e:
            self.notify(f"Failed to load inventories: {e}", severity="warning", timeout=3)

    def _load_state(self) -> None:
        """Load form state from app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = self.app.create_mode_state.get(self.create_type, {})
        if not state:
            return

        # Restore text inputs
        for field_id in ["name", "description"]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Input)
                widget.value = state[field_id]

        # Restore select widgets
        if "inventory" in state:
            widget = self.query_one("#inventory", Select)
            widget.value = state["inventory"]

        # Restore checkboxes
        if "enabled" in state:
            widget = self.query_one("#enabled", Checkbox)
            widget.value = state["enabled"]

        # Restore variables TextArea
        if "variables" in state:
            widget = self.query_one("#variables_area", TextArea)
            widget.text = state["variables"]

    def _save_state(self) -> None:
        """Save current form state to app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = {}

        # Save text inputs
        for field_id in ["name", "description"]:
            widget = self.query_one(f"#{field_id}", Input)
            state[field_id] = widget.value

        # Save select widgets
        inventory_widget = self.query_one("#inventory", Select)
        state["inventory"] = inventory_widget.value

        # Save checkboxes
        enabled_widget = self.query_one("#enabled", Checkbox)
        state["enabled"] = enabled_widget.value

        # Save variables TextArea
        widget = self.query_one("#variables_area", TextArea)
        state["variables"] = widget.text

        self.app.create_mode_state[self.create_type] = state

    def _clear_state(self) -> None:
        """Clear saved state from app.create_mode_state"""
        if hasattr(self.app, "create_mode_state"):
            self.app.create_mode_state[self.create_type] = {}

    def action_navigate_create(self, create_type: str) -> None:
        """Navigate to a different create screen (1-5 keys)"""
        # Save current state before navigating
        self._save_state()

        # Pop this screen and push the appropriate one
        if create_type == "hosts":
            # Already on hosts screen, do nothing
            return
        elif create_type == "project":
            from awx_tui.screens.create_project import CreateProjectScreen

            self.app.pop_screen()
            self.app.push_screen(CreateProjectScreen())
        elif create_type == "job_template":
            from awx_tui.screens.create_job_template import CreateJobTemplateScreen

            self.app.pop_screen()
            self.app.push_screen(CreateJobTemplateScreen())
        elif create_type == "credential":
            from awx_tui.screens.create_credential import CreateCredentialScreen

            self.app.pop_screen()
            self.app.push_screen(CreateCredentialScreen())
        elif create_type == "inventory":
            from awx_tui.screens.create_inventory import CreateInventoryScreen

            self.app.pop_screen()
            self.app.push_screen(CreateInventoryScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "submit_button":
            self.action_submit()
        elif event.button.id == "clear_button":
            self.action_clear_form()
        elif event.button.id == "cancel_button":
            self.action_close()

    def action_submit(self) -> None:
        """Validate and submit the form"""
        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get Select values and convert NoSelection to None
        inventory_id = self.query_one("#inventory", Select).value
        if inventory_id is Select.BLANK:
            inventory_id = None

        # Get enabled checkbox
        enabled = self.query_one("#enabled", Checkbox).value

        # Get variables
        variables_text = self.query_one("#variables_area", TextArea).text.strip()

        # Validate required fields
        if not name:
            self.notify("Host name is required", severity="error", timeout=3)
            self.query_one("#name", Input).focus()
            return

        if not inventory_id:
            self.notify("Inventory is required", severity="error", timeout=3)
            return

        # Validate and parse variables JSON (if provided)
        variables_dict = None
        if variables_text:
            try:
                variables_dict = json.loads(variables_text)
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON in variables: {e}", severity="error", timeout=5)
                self.query_one("#variables_area", TextArea).focus()
                return

        # Build host data
        host_data = {
            "name": name,
            "description": description,
            "inventory": inventory_id,
            "enabled": enabled,
        }

        # Add optional fields
        if variables_dict:
            host_data["variables"] = json.dumps(variables_dict)

        # Create the host via API (async)
        self.run_worker(self._create_host_async(host_data, name))

    async def _create_host_async(self, host_data: dict, name: str) -> None:
        """Async method to create host via API"""
        try:
            self.notify(f"Creating host '{name}'...", timeout=2)

            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            async with client:
                # POST to /api/v2/hosts/
                response = await client.post("hosts/", data=host_data)
                host_id = response.get("id")
                host_name = response.get("name")

                # Clear state after successful creation
                self._clear_state()

                # Show success notification
                self.notify(
                    f"[green]✓[/green] Host '{host_name}' created (ID: {host_id})", severity="information", timeout=5
                )

                # Close the screen
                self.app.pop_screen()

        except Exception as e:
            # Show error notification
            error_msg = str(e)
            self.notify(f"[red]✗[/red] Failed to create host: {error_msg}", severity="error", timeout=10)

    def action_clear_form(self) -> None:
        """Clear all form fields"""
        # Clear text inputs
        for field_id in ["name", "description"]:
            widget = self.query_one(f"#{field_id}", Input)
            widget.value = ""

        # Reset select widgets to first option
        inventory_widget = self.query_one("#inventory", Select)
        if inventory_widget._options:
            inventory_widget.value = inventory_widget._options[0][1]

        # Reset enabled checkbox
        enabled_widget = self.query_one("#enabled", Checkbox)
        enabled_widget.value = True

        # Reset variables TextArea
        variables_widget = self.query_one("#variables_area", TextArea)
        variables_widget.text = "{\n  \n}"

        # Clear saved state
        self._clear_state()

        self.notify("Form cleared", timeout=2)

    def action_reload_dropdowns(self) -> None:
        """Reload dropdown data from API"""
        self.notify("Reloading dropdown data...", timeout=2)
        # Run async reload in worker
        self.run_worker(self._reload_dropdowns_async())

    async def _reload_dropdowns_async(self) -> None:
        """Async method to reload all dropdown data"""
        # Re-fetch all dropdown data
        await self._populate_inventories()
        self.notify("Dropdown data reloaded", timeout=2)

    def action_preview_json(self) -> None:
        """Preview the JSON payload that will be sent to the API"""
        from awx_tui.modals.json_preview import JsonPreviewModal

        # Build host data from current form values (no validation)
        host_data, notes = self._build_host_data_for_preview()

        # Show the JSON preview modal
        self.app.push_screen(
            JsonPreviewModal(
                json_data=host_data,
                title="Host Creation - API Payload Preview",
                endpoint="/api/v2/hosts/",
                method="POST",
                notes=notes,
            )
        )

    def _build_host_data_for_preview(self) -> tuple:
        """Build host data dict from current form values (for preview, no validation)

        Returns:
            tuple: (host_data dict, notes list)
        """
        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get Select values
        inventory_id = self.query_one("#inventory", Select).value
        if inventory_id is Select.BLANK:
            inventory_id = None

        # Get enabled checkbox
        enabled = self.query_one("#enabled", Checkbox).value

        # Get variables
        variables_text = self.query_one("#variables_area", TextArea).text.strip()

        # Build host data
        host_data = {
            "name": name or "REQUIRED",
            "description": description,
            "inventory": inventory_id or "REQUIRED",
            "enabled": enabled,
        }

        # Add variables if provided
        if variables_text:
            try:
                variables_dict = json.loads(variables_text)
                host_data["variables"] = json.dumps(variables_dict)
            except json.JSONDecodeError:
                host_data["variables"] = "INVALID_JSON"

        # No additional notes for hosts
        notes = []

        return host_data, notes

    def action_close(self) -> None:
        """Close create hosts screen and save state"""
        # Save state before closing
        self._save_state()
        self.app.pop_screen()

    def action_show_info(self) -> None:
        """Show info/about modal"""
        from awx_tui.modals.info import InfoModal

        app_name = self.app.current_app_name if hasattr(self.app, "current_app_name") else "AWX TUI"
        self.app.push_screen(InfoModal(app_name))

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()

    def action_export_task(self) -> None:
        """Export host as Ansible task using awx.awx.host module"""
        from awx_tui.modals.task_export import TaskExportModal
        from awx_tui.utils.ansible_mapper import host_to_ansible_task

        # Build host data with resolved names
        host_data = self._build_ansible_task_data()

        # Convert to Ansible task YAML
        yaml_str, notes = host_to_ansible_task(host_data)

        # Show export modal
        self.app.push_screen(
            TaskExportModal(
                task_yaml=yaml_str,
                title="Export AP Task - Host",
                module_name="host",
                notes=notes,
            )
        )

    def _build_ansible_task_data(self) -> dict:
        """Build host data dict with resolved dropdown names for Ansible task export

        Returns:
            dict: Host data with names instead of IDs where possible
        """
        import json

        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()
        enabled = self.query_one("#enabled", Checkbox).value

        # Get inventory ID and resolve to name
        inventory_id = self.query_one("#inventory", Select).value
        inventory_name = None
        if inventory_id and inventory_id is not Select.BLANK:
            inv_select = self.query_one("#inventory", Select)
            # Find the selected option's display name
            for option in inv_select._options:
                if option[1] == inventory_id:
                    inventory_name = option[0]
                    break

        # Get variables
        variables_text = self.query_one("#variables_area", TextArea).text.strip()
        variables_dict = None
        if variables_text:
            try:
                variables_dict = json.loads(variables_text)
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON for export

        # Build host data
        host_data = {
            "name": name,
        }

        if description:
            host_data["description"] = description

        # Add inventory (prefer name, fallback to ID)
        if inventory_name:
            host_data["inventory_name"] = inventory_name
        elif inventory_id and inventory_id is not Select.BLANK:
            host_data["inventory"] = inventory_id

        # Only include enabled if False (default is True)
        if enabled is False:
            host_data["enabled"] = False

        # Add variables if valid
        if variables_dict:
            host_data["variables"] = variables_dict

        return host_data
