"""
AWX TUI - Update Project Screen

Full-screen form for updating existing AWX projects.
Accessed by selecting a project from the Projects screen.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Input, Select, Static


class UpdateProjectScreen(Screen):
    """
    Update Project - Form for updating existing AWX project

    Features:
    - Pre-populated form with project data
    - Save Changes button (enabled only when changes made)
    - Tracks dirty state (any field modified)
    - Escape key to return to Projects screen
    """

    CSS = """
    UpdateProjectScreen {
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
        Binding("i", "show_info", "Info", show=True),
        Binding("ctrl+r", "reload_dropdowns", "Reload", show=True),
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

    def __init__(self, project_id: int, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id
        self.is_dirty = False  # Track if any field has been modified
        self.original_data = {}  # Store original project data for comparison

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
            yield Button("Save Changes", variant="primary", id="save_button", disabled=True)
            yield Button("Cancel", variant="default", id="cancel_button")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize screen and load project data"""
        # Update title with app name and instance info
        app_name = self.app.current_app_name if hasattr(self.app, "current_app_name") else "AWX TUI"
        instance_manager = self.app.instance_manager
        instance_name = instance_manager.current_instance if instance_manager else "No Instance"
        self.title = f"{app_name} - Update Project for {instance_name}"

        # Update top panel (single line, accent colored)
        top_panel = self.query_one("#top_panel", Static)
        top_panel.update(
            f"[bold]{app_name}[/bold] - [bold $accent]Update Project #{self.project_id} for {instance_name}[/bold $accent]"
        )

        # Fetch and populate organizations, credentials, and execution environments
        await self._populate_organizations()
        await self._populate_credentials()
        await self._populate_execution_environments()

        # Fetch and pre-populate project data
        await self._load_project_data()

        # Change tracking handled by event handlers (on_input_changed, on_select_changed, on_checkbox_changed)

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

    async def _load_project_data(self) -> None:
        """Fetch project data from API and pre-populate form"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            async with client:
                # Fetch project data
                project = await client.get(f"projects/{self.project_id}/")
                self.original_data = project.copy()

                # Populate text inputs
                self.query_one("#name", Input).value = project.get("name", "")
                self.query_one("#description", Input).value = project.get("description", "")
                self.query_one("#scm_url", Input).value = project.get("scm_url", "")
                self.query_one("#scm_branch", Input).value = project.get("scm_branch", "")
                self.query_one("#scm_refspec", Input).value = project.get("scm_refspec", "")
                self.query_one("#scm_update_cache_timeout", Input).value = str(
                    project.get("scm_update_cache_timeout", "")
                )

                # Populate select widgets
                self.query_one("#scm_type", Select).value = project.get("scm_type", "git")
                self.query_one("#organization", Select).value = project.get("organization")

                # Only set default environment if it has a value (otherwise defaults to first option "None")
                default_env_id = project.get("default_environment")
                if default_env_id:
                    self.query_one("#default_environment", Select).value = default_env_id

                # Only set credential if it has a value (otherwise defaults to first option "None")
                credential_id = project.get("credential")
                if credential_id:
                    self.query_one("#scm_credential", Select).value = credential_id

                # Populate checkboxes
                self.query_one("#scm_clean", Checkbox).value = project.get("scm_clean", False)
                self.query_one("#scm_delete_on_update", Checkbox).value = project.get("scm_delete_on_update", False)
                self.query_one("#scm_track_submodules", Checkbox).value = project.get("scm_track_submodules", False)
                self.query_one("#scm_update_on_launch", Checkbox).value = project.get("scm_update_on_launch", False)
                self.query_one("#allow_override", Checkbox).value = project.get("allow_override", False)

        except Exception as e:
            self.notify(f"Failed to load project data: {e}", severity="error", timeout=5)
            self.app.pop_screen()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes"""
        # Only mark dirty after initial load (skip if we're still loading)
        if hasattr(self, "original_data") and self.original_data:
            self.is_dirty = True
            self._update_button_states()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes"""
        # Only mark dirty after initial load
        if hasattr(self, "original_data") and self.original_data:
            self.is_dirty = True
            self._update_button_states()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes"""
        # Only mark dirty after initial load
        if hasattr(self, "original_data") and self.original_data:
            self.is_dirty = True
            self._update_button_states()

    def _update_button_states(self) -> None:
        """Update Save Changes button enabled state based on dirty flag"""
        save_button = self.query_one("#save_button", Button)
        save_button.disabled = not self.is_dirty

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "save_button":
            self.action_save_changes()
        elif event.button.id == "cancel_button":
            self.action_close()

    def action_save_changes(self) -> None:
        """Validate and save changes to project"""
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
            "organization": organization_id,
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

        # Update the project via API (async)
        self.run_worker(self._update_project_async(project_data, name))

    async def _update_project_async(self, project_data: dict, name: str) -> None:
        """Async method to update project via API"""
        try:
            self.notify(f"Updating project '{name}'...", timeout=2)

            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            async with client:
                # PATCH to /api/v2/projects/{id}/
                response = await client.patch(f"projects/{self.project_id}/", data=project_data)
                project_name = response.get("name")

                # Reset dirty flag and update button states
                self.is_dirty = False
                self._update_button_states()

                # Show success notification
                self.notify(f"[green]✓[/green] Project '{project_name}' updated", severity="information", timeout=5)

                # Close the screen
                self.app.pop_screen()

        except Exception as e:
            # Show error notification
            error_msg = str(e)
            self.notify(f"[red]✗[/red] Failed to update project: {error_msg}", severity="error", timeout=10)

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
                title="Project Update - API Payload Preview",
                endpoint=f"/api/v2/projects/{self.project_id}/",
                method="PATCH",
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
        """Close update project screen"""
        self.app.pop_screen()

    def action_show_info(self) -> None:
        """Show info/about modal"""
        from awx_tui.modals.info import InfoModal

        app_name = self.app.current_app_name if hasattr(self.app, "current_app_name") else "AWX TUI"
        self.app.push_screen(InfoModal(app_name))

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()
