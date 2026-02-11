"""
AWX TUI - Create Project Screen

Full-screen form for creating new AWX projects.
Part of Create Mode - access via 'C' key -> '1' or select Project from menu.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Input, Select, Static


class CreateProjectScreen(Screen):
    """
    Create Project - Form for creating new AWX project

    Features:
    - Full form with all project fields
    - SCM type selection (Manual, Git, SVN, etc.)
    - Form validation before submit
    - State persistence (survives navigation to other create screens)
    - Clear Form button to reset
    - Number keys (1-4) to navigate to other create screens
    """

    CSS = """
    CreateProjectScreen {
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

    #options_section {
        height: auto;
        max-height: 12;
    }

    #options_section .section_title {
        margin-bottom: 0;
    }

    .options_row {
        height: auto;
        padding-left: 1;
        margin: 0;
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

    # SCM type options
    # NOTE: Only Git is supported in TUI. AWX UI dynamically changes form fields
    # based on SCM type, but we're keeping it simple with Git-only support.
    SCM_TYPES = [
        ("Git", "git"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_type = "project"

    def compose(self) -> ComposeResult:
        """Create the form layout"""
        # Top panel with app and instance info
        yield Static("", id="top_panel")

        with ScrollableContainer(id="form_container"):
            # Top row: Basic Info and SCM sections side-by-side (50/50 split)
            with Horizontal(id="top_sections"):
                # Basic Info Section (left half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Basic Information", classes="section_title")

                    with Horizontal():
                        yield Static("Name *:", classes="field_label")
                        yield Input(placeholder="Project name (required)", id="name", classes="field_input")

                    with Horizontal():
                        yield Static("Description:", classes="field_label")
                        yield Input(placeholder="Optional description", id="description", classes="field_input")

                    with Horizontal():
                        yield Static("Organization *:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="organization", classes="field_input", allow_blank=True
                        )

                    with Horizontal():
                        yield Static("Execution Environment:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)],
                            id="default_environment",
                            classes="field_input",
                            allow_blank=True,
                        )

                # SCM Section (right half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Source Control", classes="section_title")

                    with Horizontal():
                        yield Static("SCM Type:", classes="field_label")
                        yield Select(
                            options=[(label, value) for label, value in self.SCM_TYPES],
                            value="git",
                            id="scm_type",
                            classes="field_input",
                        )

                    with Horizontal():
                        yield Static("SCM URL *:", classes="field_label")
                        yield Input(placeholder="https://github.com/user/repo.git", id="scm_url", classes="field_input")

                    with Horizontal():
                        yield Static("Branch/Tag/Commit:", classes="field_label")
                        yield Input(
                            placeholder="main (default branch if empty)", id="scm_branch", classes="field_input"
                        )

                    with Horizontal():
                        yield Static("SCM Refspec:", classes="field_label")
                        yield Input(
                            placeholder="Optional refspec (e.g., refs/pull/*/head:refs/remotes/origin/pr/*)",
                            id="scm_refspec",
                            classes="field_input",
                        )

                    with Horizontal():
                        yield Static("SCM Credential:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="scm_credential", classes="field_input", allow_blank=True
                        )

            # Options Section (full width below)
            with Container(classes="form_section", id="options_section"):
                yield Static("Update Options", classes="section_title")

                with Horizontal(classes="options_row"):
                    yield Checkbox("Clean", id="scm_clean")
                    yield Checkbox("Delete", id="scm_delete_on_update")
                    yield Checkbox("Track Submodules", id="scm_track_submodules")
                    yield Checkbox("Allow Branch Override", id="allow_override")

                with Horizontal(classes="options_row"):
                    yield Checkbox("Update Revision on Launch", id="scm_update_on_launch")
                    yield Static("Cache Timeout (sec):", classes="inline_label")
                    yield Input(placeholder="0", id="scm_update_cache_timeout", classes="inline_input")

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
        self.title = f"{app_name} - Create Project for {instance_name}"

        # Update top panel (single line, accent colored)
        top_panel = self.query_one("#top_panel", Static)
        top_panel.update(f"[bold]{app_name}[/bold] - [bold $accent]Create Project for {instance_name}[/bold $accent]")

        # Fetch and populate organizations, credentials, and execution environments
        await self._populate_organizations()
        await self._populate_credentials()
        await self._populate_execution_environments()

        # Load saved state from app
        self._load_state()

        # Don't auto-focus input - conflicts with 1-4 navigation bindings

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

    async def _populate_credentials(self) -> None:
        """Fetch SCM credentials from API and populate dropdown"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            cred_select = self.query_one("#scm_credential", Select)
            current_value = cred_select.value

            async with client:
                # Fetch SCM credentials (Source Control)
                scm_response = await client.get("credentials/?credential_type__kind=scm")
                scm_credentials = scm_response.get("results", [])

                # Fetch token credentials (all token types)
                # Limitation: Shows all token credentials, not just GitHub/GitLab PATs
                token_response = await client.get("credentials/?credential_type__kind=token")
                token_credentials = token_response.get("results", [])

                # Combine both lists
                all_credentials = scm_credentials + token_credentials

                # Build options: (display_name, credential_id)
                # Include "None" option for optional selection
                options = [("None", None)]
                options.extend([(cred["name"], cred["id"]) for cred in all_credentials])

                # Populate select
                cred_select.set_options(options)

                # Restore previous selection if it still exists
                if current_value is not None:
                    option_ids = [opt[1] for opt in options]
                    if current_value in option_ids:
                        cred_select.value = current_value

        except Exception as e:
            self.notify(f"Failed to load credentials: {e}", severity="warning", timeout=3)

    async def _populate_execution_environments(self) -> None:
        """Fetch execution environments from API and populate dropdown"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            ee_select = self.query_one("#default_environment", Select)
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

    def _load_state(self) -> None:
        """Load form state from app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = self.app.create_mode_state.get(self.create_type, {})
        if not state:
            return

        # Restore text inputs
        for field_id in ["name", "description", "scm_url", "scm_branch", "scm_refspec", "scm_update_cache_timeout"]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Input)
                widget.value = state[field_id]

        # Restore select widgets
        for field_id in ["scm_type", "organization", "default_environment", "scm_credential"]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Select)
                widget.value = state[field_id]

        # Restore checkboxes
        for field_id in [
            "scm_clean",
            "scm_delete_on_update",
            "scm_track_submodules",
            "scm_update_on_launch",
            "allow_override",
        ]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Checkbox)
                widget.value = state[field_id]

    def _save_state(self) -> None:
        """Save current form state to app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = {}

        # Save text inputs
        for field_id in ["name", "description", "scm_url", "scm_branch", "scm_refspec", "scm_update_cache_timeout"]:
            widget = self.query_one(f"#{field_id}", Input)
            state[field_id] = widget.value

        # Save select widgets
        for field_id in ["scm_type", "organization", "default_environment", "scm_credential"]:
            widget = self.query_one(f"#{field_id}", Select)
            state[field_id] = widget.value

        # Save checkboxes
        for field_id in [
            "scm_clean",
            "scm_delete_on_update",
            "scm_track_submodules",
            "scm_update_on_launch",
            "allow_override",
        ]:
            widget = self.query_one(f"#{field_id}", Checkbox)
            state[field_id] = widget.value

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
        if create_type == "project":
            # Already on project screen, do nothing
            return
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

        default_environment_id = self.query_one("#default_environment", Select).value
        if default_environment_id is Select.BLANK:
            default_environment_id = None

        scm_type = self.query_one("#scm_type", Select).value
        if scm_type is Select.BLANK:
            scm_type = None

        scm_credential_id = self.query_one("#scm_credential", Select).value
        if scm_credential_id is Select.BLANK:
            scm_credential_id = None

        scm_url = self.query_one("#scm_url", Input).value.strip()
        scm_branch = self.query_one("#scm_branch", Input).value.strip()
        scm_refspec = self.query_one("#scm_refspec", Input).value.strip()
        scm_clean = self.query_one("#scm_clean", Checkbox).value
        scm_delete_on_update = self.query_one("#scm_delete_on_update", Checkbox).value
        scm_track_submodules = self.query_one("#scm_track_submodules", Checkbox).value
        scm_update_on_launch = self.query_one("#scm_update_on_launch", Checkbox).value
        allow_override = self.query_one("#allow_override", Checkbox).value
        scm_update_cache_timeout = self.query_one("#scm_update_cache_timeout", Input).value.strip()

        # Validate required fields
        if not name:
            self.notify("Project name is required", severity="error", timeout=3)
            self.query_one("#name", Input).focus()
            return

        if not organization_id:
            self.notify("Organization is required", severity="error", timeout=3)
            return

        # Validate SCM URL for non-manual types
        if scm_type and scm_type != "" and not scm_url:
            self.notify(f"SCM URL is required for {scm_type} projects", severity="error", timeout=3)
            self.query_one("#scm_url", Input).focus()
            return

        # Validate cache timeout is numeric (if provided)
        cache_timeout_value = 0
        if scm_update_cache_timeout:
            try:
                cache_timeout_value = int(scm_update_cache_timeout)
                if cache_timeout_value < 0:
                    self.notify("Cache timeout must be a positive number", severity="error", timeout=3)
                    self.query_one("#scm_update_cache_timeout", Input).focus()
                    return
            except ValueError:
                self.notify("Cache timeout must be a number", severity="error", timeout=3)
                self.query_one("#scm_update_cache_timeout", Input).focus()
                return

        # Build project data
        project_data = {
            "name": name,
            "description": description,
            "organization": organization_id,  # Organization ID (required)
            "scm_type": scm_type or "",
            "scm_url": scm_url,
            "scm_branch": scm_branch or "",
            "scm_refspec": scm_refspec or "",
            "scm_clean": scm_clean,
            "scm_delete_on_update": scm_delete_on_update,
            "scm_track_submodules": scm_track_submodules,
            "scm_update_on_launch": scm_update_on_launch,
            "scm_update_cache_timeout": cache_timeout_value,
            "allow_override": allow_override,
        }

        # Add optional fields if provided (not None)
        if default_environment_id:
            project_data["default_environment"] = default_environment_id

        if scm_credential_id:
            project_data["credential"] = scm_credential_id

        # Create the project via API (async)
        self.run_worker(self._create_project_async(project_data, name))

    async def _create_project_async(self, project_data: dict, name: str) -> None:
        """Async method to create project via API"""
        try:
            self.notify(f"Creating project '{name}'...", timeout=2)

            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            async with client:
                # POST to /api/v2/projects/
                response = await client.post("projects/", data=project_data)
                project_id = response.get("id")
                project_name = response.get("name")

                # Clear state after successful creation
                self._clear_state()

                # Show success notification
                self.notify(
                    f"[green]✓[/green] Project '{project_name}' created (ID: {project_id})",
                    severity="information",
                    timeout=5,
                )

                # Close the screen
                self.app.pop_screen()

        except Exception as e:
            # Show error notification
            error_msg = str(e)
            self.notify(f"[red]✗[/red] Failed to create project: {error_msg}", severity="error", timeout=10)

    def action_clear_form(self) -> None:
        """Clear all form fields"""
        # Clear text inputs
        for field_id in ["name", "description", "scm_url", "scm_branch", "scm_refspec", "scm_update_cache_timeout"]:
            widget = self.query_one(f"#{field_id}", Input)
            widget.value = ""

        # Reset select widgets to first option
        scm_type_widget = self.query_one("#scm_type", Select)
        scm_type_widget.value = "git"

        org_widget = self.query_one("#organization", Select)
        if org_widget._options:  # If we have options, select first one
            org_widget.value = org_widget._options[0][1]

        # Reset execution environment to "None"
        ee_widget = self.query_one("#default_environment", Select)
        ee_widget.value = None  # Select "None" option

        # Reset credential to "None"
        cred_widget = self.query_one("#scm_credential", Select)
        cred_widget.value = None  # Select "None" option

        # Uncheck all checkboxes
        for field_id in [
            "scm_clean",
            "scm_delete_on_update",
            "scm_track_submodules",
            "scm_update_on_launch",
            "allow_override",
        ]:
            widget = self.query_one(f"#{field_id}", Checkbox)
            widget.value = False

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
        await self._populate_credentials()
        await self._populate_execution_environments()
        self.notify("Dropdown data reloaded", timeout=2)

    def action_preview_json(self) -> None:
        """Preview the JSON payload that will be sent to the API"""
        from awx_tui.modals.json_preview import JsonPreviewModal

        # Build project data from current form values (no validation)
        project_data, notes = self._build_project_data_for_preview()

        # Show the JSON preview modal
        self.app.push_screen(
            JsonPreviewModal(
                json_data=project_data,
                title="Project Creation - API Payload Preview",
                endpoint="/api/v2/projects/",
                method="POST",
                notes=notes,
            )
        )

    def action_export_task(self) -> None:
        """Export current form as Ansible awx.awx.project task"""
        from awx_tui.modals.task_export import TaskExportModal
        from awx_tui.utils.ansible_mapper import project_to_ansible_task

        # Build project data with names resolved from dropdowns
        ansible_data = self._build_ansible_task_data()

        # Generate YAML task
        yaml_str, notes = project_to_ansible_task(ansible_data)

        # Show the export modal
        self.app.push_screen(
            TaskExportModal(
                task_yaml=yaml_str,
                title="Export AP Task - Project",
                module_name="project",
                notes=notes,
            )
        )

    def _build_project_data_for_preview(self) -> tuple:
        """Build project data dict from current form values (for preview, no validation)

        Returns:
            tuple: (project_data dict, notes list)
        """
        # Get form values
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get Select values
        organization_id = self.query_one("#organization", Select).value
        if organization_id is Select.BLANK:
            organization_id = None

        default_environment_id = self.query_one("#default_environment", Select).value
        if default_environment_id is Select.BLANK:
            default_environment_id = None

        scm_type = self.query_one("#scm_type", Select).value
        if scm_type is Select.BLANK:
            scm_type = None

        scm_credential_id = self.query_one("#scm_credential", Select).value
        if scm_credential_id is Select.BLANK:
            scm_credential_id = None

        scm_url = self.query_one("#scm_url", Input).value.strip()
        scm_branch = self.query_one("#scm_branch", Input).value.strip()
        scm_refspec = self.query_one("#scm_refspec", Input).value.strip()
        scm_clean = self.query_one("#scm_clean", Checkbox).value
        scm_delete_on_update = self.query_one("#scm_delete_on_update", Checkbox).value
        scm_track_submodules = self.query_one("#scm_track_submodules", Checkbox).value
        scm_update_on_launch = self.query_one("#scm_update_on_launch", Checkbox).value
        allow_override = self.query_one("#allow_override", Checkbox).value
        scm_update_cache_timeout = self.query_one("#scm_update_cache_timeout", Input).value.strip()

        # Build project data
        project_data = {
            "name": name or "REQUIRED",
            "description": description,
            "organization": organization_id or "REQUIRED",
            "scm_type": scm_type or "",
            "scm_url": scm_url,
            "scm_branch": scm_branch or "",
            "scm_refspec": scm_refspec or "",
            "scm_clean": scm_clean,
            "scm_delete_on_update": scm_delete_on_update,
            "scm_track_submodules": scm_track_submodules,
            "scm_update_on_launch": scm_update_on_launch,
            "scm_update_cache_timeout": int(scm_update_cache_timeout) if scm_update_cache_timeout else 0,
            "allow_override": allow_override,
        }

        # Add optional fields
        if default_environment_id:
            project_data["default_environment"] = default_environment_id

        if scm_credential_id:
            project_data["credential"] = scm_credential_id

        # No additional notes for projects
        notes = []

        return project_data, notes

    def _build_ansible_task_data(self) -> dict:
        """Build project data for Ansible export with names resolved from dropdowns

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

        organization_name, organization_id = get_selected_name("organization")
        default_environment_name, default_environment_id = get_selected_name("default_environment")
        scm_credential_name, scm_credential_id = get_selected_name("scm_credential")

        scm_type = self.query_one("#scm_type", Select).value
        if scm_type is Select.BLANK:
            scm_type = None

        scm_url = self.query_one("#scm_url", Input).value.strip()
        scm_branch = self.query_one("#scm_branch", Input).value.strip()
        scm_clean = self.query_one("#scm_clean", Checkbox).value
        scm_delete_on_update = self.query_one("#scm_delete_on_update", Checkbox).value
        scm_update_on_launch = self.query_one("#scm_update_on_launch", Checkbox).value

        # Build data dict with names
        ansible_data = {
            "name": name,
            "description": description,
            "scm_type": scm_type,
            "scm_url": scm_url,
            "scm_branch": scm_branch,
            "scm_clean": scm_clean,
            "scm_delete_on_update": scm_delete_on_update,
            "scm_update_on_launch": scm_update_on_launch,
        }

        # Add IDs and names where available
        if organization_name:
            ansible_data["organization_name"] = organization_name
        if organization_id:
            ansible_data["organization"] = organization_id

        if default_environment_name:
            ansible_data["default_environment_name"] = default_environment_name
        if default_environment_id:
            ansible_data["default_environment"] = default_environment_id

        if scm_credential_name:
            ansible_data["credential_name"] = scm_credential_name
        if scm_credential_id:
            ansible_data["credential"] = scm_credential_id

        return ansible_data

    def action_close(self) -> None:
        """Close create project screen and save state"""
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
