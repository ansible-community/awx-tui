"""
AWX TUI - Update Inventory Screen

Full-screen editor for managing inventory and its hosts.
Accessed by selecting an inventory from the Inventories screen.
"""

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, SelectionList, Static, TextArea
from textual.widgets.selection_list import Selection


class UpdateInventoryScreen(Screen):
    """
    Update Inventory - Manage inventory properties and hosts

    Features:
    - Edit inventory name, description, variables
    - View and manage hosts in inventory
    - Add new hosts to inventory
    - Edit existing hosts
    - Remove hosts from inventory
    - Toggle host enabled state (Ctrl+X)
    """

    CSS = """
    UpdateInventoryScreen {
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
        height: 16;
        overflow-y: auto;
        margin-right: 1;
    }

    .form_section_half:last-child {
        margin-right: 0;
    }

    .section_title {
        text-style: bold;
        color: $primary;
        margin-top: 0;
        margin-bottom: 1;
    }

    .form_section_half .section_title {
        margin-top: 0;
        margin-bottom: 0;
    }

    #hosts_title {
        margin-top: 1;
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

    #hosts_table {
        height: 7;
        border: solid $accent;
    }

    #button_container {
        height: 3;
        align: center middle;
        margin-bottom: 1;
    }

    Button {
        margin: 0 1;
    }

    Button:disabled {
        opacity: 0.5;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=True, priority=True),
        Binding("i", "show_info", "Info", show=True),
        Binding("ctrl+x", "toggle_enabled", "Toggle Enabled", show=True),
        Binding("enter", "edit_host", "Edit Host", show=True),
        Binding("ctrl+j", "preview_json", "Preview JSON", show=True),
        Binding("ctrl+e", "export_task", "Export AP Task", show=True),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]

    def __init__(self, inventory_id: int, **kwargs):
        super().__init__(**kwargs)
        self.inventory_id = inventory_id
        self.is_dirty = False  # Track if inventory fields modified
        self.original_data = {}  # Store original inventory data
        self.hosts_data = []  # Store hosts for this inventory

    def compose(self) -> ComposeResult:
        """Create the form layout"""
        # Top panel with app and instance info
        yield Static("", id="top_panel")

        with ScrollableContainer(id="form_container"):
            # Top row: Basic Info + Hosts (left) and Instance Groups/Labels (right) - 50/50 split
            with Horizontal(id="top_sections"):
                # Left half: Basic Information + Hosts
                with Container(classes="form_section form_section_half"):
                    yield Static("Basic Information", classes="section_title")

                    with Horizontal():
                        yield Static("Name *:", classes="field_label")
                        yield Input(placeholder="Inventory name (required)", id="name", classes="field_input")

                    with Horizontal():
                        yield Static("Description:", classes="field_label")
                        yield Input(placeholder="Optional description", id="description", classes="field_input")

                    with Horizontal():
                        yield Static("Organization:", classes="field_label")
                        yield Static("", id="organization_display", classes="field_input")

                    # Hosts Section (moved under Basic Information)
                    yield Static("Hosts in this Inventory", classes="section_title", id="hosts_title")
                    yield DataTable(id="hosts_table", cursor_type="row")

                # Right half: Instance Groups + Labels
                with Container(classes="form_section form_section_half"):
                    yield Static("Instance Groups (Optional)", classes="section_title")
                    yield SelectionList[int](id="instance_groups_list")

                    yield Static("Labels (Optional)", classes="section_title")
                    yield SelectionList[int](id="labels_list")

            # Variables Section (full width)
            with Container(classes="form_section", id="variables_section"):
                yield Static("Variables (JSON)", classes="section_title")
                yield TextArea("{\n  \n}", language="json", id="variables_area")

            # All buttons in one line at the bottom
            with Horizontal(id="button_container"):
                yield Button("Save Changes", id="save_button", variant="primary", disabled=True)
                yield Button("Add Host", id="add_host_button", variant="success")
                yield Button("Remove Host", id="remove_host_button", variant="error", disabled=True)
                yield Button("Cancel", id="cancel_button", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize screen and load inventory data"""
        # Update top panel
        app_name = self.app.current_app_name if hasattr(self.app, "current_app_name") else "AWX TUI"
        instance_name = self.app.instance_manager.current_instance if self.app.instance_manager else "No Instance"

        top_panel = self.query_one("#top_panel", Static)
        top_panel.update(f"[bold $accent]{app_name} - Update Inventory @ {instance_name}[/bold $accent]")

        # Set up hosts table
        hosts_table = self.query_one("#hosts_table", DataTable)
        hosts_table.add_columns("ID", "Name", "Description", "Enabled")

        # Load instance groups and labels options
        await self._populate_instance_groups()
        await self._populate_labels()

        # Load inventory data
        await self._load_inventory_data()
        await self._load_hosts_data()

    async def _load_inventory_data(self) -> None:
        """Load inventory data from API"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    inventory = await client.get(f"/api/v2/inventories/{self.inventory_id}/")
            else:
                inventory = await client.get(f"/api/v2/inventories/{self.inventory_id}/")

            # Store original data
            self.original_data = inventory
            summary = inventory.get("summary_fields", {})

            # Populate form fields
            name_input = self.query_one("#name", Input)
            description_input = self.query_one("#description", Input)
            variables_area = self.query_one("#variables_area", TextArea)
            org_display = self.query_one("#organization_display", Static)

            name_input.value = inventory.get("name", "")
            description_input.value = inventory.get("description", "")

            # Display organization (read-only)
            org_name = summary.get("organization", {}).get("name", "N/A")
            org_display.update(org_name)

            # Format variables as JSON
            variables = inventory.get("variables", "")
            if variables:
                try:
                    # If variables is a string, parse it
                    if isinstance(variables, str):
                        variables_dict = json.loads(variables) if variables else {}
                    else:
                        variables_dict = variables
                    variables_area.text = json.dumps(variables_dict, indent=2)
                except:
                    variables_area.text = variables if variables else "{\n  \n}"
            else:
                variables_area.text = "{\n  \n}"

            # Pre-select instance groups and labels from summary_fields
            # Select instance groups
            instance_groups = summary.get("instance_groups", {}).get("results", [])
            ig_list = self.query_one("#instance_groups_list", SelectionList)
            for ig in instance_groups:
                ig_id = ig.get("id")
                if ig_id:
                    ig_list.select(ig_id)

            # Select labels
            labels = summary.get("labels", {}).get("results", [])
            labels_list = self.query_one("#labels_list", SelectionList)
            for label in labels:
                label_id = label.get("id")
                if label_id:
                    labels_list.select(label_id)

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to load inventory: {e}\n{traceback.format_exc()}")
            self.notify(f"Error loading inventory: {e}", severity="error")

    async def _load_hosts_data(self) -> None:
        """Load hosts for this inventory"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    response = await client.get(
                        f"/api/v2/inventories/{self.inventory_id}/hosts/", params={"page_size": 200}
                    )
            else:
                response = await client.get(
                    f"/api/v2/inventories/{self.inventory_id}/hosts/", params={"page_size": 200}
                )

            self.hosts_data = response.get("results", [])
            self._update_hosts_table()

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to load hosts: {e}\n{traceback.format_exc()}")
            self.notify(f"Error loading hosts: {e}", severity="error")

    async def _populate_instance_groups(self) -> None:
        """Fetch instance groups from API and populate multi-select list"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            ig_list = self.query_one("#instance_groups_list", SelectionList)

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    response = await client.get("/api/v2/instance_groups/", params={"page_size": 100})
            else:
                response = await client.get("/api/v2/instance_groups/", params={"page_size": 100})

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

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    response = await client.get("/api/v2/labels/", params={"page_size": 100})
            else:
                response = await client.get("/api/v2/labels/", params={"page_size": 100})

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

    def _update_hosts_table(self) -> None:
        """Update hosts DataTable"""
        hosts_table = self.query_one("#hosts_table", DataTable)

        # Save current selection
        selected_host_id = None
        cursor_row = 0
        if hosts_table.cursor_coordinate and hosts_table.row_count > 0:
            cursor_row = hosts_table.cursor_coordinate[0]
            try:
                selected_host_id = hosts_table.get_row_at(cursor_row)[0]
            except:
                pass

        hosts_table.clear()

        # Sort hosts by name
        sorted_hosts = sorted(self.hosts_data, key=lambda h: h.get("name", "").lower())

        new_cursor_row = 0
        for idx, host in enumerate(sorted_hosts):
            host_id = str(host.get("id", 0))
            name = host.get("name", "Unknown")[:40]
            description = host.get("description", "")[:50]
            enabled = host.get("enabled", True)
            enabled_emoji = "[green]✓[/green]" if enabled else "[red]✗[/red]"

            # Track if this is the previously selected host
            if selected_host_id and host_id == selected_host_id:
                new_cursor_row = idx

            hosts_table.add_row(host_id, name, description, enabled_emoji)

        # Restore cursor position
        if hosts_table.row_count > 0:
            if new_cursor_row < hosts_table.row_count:
                hosts_table.cursor_coordinate = (new_cursor_row, 0)

        # Enable/disable Remove Host button based on selection
        remove_button = self.query_one("#remove_host_button", Button)
        remove_button.disabled = hosts_table.row_count == 0

    def _mark_dirty(self) -> None:
        """Mark form as dirty and enable Save Changes button"""
        if not self.is_dirty:
            self.is_dirty = True
            save_button = self.query_one("#save_button", Button)
            save_button.disabled = False

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes - mark form as dirty"""
        if event.input.id in ("name", "description"):
            self._mark_dirty()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes - mark form as dirty"""
        if event.text_area.id == "variables_area":
            self._mark_dirty()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "save_button":
            self.run_worker(self._save_inventory())
        elif event.button.id == "add_host_button":
            self.run_worker(self._show_add_host_modal())
        elif event.button.id == "remove_host_button":
            self.run_worker(self._remove_host())
        elif event.button.id == "cancel_button":
            self.action_close()

    def action_preview_json(self) -> None:
        """Preview the JSON payload that will be sent to the API"""
        from awx_tui.modals.json_preview import JsonPreviewModal

        # Build inventory data from current form values (no validation)
        inventory_data, notes = self._build_inventory_data_for_preview()

        # Show the JSON preview modal
        self.app.push_screen(
            JsonPreviewModal(
                json_data=inventory_data,
                title="Inventory Update - API Payload Preview",
                endpoint=f"/api/v2/inventories/{self.inventory_id}/",
                method="PATCH",
                notes=notes,
            )
        )

    def _build_inventory_data_for_preview(self) -> tuple:
        """Build inventory data dict from current form values (for preview, no validation)

        Returns:
            tuple: (inventory_data dict, notes list)
        """
        # Get form values
        name_input = self.query_one("#name", Input)
        description_input = self.query_one("#description", Input)
        variables_area = self.query_one("#variables_area", TextArea)

        # Parse variables (lenient, no validation)
        variables_text = variables_area.text.strip()
        try:
            variables_dict = json.loads(variables_text) if variables_text else {}
        except json.JSONDecodeError:
            variables_dict = {}  # Preview continues even with invalid JSON

        inventory_data = {
            "name": name_input.value.strip(),
            "description": description_input.value.strip(),
            "variables": json.dumps(variables_dict) if variables_dict else "",
        }

        # Build notes
        notes = []
        notes.append(f"PATCH to /api/v2/inventories/{self.inventory_id}/")

        # Note: Instance groups and labels are associated via separate POST requests
        # These are not included in the PATCH payload
        instance_groups_list = self.query_one("#instance_groups_list", SelectionList)
        labels_list = self.query_one("#labels_list", SelectionList)

        if instance_groups_list.selected:
            notes.append(
                f"Instance groups {list(instance_groups_list.selected)} will be associated via separate POST to /api/v2/inventories/{self.inventory_id}/instance_groups/"
            )

        if labels_list.selected:
            notes.append(
                f"Labels {list(labels_list.selected)} will be associated via separate POST to /api/v2/inventories/{self.inventory_id}/labels/"
            )

        return inventory_data, notes

    async def _save_inventory(self) -> None:
        """Save inventory changes"""
        # Validate required fields
        name_input = self.query_one("#name", Input)
        if not name_input.value.strip():
            self.notify("Name is required", severity="error")
            name_input.focus()
            return

        # Validate JSON variables
        variables_area = self.query_one("#variables_area", TextArea)
        variables_text = variables_area.text.strip()

        if variables_text:
            try:
                variables_dict = json.loads(variables_text)
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON in variables: {e}", severity="error", timeout=5)
                variables_area.focus()
                return
        else:
            variables_dict = {}

        # Build update payload
        description_input = self.query_one("#description", Input)

        inventory_data = {
            "name": name_input.value.strip(),
            "description": description_input.value.strip(),
            "variables": json.dumps(variables_dict) if variables_dict else "",
        }

        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    response = await client.patch(f"/api/v2/inventories/{self.inventory_id}/", data=inventory_data)

                    # Update instance groups associations
                    ig_list = self.query_one("#instance_groups_list", SelectionList)
                    selected_igs = set(ig_list.selected)
                    original_igs = set(
                        ig.get("id")
                        for ig in self.original_data.get("summary_fields", {})
                        .get("instance_groups", {})
                        .get("results", [])
                    )

                    # Add new instance groups
                    for ig_id in selected_igs - original_igs:
                        await client.post(
                            f"/api/v2/inventories/{self.inventory_id}/instance_groups/", data={"id": ig_id}
                        )

                    # Remove unselected instance groups
                    for ig_id in original_igs - selected_igs:
                        await client.post(
                            f"/api/v2/inventories/{self.inventory_id}/instance_groups/",
                            data={"id": ig_id, "disassociate": True},
                        )

                    # Update labels associations
                    labels_list = self.query_one("#labels_list", SelectionList)
                    selected_labels = set(labels_list.selected)
                    original_labels = set(
                        label.get("id")
                        for label in self.original_data.get("summary_fields", {}).get("labels", {}).get("results", [])
                    )

                    # Add new labels
                    for label_id in selected_labels - original_labels:
                        await client.post(f"/api/v2/inventories/{self.inventory_id}/labels/", data={"id": label_id})

                    # Remove unselected labels
                    for label_id in original_labels - selected_labels:
                        await client.post(
                            f"/api/v2/inventories/{self.inventory_id}/labels/",
                            data={"id": label_id, "disassociate": True},
                        )

            else:
                response = await client.patch(f"/api/v2/inventories/{self.inventory_id}/", data=inventory_data)

                # Update instance groups associations
                ig_list = self.query_one("#instance_groups_list", SelectionList)
                selected_igs = set(ig_list.selected)
                original_igs = set(
                    ig.get("id")
                    for ig in self.original_data.get("summary_fields", {}).get("instance_groups", {}).get("results", [])
                )

                # Add new instance groups
                for ig_id in selected_igs - original_igs:
                    await client.post(f"/api/v2/inventories/{self.inventory_id}/instance_groups/", data={"id": ig_id})

                # Remove unselected instance groups
                for ig_id in original_igs - selected_igs:
                    await client.post(
                        f"/api/v2/inventories/{self.inventory_id}/instance_groups/",
                        data={"id": ig_id, "disassociate": True},
                    )

                # Update labels associations
                labels_list = self.query_one("#labels_list", SelectionList)
                selected_labels = set(labels_list.selected)
                original_labels = set(
                    label.get("id")
                    for label in self.original_data.get("summary_fields", {}).get("labels", {}).get("results", [])
                )

                # Add new labels
                for label_id in selected_labels - original_labels:
                    await client.post(f"/api/v2/inventories/{self.inventory_id}/labels/", data={"id": label_id})

                # Remove unselected labels
                for label_id in original_labels - selected_labels:
                    await client.post(
                        f"/api/v2/inventories/{self.inventory_id}/labels/", data={"id": label_id, "disassociate": True}
                    )

            self.notify(f"[green]✓[/green] Inventory '{name_input.value}' updated successfully!", timeout=5)

            # Reset dirty state
            self.is_dirty = False
            save_button = self.query_one("#save_button", Button)
            save_button.disabled = True

            # Update original data
            self.original_data = response

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to save inventory: {e}\n{traceback.format_exc()}")
            self.notify(f"[red]✗[/red] Failed to save inventory: {e}", severity="error", timeout=5)

    async def _show_add_host_modal(self) -> None:
        """Show modal to add new host"""
        from awx_tui.modals.host_edit import HostEditModal

        # Get inventory name from loaded data
        inventory_name = self.original_data.get("name", "Unknown")

        # Show modal in create mode
        result = await self.app.push_screen_wait(
            HostEditModal(inventory_id=self.inventory_id, inventory_name=inventory_name)
        )

        if result:
            # Reload hosts data
            await self._load_hosts_data()
            self.notify("Host added successfully!", timeout=3)

    async def _remove_host(self) -> None:
        """Remove selected host from inventory"""
        hosts_table = self.query_one("#hosts_table", DataTable)

        if not hosts_table.cursor_coordinate or hosts_table.row_count == 0:
            self.notify("No host selected", severity="warning")
            return

        try:
            cursor_row = hosts_table.cursor_coordinate[0]
            host_id = int(hosts_table.get_row_at(cursor_row)[0])
            host_name = hosts_table.get_row_at(cursor_row)[1]

            # Find host data
            host = None
            for h in self.hosts_data:
                if h.get("id") == host_id:
                    host = h
                    break

            if not host:
                self.notify("Host not found", severity="error")
                return

            # Confirm removal
            from awx_tui.modals.confirm_remove_host import ConfirmRemoveHostModal

            confirmed = await self.app.push_screen_wait(
                ConfirmRemoveHostModal(
                    f"Remove host [bold]'{host_name}'[/bold] from this inventory?",
                    "This will disassociate the host but not delete it.",
                )
            )

            if not confirmed:
                return

            # Disassociate host
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            disassociate_data = {"id": host_id, "disassociate": True}

            if isinstance(client, AWXClient):
                async with client:
                    await client.post(f"/api/v2/inventories/{self.inventory_id}/hosts/", data=disassociate_data)
            else:
                await client.post(f"/api/v2/inventories/{self.inventory_id}/hosts/", data=disassociate_data)

            self.notify(f"[green]✓[/green] Host '{host_name}' removed from inventory", timeout=3)

            # Reload hosts
            await self._load_hosts_data()

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to remove host: {e}\n{traceback.format_exc()}")
            self.notify(f"[red]✗[/red] Failed to remove host: {e}", severity="error", timeout=5)

    def action_edit_host(self) -> None:
        """Edit selected host (Enter key)"""
        self.run_worker(self._show_edit_host_modal())

    async def _show_edit_host_modal(self) -> None:
        """Show modal to edit selected host"""
        hosts_table = self.query_one("#hosts_table", DataTable)

        if not hosts_table.cursor_coordinate or hosts_table.row_count == 0:
            self.notify("No host selected", severity="warning")
            return

        try:
            cursor_row = hosts_table.cursor_coordinate[0]
            host_id = int(hosts_table.get_row_at(cursor_row)[0])

            # Find host data
            host = None
            for h in self.hosts_data:
                if h.get("id") == host_id:
                    host = h
                    break

            if not host:
                self.notify("Host not found", severity="error")
                return

            from awx_tui.modals.host_edit import HostEditModal

            # Get inventory name from loaded data
            inventory_name = self.original_data.get("name", "Unknown")

            # Show modal in edit mode
            result = await self.app.push_screen_wait(
                HostEditModal(inventory_id=self.inventory_id, host_data=host, inventory_name=inventory_name)
            )

            if result:
                # Reload hosts data
                await self._load_hosts_data()
                self.notify("Host updated successfully!", timeout=3)

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to edit host: {e}\n{traceback.format_exc()}")
            self.notify(f"Error editing host: {e}", severity="error")

    def action_toggle_enabled(self) -> None:
        """Toggle enabled state of selected host (Ctrl+X)"""
        self.run_worker(self._toggle_host_enabled())

    async def _toggle_host_enabled(self) -> None:
        """Toggle the enabled state of the selected host"""
        hosts_table = self.query_one("#hosts_table", DataTable)

        if not hosts_table.cursor_coordinate or hosts_table.row_count == 0:
            self.notify("No host selected", severity="warning")
            return

        try:
            cursor_row = hosts_table.cursor_coordinate[0]
            host_id = int(hosts_table.get_row_at(cursor_row)[0])
            host_name = hosts_table.get_row_at(cursor_row)[1]

            # Find host data
            host = None
            for h in self.hosts_data:
                if h.get("id") == host_id:
                    host = h
                    break

            if not host:
                self.notify("Host not found", severity="error")
                return

            # Toggle enabled state
            current_enabled = host.get("enabled", True)
            new_enabled = not current_enabled

            # Update via API
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            from awx_tui.client import AWXClient

            if isinstance(client, AWXClient):
                async with client:
                    await client.patch(f"/api/v2/hosts/{host_id}/", data={"enabled": new_enabled})
            else:
                await client.patch(f"/api/v2/hosts/{host_id}/", data={"enabled": new_enabled})

            # Update local data
            host["enabled"] = new_enabled

            # Update table (just the one row)
            enabled_emoji = "[green]✓[/green]" if new_enabled else "[red]✗[/red]"
            hosts_table.update_cell_at((cursor_row, 3), enabled_emoji)

            state_text = "enabled" if new_enabled else "disabled"
            self.notify(f"Host '{host_name}' {state_text}", timeout=2)

        except Exception as e:
            import traceback

            self.app.log.error(f"Failed to toggle host enabled: {e}\n{traceback.format_exc()}")
            self.notify(f"[red]✗[/red] Failed to toggle host: {e}", severity="error", timeout=5)

    def action_show_info(self) -> None:
        """Show info modal"""
        from awx_tui.modals.info_modal import InfoModal

        self.app.push_screen(InfoModal())

    def action_close(self) -> None:
        """Close screen and return to inventories list"""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()

    def action_export_task(self) -> None:
        """Export inventory and all hosts as Ansible tasks"""
        from awx_tui.modals.task_export import TaskExportModal
        from awx_tui.utils.ansible_mapper import host_to_ansible_task, inventory_to_ansible_task

        # Build inventory data with resolved names
        inventory_data = self._build_ansible_task_data()

        # Convert inventory to Ansible task YAML
        inventory_yaml, inventory_notes = inventory_to_ansible_task(inventory_data)

        # Combine all YAML and notes
        all_yaml_parts = [inventory_yaml]
        all_notes = list(inventory_notes)

        # Add all hosts
        inventory_name = inventory_data.get("name", "")
        if self.hosts_data:
            all_notes.append(f"Inventory contains {len(self.hosts_data)} host(s)")

            for host in self.hosts_data:
                # Build host data with inventory reference
                host_data = {
                    "name": host.get("name", ""),
                    "inventory_name": inventory_name,  # Reference the inventory by name
                }

                # Add optional fields
                if host.get("description"):
                    host_data["description"] = host["description"]

                if host.get("enabled") is False:
                    host_data["enabled"] = False

                # Parse variables if present
                variables = host.get("variables")
                if variables:
                    try:
                        import json

                        if isinstance(variables, str):
                            host_data["variables"] = json.loads(variables)
                        else:
                            host_data["variables"] = variables
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Convert host to YAML
                host_yaml, host_notes = host_to_ansible_task(host_data)
                all_yaml_parts.append(host_yaml)
                all_notes.extend(host_notes)

        # Combine all YAML parts
        combined_yaml = "\n".join(all_yaml_parts)

        # Show export modal
        self.app.push_screen(
            TaskExportModal(
                task_yaml=combined_yaml,
                title="Export AP Task - Inventory + Hosts",
                module_name="inventory",
                notes=all_notes,
            )
        )

    def _build_ansible_task_data(self) -> dict:
        """Build inventory data dict with resolved names for Ansible task export

        Returns:
            dict: Inventory data with names instead of IDs where possible
        """
        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get organization name from original_data
        organization_name = None
        if "summary_fields" in self.original_data:
            org_summary = self.original_data["summary_fields"].get("organization", {})
            organization_name = org_summary.get("name")

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

        # Add organization name if available
        if organization_name:
            inventory_data["organization_name"] = organization_name

        # Add variables if valid
        if variables_dict:
            inventory_data["variables"] = variables_dict

        return inventory_data

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Enable/disable Remove Host button based on selection"""
        remove_button = self.query_one("#remove_host_button", Button)
        hosts_table = self.query_one("#hosts_table", DataTable)
        remove_button.disabled = hosts_table.row_count == 0

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle host selection (Enter key on row)"""
        # Only handle events from hosts table
        if event.data_table.id == "hosts_table":
            self.action_edit_host()
