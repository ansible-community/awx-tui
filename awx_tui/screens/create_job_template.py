"""
AWX TUI - Create Job Template Screen

Full-screen form for creating new AWX job templates.
Part of Create Mode - access via 'C' key -> '2' or select Job Template from menu.
"""

import json
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Input, Select, SelectionList, Static, TextArea
from textual.widgets.selection_list import Selection


class CreateJobTemplateScreen(Screen):
    """
    Create Job Template - Form for creating new AWX job template

    Features:
    - Full form with all job template fields
    - Dynamic playbook loading based on selected project
    - Form validation before submit
    - State persistence (survives navigation to other create screens)
    - Clear Form button to reset
    - Number keys (1-4) to navigate to other create screens
    """

    CSS = """
    CreateJobTemplateScreen {
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
        margin-bottom: 0;
    }

    .form_section {
        border: solid $accent;
        padding: 0 1;
        margin-bottom: 0;
    }

    .form_section_half {
        width: 1fr;
        height: 16;
        overflow-y: auto;
        margin-right: 1;
        padding-bottom: 0;
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

    #extra_vars_section {
        height: auto;
        margin-bottom: 1;
    }

    #extra_vars_section .section_title {
        margin-bottom: 0;
    }

    #extra_vars_area {
        height: 5;
    }

    .inline_label {
        width: auto;
        margin-left: 2;
        margin-right: 1;
    }

    .inline_input {
        width: 15;
        margin: 0;
        padding: 0 1;
        border: none;
        height: 1;
        background: $boost;
    }

    .options_row {
        height: auto;
        padding-left: 25;
        margin: 0;
        padding-bottom: 0;
    }

    #playbook_execution_row {
        height: auto;
        width: 100%;
        margin-bottom: 0;
    }

    .execution_section_half {
        width: 50%;
        height: 7;
        border: solid $accent;
        padding: 0 1;
        margin-right: 1;
    }

    .execution_section_half:last-child {
        margin-right: 0;
    }

    .execution_section_half .section_title {
        margin-bottom: 0;
    }

    #execution_fields {
        height: auto;
        width: 100%;
    }

    .execution_inputs_column {
        width: 35%;
        height: auto;
    }

    .execution_checkboxes_column {
        width: 65%;
        height: auto;
        padding-left: 2;
    }

    .execution_field_row {
        height: auto;
        margin-bottom: 0;
    }

    .execution_label {
        width: 13;
        padding-right: 1;
        text-align: right;
    }

    .execution_input {
        width: 17;
        margin: 0;
        padding: 0 1;
        border: none;
        height: 1;
        background: $boost;
    }

    SelectionList {
        height: 4;
        border: solid $accent;
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

    # Verbosity options (0-5)
    VERBOSITY_OPTIONS = [
        ("0 (Normal)", 0),
        ("1 (Verbose)", 1),
        ("2 (More Verbose)", 2),
        ("3 (Debug)", 3),
        ("4 (Connection Debug)", 4),
        ("5 (WinRM Debug)", 5),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_type = "job_template"
        self._pending_playbook_restore = None  # Track playbook value to restore after loading

    def compose(self) -> ComposeResult:
        """Create the form layout"""
        # Top panel with app and instance info
        yield Static("", id="top_panel")

        with ScrollableContainer(id="form_container"):
            # Top row: Basic Info and Run Information sections side-by-side (50/50 split)
            with Horizontal(id="top_sections"):
                # Basic Information Section (left half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Basic Information", classes="section_title")

                    with Horizontal():
                        yield Static("Name *:", classes="field_label")
                        yield Input(placeholder="Job template name (required)", id="name", classes="field_input")

                    with Horizontal():
                        yield Static("Description:", classes="field_label")
                        yield Input(placeholder="Optional description", id="description", classes="field_input")

                    with Horizontal():
                        yield Static("Project *:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="project", classes="field_input", allow_blank=True
                        )

                    with Horizontal():
                        yield Static("Playbook *:", classes="field_label")
                        yield Select(
                            options=[("Select project first...", None)],
                            id="playbook",
                            classes="field_input",
                            allow_blank=True,
                        )

                    with Horizontal():
                        yield Static("Verbosity:", classes="field_label")
                        yield Select(
                            options=[(label, value) for label, value in self.VERBOSITY_OPTIONS],
                            value=0,
                            id="verbosity",
                            classes="field_input",
                        )

                # Run Information Section (right half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Run Information", classes="section_title")

                    with Horizontal():
                        yield Static("Execution Environment:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)],
                            id="execution_environment",
                            classes="field_input",
                            allow_blank=True,
                        )

                    with Horizontal():
                        yield Static("Inventory *:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="inventory", classes="field_input", allow_blank=True
                        )

                    with Horizontal():
                        yield Static("Limit:", classes="field_label")
                        yield Input(
                            placeholder="Ansible host pattern (e.g., webservers:dbservers)",
                            id="limit",
                            classes="field_input",
                        )

                    with Horizontal():
                        yield Static("Machine Credential:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="credential", classes="field_input", allow_blank=True
                        )

                    with Horizontal(classes="options_row"):
                        yield Checkbox("Enable Privilege Escalation", id="become_enabled")

            # Playbook Execution Section - 50/50 split
            with Horizontal(id="playbook_execution_row"):
                # Left half: Playbook Execution fields
                with Container(classes="execution_section_half"):
                    yield Static("Playbook Execution", classes="section_title")

                    with Horizontal(id="execution_fields"):
                        # Left side: inputs
                        with Vertical(classes="execution_inputs_column"):
                            with Horizontal(classes="execution_field_row"):
                                yield Static("Forks:", classes="execution_label")
                                yield Input(placeholder="5", id="forks", classes="execution_input")

                            with Horizontal(classes="execution_field_row"):
                                yield Static("Job Slicing:", classes="execution_label")
                                yield Input(placeholder="1", id="job_slicing", classes="execution_input")

                            with Horizontal(classes="execution_field_row"):
                                yield Static("Timeout (s):", classes="execution_label")
                                yield Input(placeholder="0", id="timeout", classes="execution_input")

                        # Right side: checkboxes
                        with Horizontal(classes="execution_checkboxes_column"):
                            yield Checkbox("Allow Concurrent Jobs", id="allow_simultaneous")
                            yield Checkbox("Enable Fact Storage", id="use_fact_cache")

                # Right half: Other Credentials (Ansible Vault)
                with Container(classes="execution_section_half"):
                    yield Static("Other Credentials (Ansible Vault)", classes="section_title")
                    yield SelectionList[int](id="vault_credentials_list")

            # Extra Vars Section
            with Container(classes="form_section", id="extra_vars_section"):
                yield Static("Extra Variables (JSON)", classes="section_title")
                yield TextArea(id="extra_vars_area", language="json", text="{\n  \n}")

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
        self.title = f"{app_name} - Create Job Template for {instance_name}"

        # Update top panel (single line, accent colored)
        top_panel = self.query_one("#top_panel", Static)
        top_panel.update(
            f"[bold]{app_name}[/bold] - [bold $accent]Create Job Template for {instance_name}[/bold $accent]"
        )

        # Fetch and populate dropdowns
        await self._populate_projects()
        await self._populate_inventories()
        await self._populate_execution_environments()
        await self._populate_credentials()
        await self._populate_vault_credentials()

        # Load saved state from app
        self._load_state()

        # Don't auto-focus input - conflicts with 1-4 navigation bindings

    async def _populate_projects(self) -> None:
        """Fetch projects from API and populate dropdown"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            project_select = self.query_one("#project", Select)
            current_value = project_select.value

            async with client:
                # Fetch projects
                response = await client.get("projects/")
                projects = response.get("results", [])

                # Build options: (display_name, project_id)
                options = [(project["name"], project["id"]) for project in projects]

                # Populate select
                project_select.set_options(options)

                # Restore previous selection if it still exists
                if current_value is not None:
                    option_ids = [opt[1] for opt in options]
                    if current_value in option_ids:
                        project_select.value = current_value

        except Exception as e:
            self.notify(f"Failed to load projects: {e}", severity="warning", timeout=3)

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

    async def _populate_execution_environments(self) -> None:
        """Fetch execution environments from API and populate dropdown"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            ee_select = self.query_one("#execution_environment", Select)
            current_value = ee_select.value

            async with client:
                # Fetch execution environments
                response = await client.get("execution_environments/")
                execution_environments = response.get("results", [])

                # Build options: (display_name, ee_id)
                # Include "None" option for optional selection
                options = [("None", None)]
                options.extend([(ee["name"], ee["id"]) for ee in execution_environments])

                # Populate select
                ee_select.set_options(options)

                # Restore previous selection if it still exists
                if current_value is not None:
                    option_ids = [opt[1] for opt in options]
                    if current_value in option_ids:
                        ee_select.value = current_value

        except Exception as e:
            self.notify(f"Failed to load execution environments: {e}", severity="warning", timeout=3)

    async def _populate_credentials(self) -> None:
        """Fetch credentials from API and populate dropdown"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            cred_select = self.query_one("#credential", Select)
            current_value = cred_select.value

            async with client:
                # Fetch machine credentials only (SSH credentials for job templates)
                # Job templates can only use one machine credential for SSH access
                response = await client.get("credentials/?credential_type__kind=ssh")
                credentials = response.get("results", [])

                # Build options: (display_name, credential_id)
                # Include "None" option for optional selection
                options = [("None", None)]
                options.extend([(cred["name"], cred["id"]) for cred in credentials])

                # Populate select
                cred_select.set_options(options)

                # Restore previous selection if it still exists
                if current_value is not None:
                    option_ids = [opt[1] for opt in options]
                    if current_value in option_ids:
                        cred_select.value = current_value

        except Exception as e:
            self.notify(f"Failed to load credentials: {e}", severity="warning", timeout=3)

    async def _populate_vault_credentials(self) -> None:
        """Fetch vault credentials from API and populate multi-select list"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            vault_list = self.query_one("#vault_credentials_list", SelectionList)

            async with client:
                # Fetch vault credentials only
                response = await client.get("credentials/?credential_type__kind=vault")
                vault_credentials = response.get("results", [])

                # Clear existing options
                vault_list.clear_options()

                # Build options - Selection takes (prompt, value, initial_state)
                for cred in vault_credentials:
                    cred_name = cred.get("name", "Unknown")
                    cred_id = cred.get("id")
                    vault_list.add_option(Selection(cred_name, cred_id, initial_state=False))

        except Exception as e:
            self.notify(f"Failed to load vault credentials: {e}", severity="warning", timeout=3)

    async def _load_playbooks_for_project(self, project_id: int) -> None:
        """Fetch playbooks for selected project"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            playbook_select = self.query_one("#playbook", Select)

            async with client:
                # Fetch playbooks from dedicated endpoint
                response = await client.get(f"projects/{project_id}/playbooks/")
                playbooks = response  # Response is a list of playbook names

                if playbooks and len(playbooks) > 0:
                    # Build options: (playbook_name, playbook_name)
                    options = [(pb, pb) for pb in playbooks]
                    playbook_select.set_options(options)

                    # Restore pending playbook value if set
                    if self._pending_playbook_restore and self._pending_playbook_restore in playbooks:
                        playbook_select.value = self._pending_playbook_restore
                        self._pending_playbook_restore = None
                else:
                    # No playbooks found
                    playbook_select.set_options([("No playbooks found", None)])
                    self.notify("No playbooks found in selected project", severity="warning", timeout=3)

        except Exception as e:
            self.notify(f"Failed to load playbooks: {e}", severity="warning", timeout=3)
            playbook_select = self.query_one("#playbook", Select)
            playbook_select.set_options([("Error loading playbooks", None)])

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes - load playbooks when project changes"""
        if event.select.id == "project":
            project_id = event.value
            if project_id is not None and project_id is not Select.BLANK:
                # Load playbooks for the selected project
                self.run_worker(self._load_playbooks_for_project(project_id))

    def _load_state(self) -> None:
        """Load form state from app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = self.app.create_mode_state.get(self.create_type, {})
        if not state:
            return

        # Restore text inputs
        for field_id in ["name", "description", "limit", "forks", "job_slicing", "timeout"]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Input)
                widget.value = state[field_id]

        # Store playbook value to restore after project loads playbooks
        # Must be set BEFORE restoring project (which triggers playbook loading)
        if "playbook" in state and "project" in state and state["project"] is not None:
            self._pending_playbook_restore = state["playbook"]

        # Restore select widgets
        # When project is set, it will trigger on_select_changed which loads playbooks
        # and then _load_playbooks_for_project will restore the pending playbook value
        for field_id in ["project", "verbosity", "execution_environment", "inventory", "credential"]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Select)
                widget.value = state[field_id]

        # Restore checkboxes
        for field_id in ["become_enabled", "allow_simultaneous", "use_fact_cache"]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Checkbox)
                widget.value = state[field_id]

        # Restore vault credentials selection
        if "vault_credentials" in state:
            vault_list = self.query_one("#vault_credentials_list", SelectionList)
            selected_ids = state["vault_credentials"]
            for vault_id in selected_ids:
                try:
                    vault_list.select(vault_id)
                except Exception:
                    pass  # Option may not exist anymore

        # Restore extra vars TextArea
        if "extra_vars" in state:
            widget = self.query_one("#extra_vars_area", TextArea)
            widget.text = state["extra_vars"]

    def _save_state(self) -> None:
        """Save current form state to app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = {}

        # Save text inputs
        for field_id in ["name", "description", "limit", "forks", "job_slicing", "timeout"]:
            widget = self.query_one(f"#{field_id}", Input)
            state[field_id] = widget.value

        # Save select widgets
        for field_id in ["project", "playbook", "verbosity", "execution_environment", "inventory", "credential"]:
            widget = self.query_one(f"#{field_id}", Select)
            state[field_id] = widget.value

        # Save checkboxes
        for field_id in ["become_enabled", "allow_simultaneous", "use_fact_cache"]:
            widget = self.query_one(f"#{field_id}", Checkbox)
            state[field_id] = widget.value

        # Save vault credentials selection
        vault_list = self.query_one("#vault_credentials_list", SelectionList)
        state["vault_credentials"] = list(vault_list.selected)

        # Save extra vars TextArea
        widget = self.query_one("#extra_vars_area", TextArea)
        state["extra_vars"] = widget.text

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
        if create_type == "job_template":
            # Already on job template screen, do nothing
            return
        elif create_type == "project":
            from awx_tui.screens.create_project import CreateProjectScreen

            self.app.pop_screen()
            self.app.push_screen(CreateProjectScreen())
        elif create_type == "credential":
            from awx_tui.screens.create_credential import CreateCredentialScreen

            self.app.pop_screen()
            self.app.push_screen(CreateCredentialScreen())
        elif create_type == "inventory":
            from awx_tui.screens.create_inventory import CreateInventoryScreen

            self.app.pop_screen()
            self.app.push_screen(CreateInventoryScreen())
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
        project_id = self.query_one("#project", Select).value
        if project_id is Select.BLANK:
            project_id = None

        playbook = self.query_one("#playbook", Select).value
        if playbook is Select.BLANK:
            playbook = None

        verbosity = self.query_one("#verbosity", Select).value
        if verbosity is Select.BLANK:
            verbosity = 0

        execution_environment_id = self.query_one("#execution_environment", Select).value
        if execution_environment_id is Select.BLANK:
            execution_environment_id = None

        inventory_id = self.query_one("#inventory", Select).value
        if inventory_id is Select.BLANK:
            inventory_id = None

        # Get credential from Select (single select)
        credential_id = self.query_one("#credential", Select).value
        if credential_id is Select.BLANK:
            credential_id = None

        limit = self.query_one("#limit", Input).value.strip()
        forks = self.query_one("#forks", Input).value.strip()
        job_slicing = self.query_one("#job_slicing", Input).value.strip()
        timeout = self.query_one("#timeout", Input).value.strip()

        become_enabled = self.query_one("#become_enabled", Checkbox).value
        allow_simultaneous = self.query_one("#allow_simultaneous", Checkbox).value
        use_fact_cache = self.query_one("#use_fact_cache", Checkbox).value

        # Get vault credentials selection
        vault_list = self.query_one("#vault_credentials_list", SelectionList)
        selected_vault_ids = list(vault_list.selected)

        extra_vars_text = self.query_one("#extra_vars_area", TextArea).text.strip()

        # Validate required fields
        if not name:
            self.notify("Job template name is required", severity="error", timeout=3)
            self.query_one("#name", Input).focus()
            return

        if not project_id:
            self.notify("Project is required", severity="error", timeout=3)
            return

        if not playbook:
            self.notify("Playbook is required", severity="error", timeout=3)
            return

        if not inventory_id:
            self.notify("Inventory is required", severity="error", timeout=3)
            return

        # Validate numeric fields (if provided)
        forks_value = None
        if forks:
            try:
                forks_value = int(forks)
                if forks_value < 0:
                    self.notify("Forks must be a positive number", severity="error", timeout=3)
                    self.query_one("#forks", Input).focus()
                    return
            except ValueError:
                self.notify("Forks must be a number", severity="error", timeout=3)
                self.query_one("#forks", Input).focus()
                return

        job_slicing_value = None
        if job_slicing:
            try:
                job_slicing_value = int(job_slicing)
                if job_slicing_value < 1:
                    self.notify("Job slicing must be at least 1", severity="error", timeout=3)
                    self.query_one("#job_slicing", Input).focus()
                    return
            except ValueError:
                self.notify("Job slicing must be a number", severity="error", timeout=3)
                self.query_one("#job_slicing", Input).focus()
                return

        timeout_value = 0
        if timeout:
            try:
                timeout_value = int(timeout)
                if timeout_value < 0:
                    self.notify("Timeout must be a positive number", severity="error", timeout=3)
                    self.query_one("#timeout", Input).focus()
                    return
            except ValueError:
                self.notify("Timeout must be a number", severity="error", timeout=3)
                self.query_one("#timeout", Input).focus()
                return

        # Validate and parse extra vars JSON (if provided)
        extra_vars_dict = None
        if extra_vars_text:
            try:
                extra_vars_dict = json.loads(extra_vars_text)
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON in extra vars: {e}", severity="error", timeout=5)
                self.query_one("#extra_vars_area", TextArea).focus()
                return

        # Build job template data
        job_template_data = {
            "name": name,
            "description": description,
            "job_type": "run",  # Hardcoded to "run" for MVP
            "project": project_id,
            "playbook": playbook,
            "inventory": inventory_id,
            "verbosity": verbosity,
            "become_enabled": become_enabled,
            "allow_simultaneous": allow_simultaneous,
            "use_fact_cache": use_fact_cache,
            "timeout": timeout_value,
        }

        # Add optional fields if provided (not None)
        if execution_environment_id:
            job_template_data["execution_environment"] = execution_environment_id

        if limit:
            job_template_data["limit"] = limit

        if forks_value is not None:
            job_template_data["forks"] = forks_value

        if job_slicing_value is not None:
            job_template_data["job_slice_count"] = job_slicing_value

        if extra_vars_dict:
            job_template_data["extra_vars"] = json.dumps(extra_vars_dict)

        # Create the job template via API (async) - credential and vault credentials associated separately
        self.run_worker(self._create_job_template_async(job_template_data, name, credential_id, selected_vault_ids))

    async def _create_job_template_async(
        self, job_template_data: dict, name: str, credential_id: Optional[int], vault_credential_ids: list
    ) -> None:
        """Async method to create job template via API"""
        try:
            self.notify(f"Creating job template '{name}'...", timeout=2)

            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            async with client:
                # POST to /api/v2/job_templates/
                response = await client.post("job_templates/", data=job_template_data)
                job_template_id = response.get("id")
                job_template_name = response.get("name")

                # If credential was selected, associate it
                if credential_id:
                    try:
                        await client.post(f"job_templates/{job_template_id}/credentials/", data={"id": credential_id})
                    except Exception as e:
                        self.app.log.warning(f"Failed to associate credential: {e}")
                        self.notify(
                            f"Job template created but credential association failed: {e}",
                            severity="warning",
                            timeout=5,
                        )

                # Associate vault credentials if any were selected
                if vault_credential_ids:
                    for vault_id in vault_credential_ids:
                        try:
                            await client.post(f"job_templates/{job_template_id}/credentials/", data={"id": vault_id})
                        except Exception as e:
                            self.app.log.warning(f"Failed to associate vault credential {vault_id}: {e}")
                            self.notify(
                                f"Job template created but vault credential {vault_id} association failed: {e}",
                                severity="warning",
                                timeout=5,
                            )

                # Clear state after successful creation
                self._clear_state()

                # Show success notification
                self.notify(
                    f"[green]✓[/green] Job Template '{job_template_name}' created (ID: {job_template_id})",
                    severity="information",
                    timeout=5,
                )

                # Close the screen
                self.app.pop_screen()

        except Exception as e:
            # Show error notification
            error_msg = str(e)
            self.notify(f"[red]✗[/red] Failed to create job template: {error_msg}", severity="error", timeout=10)

    def action_clear_form(self) -> None:
        """Clear all form fields"""
        # Clear text inputs
        for field_id in ["name", "description", "limit", "forks", "job_slicing", "timeout"]:
            widget = self.query_one(f"#{field_id}", Input)
            widget.value = ""

        # Reset select widgets
        verbosity_widget = self.query_one("#verbosity", Select)
        verbosity_widget.value = 0

        # Reset project and playbook
        project_widget = self.query_one("#project", Select)
        if project_widget._options:
            project_widget.value = project_widget._options[0][1]

        playbook_widget = self.query_one("#playbook", Select)
        playbook_widget.set_options([("Select project first...", None)])

        # Reset execution environment to "None"
        ee_widget = self.query_one("#execution_environment", Select)
        ee_widget.value = None

        # Reset inventory
        inventory_widget = self.query_one("#inventory", Select)
        if inventory_widget._options:
            inventory_widget.value = inventory_widget._options[0][1]

        # Reset credential to "None"
        cred_widget = self.query_one("#credential", Select)
        cred_widget.value = None

        # Clear vault credentials selection
        vault_list = self.query_one("#vault_credentials_list", SelectionList)
        vault_list.deselect_all()

        # Uncheck all checkboxes
        for field_id in ["become_enabled", "allow_simultaneous", "use_fact_cache"]:
            widget = self.query_one(f"#{field_id}", Checkbox)
            widget.value = False

        # Reset extra vars TextArea
        extra_vars_widget = self.query_one("#extra_vars_area", TextArea)
        extra_vars_widget.text = "{\n  \n}"

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
        await self._populate_projects()
        await self._populate_inventories()
        await self._populate_execution_environments()
        await self._populate_credentials()
        await self._populate_vault_credentials()
        self.notify("Dropdown data reloaded", timeout=2)

    def action_preview_json(self) -> None:
        """Preview the JSON payload that will be sent to the API"""
        from awx_tui.modals.json_preview import JsonPreviewModal

        # Build job template data from current form values (no validation)
        job_template_data, notes = self._build_job_template_data_for_preview()

        # Show the JSON preview modal
        self.app.push_screen(
            JsonPreviewModal(
                json_data=job_template_data,
                title="Job Template Creation - API Payload Preview",
                endpoint="/api/v2/job_templates/",
                method="POST",
                notes=notes,
            )
        )

    def action_export_task(self) -> None:
        """Export current form as Ansible awx.awx.job_template task"""
        from awx_tui.modals.task_export import TaskExportModal
        from awx_tui.utils.ansible_mapper import job_template_to_ansible_task

        # Build job template data with names resolved from dropdowns
        ansible_data = self._build_ansible_task_data()

        # Generate YAML task
        yaml_str, notes = job_template_to_ansible_task(ansible_data)

        # Show the export modal
        self.app.push_screen(
            TaskExportModal(
                task_yaml=yaml_str,
                title="Export AP Task - Job Template",
                module_name="job_template",
                notes=notes,
            )
        )

    def _build_job_template_data_for_preview(self) -> tuple:
        """Build job template data dict from current form values (for preview, no validation)

        Returns:
            tuple: (job_template_data dict, notes list)
        """
        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get Select values
        project_id = self.query_one("#project", Select).value
        if project_id is Select.BLANK:
            project_id = None

        playbook = self.query_one("#playbook", Select).value
        if playbook is Select.BLANK:
            playbook = None

        verbosity = self.query_one("#verbosity", Select).value
        if verbosity is Select.BLANK:
            verbosity = 0

        execution_environment_id = self.query_one("#execution_environment", Select).value
        if execution_environment_id is Select.BLANK:
            execution_environment_id = None

        inventory_id = self.query_one("#inventory", Select).value
        if inventory_id is Select.BLANK:
            inventory_id = None

        credential_id = self.query_one("#credential", Select).value
        if credential_id is Select.BLANK:
            credential_id = None

        limit = self.query_one("#limit", Input).value.strip()
        forks = self.query_one("#forks", Input).value.strip()
        job_slicing = self.query_one("#job_slicing", Input).value.strip()
        timeout = self.query_one("#timeout", Input).value.strip()

        become_enabled = self.query_one("#become_enabled", Checkbox).value
        allow_simultaneous = self.query_one("#allow_simultaneous", Checkbox).value
        use_fact_cache = self.query_one("#use_fact_cache", Checkbox).value

        extra_vars_text = self.query_one("#extra_vars_area", TextArea).text.strip()

        # Build job template data
        job_template_data = {
            "name": name or "REQUIRED",
            "description": description,
            "job_type": "run",
            "project": project_id or "REQUIRED",
            "playbook": playbook or "REQUIRED",
            "inventory": inventory_id or "REQUIRED",
            "verbosity": verbosity,
            "become_enabled": become_enabled,
            "allow_simultaneous": allow_simultaneous,
            "use_fact_cache": use_fact_cache,
            "timeout": int(timeout) if timeout else 0,
        }

        # Add optional fields
        if execution_environment_id:
            job_template_data["execution_environment"] = execution_environment_id

        if limit:
            job_template_data["limit"] = limit

        if forks:
            job_template_data["forks"] = int(forks) if forks.isdigit() else forks

        if job_slicing:
            job_template_data["job_slice_count"] = int(job_slicing) if job_slicing.isdigit() else job_slicing

        if extra_vars_text:
            try:
                extra_vars_dict = json.loads(extra_vars_text)
                job_template_data["extra_vars"] = json.dumps(extra_vars_dict)
            except json.JSONDecodeError:
                job_template_data["extra_vars"] = "INVALID_JSON"

        # Get vault credentials selection
        vault_list = self.query_one("#vault_credentials_list", SelectionList)
        selected_vault_ids = list(vault_list.selected)

        # Build notes for additional context
        notes = []
        if credential_id:
            notes.append(
                f"Credential ID {credential_id} will be associated via separate POST to /api/v2/job_templates/{{id}}/credentials/"
            )
        if selected_vault_ids:
            notes.append(
                f"Vault credentials {selected_vault_ids} will be associated via separate POST to /api/v2/job_templates/{{id}}/credentials/"
            )

        return job_template_data, notes

    def _build_ansible_task_data(self) -> dict:
        """Build job template data for Ansible export with names resolved from dropdowns

        Returns:
            dict: Data dictionary with names instead of IDs where possible
        """

        # Helper function to get name from Select widget
        def get_selected_name(widget_id: str) -> tuple:
            """Get (name, id) from Select widget, returns (None, None) if not selected"""
            select_widget = self.query_one(f"#{widget_id}", Select)
            selected_id = select_widget.value
            if selected_id is None or selected_id is Select.BLANK:
                return None, None

            # Find the name by looking through options
            for option_name, option_id in select_widget._options:
                if option_id == selected_id:
                    return option_name, option_id
            return None, selected_id

        # Get form values with names
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        project_name, project_id = get_selected_name("project")
        inventory_name, inventory_id = get_selected_name("inventory")
        ee_name, ee_id = get_selected_name("execution_environment")
        credential_name, credential_id = get_selected_name("credential")

        playbook = self.query_one("#playbook", Select).value
        if playbook is Select.BLANK:
            playbook = None

        verbosity = self.query_one("#verbosity", Select).value
        if verbosity is Select.BLANK:
            verbosity = 0

        limit = self.query_one("#limit", Input).value.strip()
        forks = self.query_one("#forks", Input).value.strip()
        job_slicing = self.query_one("#job_slicing", Input).value.strip()
        timeout = self.query_one("#timeout", Input).value.strip()

        become_enabled = self.query_one("#become_enabled", Checkbox).value
        allow_simultaneous = self.query_one("#allow_simultaneous", Checkbox).value
        use_fact_cache = self.query_one("#use_fact_cache", Checkbox).value

        extra_vars_text = self.query_one("#extra_vars_area", TextArea).text.strip()

        # Build data dict with names
        ansible_data = {
            "name": name,
            "description": description,
            "job_type": "run",
            "playbook": playbook,
            "verbosity": verbosity,
            "become_enabled": become_enabled,
            "allow_simultaneous": allow_simultaneous,
            "use_fact_cache": use_fact_cache,
        }

        # Add IDs and names where available
        if project_name:
            ansible_data["project_name"] = project_name
        if project_id:
            ansible_data["project"] = project_id

        if inventory_name:
            ansible_data["inventory_name"] = inventory_name
        if inventory_id:
            ansible_data["inventory"] = inventory_id

        if ee_name:
            ansible_data["execution_environment_name"] = ee_name
        if ee_id:
            ansible_data["execution_environment"] = ee_id

        if credential_name:
            ansible_data["credential_names"] = [credential_name]
        if credential_id:
            ansible_data["credentials"] = [credential_id]

        # Optional fields
        if limit:
            ansible_data["limit"] = limit
        if forks:
            ansible_data["forks"] = forks
        if job_slicing:
            ansible_data["job_slice_count"] = job_slicing
        if timeout:
            ansible_data["timeout"] = timeout

        # Extra vars
        if extra_vars_text:
            try:
                extra_vars_dict = json.loads(extra_vars_text)
                ansible_data["extra_vars"] = extra_vars_dict
            except json.JSONDecodeError:
                ansible_data["extra_vars"] = extra_vars_text

        # Get vault credentials
        vault_list = self.query_one("#vault_credentials_list", SelectionList)
        selected_vault_ids = list(vault_list.selected)
        if selected_vault_ids:
            # Try to get names from the SelectionList options
            vault_names = []
            for option in vault_list._options:
                if option.id in selected_vault_ids:
                    vault_names.append(str(option.prompt))

            if vault_names and credential_name:
                ansible_data["credential_names"].extend(vault_names)
            elif vault_names:
                ansible_data["credential_names"] = vault_names

        return ansible_data

    def action_close(self) -> None:
        """Close create job template screen and save state"""
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
