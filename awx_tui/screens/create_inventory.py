"""
AWX TUI - Create Inventory Screen

Full-screen form for creating new AWX inventories.
Part of Create Mode - access via 'C' key -> '4' or select Inventory from menu.
"""

import json
from typing import List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Select, SelectionList, Static, TextArea
from textual.widgets.selection_list import Selection


class CreateInventoryScreen(Screen):
    """
    Create Inventory - Form for creating new AWX inventory

    Features:
    - Basic inventory creation (name, description, organization)
    - Instance groups multi-select
    - Variables (JSON format)
    - State persistence (survives navigation to other create screens)
    - Number keys (1-5) to navigate to other create screens
    """

    CSS = """
    CreateInventoryScreen {
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

    SelectionList {
        height: 4;
        border: solid $accent;
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
        self.create_type = "inventory"

    def compose(self) -> ComposeResult:
        """Create the form layout"""
        # Top panel with app and instance info
        yield Static("", id="top_panel")

        with ScrollableContainer(id="form_container"):
            # Top row: Basic Info and Instance Groups side-by-side (50/50 split)
            with Horizontal(id="top_sections"):
                # Basic Information Section (left half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Basic Information", classes="section_title")

                    with Horizontal():
                        yield Static("Name *:", classes="field_label")
                        yield Input(placeholder="Inventory name (required)", id="name", classes="field_input")

                    with Horizontal():
                        yield Static("Description:", classes="field_label")
                        yield Input(placeholder="Optional description", id="description", classes="field_input")

                    with Horizontal():
                        yield Static("Organization *:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="organization", classes="field_input", allow_blank=True
                        )

                # Instance Groups and Labels Section (right half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Instance Groups (Optional)", classes="section_title")
                    yield SelectionList[int](id="instance_groups_list")

                    yield Static("Labels (Optional)", classes="section_title")
                    yield SelectionList[int](id="labels_list")

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
        self.title = f"{app_name} - Create Inventory for {instance_name}"

        # Update top panel (single line, accent colored)
        top_panel = self.query_one("#top_panel", Static)
        top_panel.update(f"[bold]{app_name}[/bold] - [bold $accent]Create Inventory for {instance_name}[/bold $accent]")

        # Fetch and populate organizations, instance groups, and labels
        await self._populate_organizations()
        await self._populate_instance_groups()
        await self._populate_labels()

        # Load saved state from app
        self._load_state()

    async def _populate_organizations(self) -> None:
        """Fetch organizations from API and populate dropdown"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            org_select = self.query_one("#organization", Select)
            current_value = org_select.value

            async with client:
                # Fetch organizations
                response = await client.get("organizations/")
                orgs = response.get("results", [])

                # Build options: (display_name, org_id)
                options = [(org["name"], org["id"]) for org in orgs]

                # Populate select
                org_select.set_options(options)

                # Restore previous selection if it still exists
                if current_value is not None:
                    option_ids = [opt[1] for opt in options]
                    if current_value in option_ids:
                        org_select.value = current_value

        except Exception as e:
            self.notify(f"Failed to load organizations: {e}", severity="warning", timeout=3)

    async def _populate_instance_groups(self) -> None:
        """Fetch instance groups from API and populate multi-select list"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            ig_list = self.query_one("#instance_groups_list", SelectionList)

            async with client:
                # Fetch instance groups
                response = await client.get("instance_groups/", params={"page_size": 100})
                instance_groups = response.get("results", [])

                # Clear existing options
                ig_list.clear_options()

                # Build options - Selection takes (prompt, value, initial_state)
                for ig in instance_groups:
                    ig_name = ig.get("name", "Unknown")
                    ig_id = ig.get("id")
                    ig_list.add_option(Selection(ig_name, ig_id, initial_state=False))

        except Exception as e:
            self.notify(f"Failed to load instance groups: {e}", severity="warning", timeout=3)

    async def _populate_labels(self) -> None:
        """Fetch labels from API and populate multi-select list"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            labels_list = self.query_one("#labels_list", SelectionList)

            async with client:
                # Fetch labels
                response = await client.get("labels/", params={"page_size": 100})
                labels = response.get("results", [])

                # Clear existing options
                labels_list.clear_options()

                # Build options - Selection takes (prompt, value, initial_state)
                for label in labels:
                    label_name = label.get("name", "Unknown")
                    label_id = label.get("id")
                    labels_list.add_option(Selection(label_name, label_id, initial_state=False))

        except Exception as e:
            self.notify(f"Failed to load labels: {e}", severity="warning", timeout=3)

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
        if "organization" in state:
            widget = self.query_one("#organization", Select)
            widget.value = state["organization"]

        # Restore instance groups selection
        if "instance_groups" in state:
            ig_list = self.query_one("#instance_groups_list", SelectionList)
            selected_ids = state["instance_groups"]
            for ig_id in selected_ids:
                try:
                    ig_list.select(ig_id)
                except Exception:
                    pass  # Option may not exist anymore

        # Restore labels selection
        if "labels" in state:
            labels_list = self.query_one("#labels_list", SelectionList)
            selected_ids = state["labels"]
            for label_id in selected_ids:
                try:
                    labels_list.select(label_id)
                except Exception:
                    pass  # Option may not exist anymore

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
        org_widget = self.query_one("#organization", Select)
        state["organization"] = org_widget.value

        # Save instance groups selection
        ig_list = self.query_one("#instance_groups_list", SelectionList)
        state["instance_groups"] = list(ig_list.selected)

        # Save labels selection
        labels_list = self.query_one("#labels_list", SelectionList)
        state["labels"] = list(labels_list.selected)

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
        if create_type == "inventory":
            # Already on inventory screen, do nothing
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
        elif create_type == "hosts":
            from awx_tui.screens.create_hosts import CreateHostsScreen

            self.app.pop_screen()
            self.app.push_screen(CreateHostsScreen())

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
        organization_id = self.query_one("#organization", Select).value
        if organization_id is Select.BLANK:
            organization_id = None

        # Get instance groups selection
        ig_list = self.query_one("#instance_groups_list", SelectionList)
        selected_ig_ids = list(ig_list.selected)

        # Get labels selection
        labels_list = self.query_one("#labels_list", SelectionList)
        selected_label_ids = list(labels_list.selected)

        # Get variables
        variables_text = self.query_one("#variables_area", TextArea).text.strip()

        # Validate required fields
        if not name:
            self.notify("Inventory name is required", severity="error", timeout=3)
            self.query_one("#name", Input).focus()
            return

        if not organization_id:
            self.notify("Organization is required", severity="error", timeout=3)
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

        # Build inventory data
        inventory_data = {
            "name": name,
            "description": description,
            "organization": organization_id,
        }

        # Add optional fields
        if variables_dict:
            inventory_data["variables"] = json.dumps(variables_dict)

        # Create the inventory via API (async)
        self.run_worker(self._create_inventory_async(inventory_data, name, selected_ig_ids, selected_label_ids))

    async def _create_inventory_async(
        self, inventory_data: dict, name: str, instance_group_ids: List[int], label_ids: List[int]
    ) -> None:
        """Async method to create inventory via API"""
        try:
            self.notify(f"Creating inventory '{name}'...", timeout=2)

            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            async with client:
                # POST to /api/v2/inventories/
                response = await client.post("inventories/", data=inventory_data)
                inventory_id = response.get("id")
                inventory_name = response.get("name")

                # Associate instance groups if any were selected
                if instance_group_ids:
                    for ig_id in instance_group_ids:
                        try:
                            await client.post(f"inventories/{inventory_id}/instance_groups/", data={"id": ig_id})
                        except Exception as e:
                            self.app.log.warning(f"Failed to associate instance group {ig_id}: {e}")

                # Associate labels if any were selected
                if label_ids:
                    for label_id in label_ids:
                        try:
                            await client.post(f"inventories/{inventory_id}/labels/", data={"id": label_id})
                        except Exception as e:
                            self.app.log.warning(f"Failed to associate label {label_id}: {e}")

                # Clear state after successful creation
                self._clear_state()

                # Show success notification
                self.notify(
                    f"[green]✓[/green] Inventory '{inventory_name}' created (ID: {inventory_id})",
                    severity="information",
                    timeout=5,
                )

                # Close the screen
                self.app.pop_screen()

        except Exception as e:
            # Show error notification
            error_msg = str(e)
            self.notify(f"[red]✗[/red] Failed to create inventory: {error_msg}", severity="error", timeout=10)

    def action_clear_form(self) -> None:
        """Clear all form fields"""
        # Clear text inputs
        for field_id in ["name", "description"]:
            widget = self.query_one(f"#{field_id}", Input)
            widget.value = ""

        # Reset select widgets to first option
        org_widget = self.query_one("#organization", Select)
        if org_widget._options:
            org_widget.value = org_widget._options[0][1]

        # Clear instance groups selection
        ig_list = self.query_one("#instance_groups_list", SelectionList)
        ig_list.deselect_all()

        # Clear labels selection
        labels_list = self.query_one("#labels_list", SelectionList)
        labels_list.deselect_all()

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
        await self._populate_organizations()
        await self._populate_instance_groups()
        await self._populate_labels()
        self.notify("Dropdown data reloaded", timeout=2)

    def action_preview_json(self) -> None:
        """Preview the JSON payload that will be sent to the API"""
        from awx_tui.modals.json_preview import JsonPreviewModal

        # Build inventory data from current form values (no validation)
        inventory_data, notes = self._build_inventory_data_for_preview()

        # Show the JSON preview modal
        self.app.push_screen(
            JsonPreviewModal(
                json_data=inventory_data,
                title="Inventory Creation - API Payload Preview",
                endpoint="/api/v2/inventories/",
                method="POST",
                notes=notes,
            )
        )

    def _build_inventory_data_for_preview(self) -> tuple:
        """Build inventory data dict from current form values (for preview, no validation)

        Returns:
            tuple: (inventory_data dict, notes list)
        """
        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get Select values
        organization_id = self.query_one("#organization", Select).value
        if organization_id is Select.BLANK:
            organization_id = None

        # Get instance groups and labels selection
        ig_list = self.query_one("#instance_groups_list", SelectionList)
        selected_ig_ids = list(ig_list.selected)

        labels_list = self.query_one("#labels_list", SelectionList)
        selected_label_ids = list(labels_list.selected)

        # Get variables
        variables_text = self.query_one("#variables_area", TextArea).text.strip()

        # Build inventory data
        inventory_data = {
            "name": name or "REQUIRED",
            "description": description,
            "organization": organization_id or "REQUIRED",
        }

        # Add variables if provided
        if variables_text:
            try:
                variables_dict = json.loads(variables_text)
                inventory_data["variables"] = json.dumps(variables_dict)
            except json.JSONDecodeError:
                inventory_data["variables"] = "INVALID_JSON"

        # Build notes for additional context
        notes = []
        if selected_ig_ids:
            notes.append(
                f"Instance groups {selected_ig_ids} will be associated via separate POST to /api/v2/inventories/{{id}}/instance_groups/"
            )
        if selected_label_ids:
            notes.append(
                f"Labels {selected_label_ids} will be associated via separate POST to /api/v2/inventories/{{id}}/labels/"
            )

        return inventory_data, notes

    def action_close(self) -> None:
        """Close create inventory screen and save state"""
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
        """Export inventory as Ansible task using awx.awx.inventory module"""
        from awx_tui.modals.task_export import TaskExportModal
        from awx_tui.utils.ansible_mapper import inventory_to_ansible_task

        # Build inventory data with resolved names
        inventory_data = self._build_ansible_task_data()

        # Convert to Ansible task YAML
        yaml_str, notes = inventory_to_ansible_task(inventory_data)

        # Show export modal
        self.app.push_screen(
            TaskExportModal(
                task_yaml=yaml_str,
                title="Export AP Task - Inventory",
                module_name="inventory",
                notes=notes,
            )
        )

    def _build_ansible_task_data(self) -> dict:
        """Build inventory data dict with resolved dropdown names for Ansible task export

        Returns:
            dict: Inventory data with names instead of IDs where possible
        """
        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get organization ID and resolve to name
        organization_id = self.query_one("#organization", Select).value
        organization_name = None
        if organization_id and organization_id is not Select.BLANK:
            org_select = self.query_one("#organization", Select)
            # Find the selected option's display name
            for option in org_select._options:
                if option[1] == organization_id:
                    organization_name = option[0]
                    break

        # Get variables
        variables_text = self.query_one("#variables_area", TextArea).text.strip()
        variables_dict = None
        if variables_text:
            try:
                variables_dict = json.loads(variables_text)
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON for export

        # Build inventory data
        inventory_data = {
            "name": name,
        }

        if description:
            inventory_data["description"] = description

        # Add organization (prefer name, fallback to ID)
        if organization_name:
            inventory_data["organization_name"] = organization_name
        elif organization_id and organization_id is not Select.BLANK:
            inventory_data["organization"] = organization_id

        # Add variables if valid
        if variables_dict:
            inventory_data["variables"] = variables_dict

        return inventory_data
