"""
AWX TUI - Create Credential Screen

Full-screen form for creating new AWX credentials.
Part of Create Mode - access via 'C' key -> '4' or select Credential from menu.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Input, Select, Static, TextArea


class CreateCredentialScreen(Screen):
    """
    Create Credential - Form for creating new AWX credential

    Features:
    - 6 credential types: Machine, Source Control, GitHub PAT, GitLab PAT, Vault, Kubernetes
    - Dynamic form based on selected credential type
    - Password masking for sensitive fields
    - SSH key support for Machine/Source Control types
    - Bearer token support for Kubernetes/PAT types
    - State persistence (survives navigation to other create screens)
    - Number keys (1-4) to navigate to other create screens
    """

    CSS = """
    CreateCredentialScreen {
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
        height: 17;
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

    .subsection_title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 0;
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

    #ssh_key_section {
        height: auto;
        margin-bottom: 1;
    }

    #ssh_key_section .section_title {
        margin-bottom: 0;
    }

    #ssh_key_area {
        height: 6;
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

    /* Visibility control for dynamic sections */
    .hidden {
        display: none;
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

    # Map credential type names to their kind identifiers
    # We'll fetch actual credential_type IDs from API
    CREDENTIAL_TYPE_KINDS = {
        "Machine": "ssh",
        "Source Control": "scm",
        "GitHub Personal Access Token": "github_token",
        "GitLab Personal Access Token": "gitlab_token",
        "Vault": "vault",
        "OpenShift or Kubernetes API Bearer Token": "kubernetes",
    }

    # Privilege escalation methods for Machine credentials
    PRIV_ESC_METHODS = [
        ("sudo", "sudo"),
        ("su", "su"),
        ("pbrun", "pbrun"),
        ("pfexec", "pfexec"),
        ("doas", "doas"),
        ("dzdo", "dzdo"),
        ("ksu", "ksu"),
        ("runas", "runas"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_type = "credential"
        self.credential_type_map = {}  # Maps kind to credential_type ID

    def compose(self) -> ComposeResult:
        """Create the form layout"""
        # Top panel with app and instance info
        yield Static("", id="top_panel")

        with ScrollableContainer(id="form_container"):
            # Top row: Basic Information and User Authentication sections side-by-side (50/50 split)
            with Horizontal(id="top_sections"):
                # Basic Information Section (left half)
                with Container(classes="form_section form_section_half"):
                    yield Static("Basic Information", classes="section_title")

                    with Horizontal():
                        yield Static("Name *:", classes="field_label")
                        yield Input(placeholder="Credential name (required)", id="name", classes="field_input")

                    with Horizontal():
                        yield Static("Description:", classes="field_label")
                        yield Input(placeholder="Optional description", id="description", classes="field_input")

                    with Horizontal():
                        yield Static("Organization *:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)], id="organization", classes="field_input", allow_blank=True
                        )

                    with Horizontal():
                        yield Static("Credential Type *:", classes="field_label")
                        yield Select(
                            options=[("Loading...", None)],
                            id="credential_type",
                            classes="field_input",
                            allow_blank=True,
                        )

                # User Authentication Section (right half) - dynamic based on type
                with Container(classes="form_section form_section_half", id="auth_section"):
                    yield Static("User Authentication", classes="section_title")

                    # Common fields (Machine, Source Control)
                    with Vertical(id="username_password_fields"):
                        with Horizontal():
                            yield Static("Username:", classes="field_label")
                            yield Input(placeholder="Username", id="username", classes="field_input")

                        with Horizontal():
                            yield Static("Password:", classes="field_label")
                            yield Input(
                                placeholder="Password or token", password=True, id="password", classes="field_input"
                            )

                    # Token field (GitHub PAT, GitLab PAT)
                    with Vertical(id="token_field", classes="hidden"):
                        with Horizontal():
                            yield Static("Token *:", classes="field_label")
                            yield Input(
                                placeholder="Personal access token", password=True, id="token", classes="field_input"
                            )

                    # Vault fields
                    with Vertical(id="vault_fields", classes="hidden"):
                        with Horizontal():
                            yield Static("Vault Password *:", classes="field_label")
                            yield Input(
                                placeholder="Ansible Vault password",
                                password=True,
                                id="vault_password",
                                classes="field_input",
                            )

                        with Horizontal():
                            yield Static("Vault ID:", classes="field_label")
                            yield Input(placeholder="Optional vault identifier", id="vault_id", classes="field_input")

                    # Kubernetes fields
                    with Vertical(id="kubernetes_fields", classes="hidden"):
                        with Horizontal():
                            yield Static("API Endpoint:", classes="field_label")
                            yield Input(
                                placeholder="https://kubernetes.example.com:6443", id="k8s_host", classes="field_input"
                            )

                        with Horizontal():
                            yield Static("Bearer Token *:", classes="field_label")
                            yield Input(
                                placeholder="Kubernetes API bearer token",
                                password=True,
                                id="k8s_bearer_token",
                                classes="field_input",
                            )

                        with Horizontal():
                            yield Static("CA Certificate:", classes="field_label")
                            yield Input(
                                placeholder="Certificate Authority data (PEM format)",
                                id="k8s_ca_cert",
                                classes="field_input",
                            )

                        with Horizontal():
                            yield Static("Verify SSL:", classes="field_label")
                            yield Checkbox("Verify SSL certificate", id="k8s_verify_ssl", value=True)

                    # Privilege Escalation (Machine only)
                    with Vertical(id="priv_esc_fields", classes="hidden"):
                        yield Static("Privilege Escalation", classes="subsection_title")

                        with Horizontal():
                            yield Static("Method:", classes="field_label")
                            yield Select(
                                options=[(label, value) for label, value in self.PRIV_ESC_METHODS],
                                value="sudo",
                                id="priv_method",
                                classes="field_input",
                            )

                        with Horizontal():
                            yield Static("Username:", classes="field_label")
                            yield Input(
                                placeholder="Privilege escalation username", id="priv_username", classes="field_input"
                            )

                        with Horizontal():
                            yield Static("Password:", classes="field_label")
                            yield Input(
                                placeholder="Privilege escalation password",
                                password=True,
                                id="priv_password",
                                classes="field_input",
                            )

            # SSH Key Section (full width, Machine/Source Control only)
            with Container(classes="form_section", id="ssh_key_section"):
                yield Static("SSH Private Key (Optional)", classes="section_title")

                yield TextArea(id="ssh_key_area", language="", text="")

                with Horizontal():
                    yield Static("Passphrase:", classes="field_label")
                    yield Input(
                        placeholder="SSH key passphrase (if encrypted)",
                        password=True,
                        id="ssh_passphrase",
                        classes="field_input",
                    )

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
        self.title = f"{app_name} - Create Credential for {instance_name}"

        # Update top panel (single line, accent colored)
        top_panel = self.query_one("#top_panel", Static)
        top_panel.update(
            f"[bold]{app_name}[/bold] - [bold $accent]Create Credential for {instance_name}[/bold $accent]"
        )

        # Fetch and populate dropdowns
        await self._populate_organizations()
        await self._populate_credential_types()

        # Load saved state from app
        self._load_state()

        # Update authentication panel based on current credential type
        self._update_authentication_panel()

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

    async def _populate_credential_types(self) -> None:
        """Fetch credential types from API and populate dropdown with supported types"""
        try:
            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            # Save current selection before reloading
            type_select = self.query_one("#credential_type", Select)
            current_value = type_select.value

            async with client:
                # Fetch all credential types (page_size 100 to get all in one request)
                response = await client.get("credential_types/", params={"page_size": 100})
                all_types = response.get("results", [])

                # Filter to only our supported types
                options = []
                self.credential_type_map = {}

                # Supported credential type names
                supported_names = {
                    "Machine",
                    "Source Control",
                    "GitHub Personal Access Token",
                    "GitLab Personal Access Token",
                    "Vault",
                    "OpenShift or Kubernetes API Bearer Token",
                }

                for cred_type in all_types:
                    name = cred_type.get("name", "")
                    cred_type_id = cred_type.get("id")
                    kind = cred_type.get("kind", "")

                    # Only add if name matches one we support
                    if name in supported_names:
                        options.append((name, cred_type_id))
                        self.credential_type_map[cred_type_id] = kind

                # Sort by name
                options.sort(key=lambda x: x[0])

                # Populate select
                type_select.set_options(options)

                # Restore previous selection if it still exists
                if current_value is not None:
                    option_ids = [opt[1] for opt in options]
                    if current_value in option_ids:
                        type_select.value = current_value

        except Exception as e:
            self.notify(f"Failed to load credential types: {e}", severity="warning", timeout=3)

    def _update_authentication_panel(self) -> None:
        """Update authentication panel visibility based on selected credential type"""
        type_select = self.query_one("#credential_type", Select)
        cred_type_id = type_select.value

        if cred_type_id is Select.BLANK or cred_type_id is None:
            # No type selected, hide all
            self.query_one("#username_password_fields", Vertical).add_class("hidden")
            self.query_one("#token_field", Vertical).add_class("hidden")
            self.query_one("#vault_fields", Vertical).add_class("hidden")
            self.query_one("#kubernetes_fields", Vertical).add_class("hidden")
            self.query_one("#priv_esc_fields", Vertical).add_class("hidden")
            self.query_one("#ssh_key_section", Container).add_class("hidden")
            return

        # Get the kind for this credential type
        kind = self.credential_type_map.get(cred_type_id, "")

        # Show/hide sections based on kind
        if kind == "ssh":  # Machine
            self.query_one("#username_password_fields", Vertical).remove_class("hidden")
            self.query_one("#token_field", Vertical).add_class("hidden")
            self.query_one("#vault_fields", Vertical).add_class("hidden")
            self.query_one("#kubernetes_fields", Vertical).add_class("hidden")
            self.query_one("#priv_esc_fields", Vertical).remove_class("hidden")
            self.query_one("#ssh_key_section", Container).remove_class("hidden")

        elif kind == "scm":  # Source Control
            self.query_one("#username_password_fields", Vertical).remove_class("hidden")
            self.query_one("#token_field", Vertical).add_class("hidden")
            self.query_one("#vault_fields", Vertical).add_class("hidden")
            self.query_one("#kubernetes_fields", Vertical).add_class("hidden")
            self.query_one("#priv_esc_fields", Vertical).add_class("hidden")
            self.query_one("#ssh_key_section", Container).remove_class("hidden")

        elif kind == "token":  # PATs (GitHub, GitLab)
            self.query_one("#username_password_fields", Vertical).add_class("hidden")
            self.query_one("#token_field", Vertical).remove_class("hidden")
            self.query_one("#vault_fields", Vertical).add_class("hidden")
            self.query_one("#kubernetes_fields", Vertical).add_class("hidden")
            self.query_one("#priv_esc_fields", Vertical).add_class("hidden")
            self.query_one("#ssh_key_section", Container).add_class("hidden")

        elif kind == "vault":  # Vault
            self.query_one("#username_password_fields", Vertical).add_class("hidden")
            self.query_one("#token_field", Vertical).add_class("hidden")
            self.query_one("#vault_fields", Vertical).remove_class("hidden")
            self.query_one("#kubernetes_fields", Vertical).add_class("hidden")
            self.query_one("#priv_esc_fields", Vertical).add_class("hidden")
            self.query_one("#ssh_key_section", Container).add_class("hidden")

        elif kind == "kubernetes":  # Kubernetes
            self.query_one("#username_password_fields", Vertical).add_class("hidden")
            self.query_one("#token_field", Vertical).add_class("hidden")
            self.query_one("#vault_fields", Vertical).add_class("hidden")
            self.query_one("#kubernetes_fields", Vertical).remove_class("hidden")
            self.query_one("#priv_esc_fields", Vertical).add_class("hidden")
            self.query_one("#ssh_key_section", Container).add_class("hidden")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes - update form when credential type changes"""
        if event.select.id == "credential_type":
            self._update_authentication_panel()

    def _load_state(self) -> None:
        """Load form state from app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = self.app.create_mode_state.get(self.create_type, {})
        if not state:
            return

        # Restore text inputs
        for field_id in [
            "name",
            "description",
            "username",
            "password",
            "token",
            "vault_password",
            "vault_id",
            "priv_username",
            "priv_password",
            "ssh_passphrase",
            "k8s_host",
            "k8s_bearer_token",
            "k8s_ca_cert",
        ]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Input)
                widget.value = state[field_id]

        # Restore select widgets
        for field_id in ["organization", "credential_type", "priv_method"]:
            if field_id in state:
                widget = self.query_one(f"#{field_id}", Select)
                widget.value = state[field_id]

        # Restore checkboxes
        if "k8s_verify_ssl" in state:
            widget = self.query_one("#k8s_verify_ssl", Checkbox)
            widget.value = state["k8s_verify_ssl"]

        # Restore SSH key TextArea
        if "ssh_key" in state:
            widget = self.query_one("#ssh_key_area", TextArea)
            widget.text = state["ssh_key"]

    def _save_state(self) -> None:
        """Save current form state to app.create_mode_state"""
        if not hasattr(self.app, "create_mode_state"):
            return

        state = {}

        # Save text inputs
        for field_id in [
            "name",
            "description",
            "username",
            "password",
            "token",
            "vault_password",
            "vault_id",
            "priv_username",
            "priv_password",
            "ssh_passphrase",
            "k8s_host",
            "k8s_bearer_token",
            "k8s_ca_cert",
        ]:
            widget = self.query_one(f"#{field_id}", Input)
            state[field_id] = widget.value

        # Save select widgets
        for field_id in ["organization", "credential_type", "priv_method"]:
            widget = self.query_one(f"#{field_id}", Select)
            state[field_id] = widget.value

        # Save checkboxes
        k8s_verify_widget = self.query_one("#k8s_verify_ssl", Checkbox)
        state["k8s_verify_ssl"] = k8s_verify_widget.value

        # Save SSH key TextArea
        widget = self.query_one("#ssh_key_area", TextArea)
        state["ssh_key"] = widget.text

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
        if create_type == "credential":
            # Already on credential screen, do nothing
            return
        elif create_type == "project":
            from awx_tui.screens.create_project import CreateProjectScreen

            self.app.pop_screen()
            self.app.push_screen(CreateProjectScreen())
        elif create_type == "job_template":
            from awx_tui.screens.create_job_template import CreateJobTemplateScreen

            self.app.pop_screen()
            self.app.push_screen(CreateJobTemplateScreen())
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
        # Get basic fields
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get Select values and convert NoSelection to None
        organization_id = self.query_one("#organization", Select).value
        if organization_id is Select.BLANK:
            organization_id = None

        credential_type_id = self.query_one("#credential_type", Select).value
        if credential_type_id is Select.BLANK:
            credential_type_id = None

        # Validate required fields
        if not name:
            self.notify("Credential name is required", severity="error", timeout=3)
            self.query_one("#name", Input).focus()
            return

        if not organization_id:
            self.notify("Organization is required", severity="error", timeout=3)
            return

        if not credential_type_id:
            self.notify("Credential type is required", severity="error", timeout=3)
            return

        # Get the kind for validation and field reading
        kind = self.credential_type_map.get(credential_type_id, "")

        # Build credential data - inputs object contains type-specific fields
        credential_data = {
            "name": name,
            "description": description,
            "organization": organization_id,
            "credential_type": credential_type_id,
            "inputs": {},  # Type-specific fields go here
        }

        # Add type-specific fields based on kind
        if kind == "ssh":  # Machine
            username = self.query_one("#username", Input).value.strip()
            password = self.query_one("#password", Input).value.strip()
            ssh_key = self.query_one("#ssh_key_area", TextArea).text.strip()
            ssh_passphrase = self.query_one("#ssh_passphrase", Input).value.strip()
            priv_method = self.query_one("#priv_method", Select).value
            priv_username = self.query_one("#priv_username", Input).value.strip()
            priv_password = self.query_one("#priv_password", Input).value.strip()

            if username:
                credential_data["inputs"]["username"] = username
            if password:
                credential_data["inputs"]["password"] = password
            if ssh_key:
                credential_data["inputs"]["ssh_key_data"] = ssh_key
            if ssh_passphrase:
                credential_data["inputs"]["ssh_key_unlock"] = ssh_passphrase
            if priv_method:
                credential_data["inputs"]["become_method"] = priv_method
            if priv_username:
                credential_data["inputs"]["become_username"] = priv_username
            if priv_password:
                credential_data["inputs"]["become_password"] = priv_password

        elif kind == "scm":  # Source Control
            username = self.query_one("#username", Input).value.strip()
            password = self.query_one("#password", Input).value.strip()
            ssh_key = self.query_one("#ssh_key_area", TextArea).text.strip()
            ssh_passphrase = self.query_one("#ssh_passphrase", Input).value.strip()

            if username:
                credential_data["inputs"]["username"] = username
            if password:
                credential_data["inputs"]["password"] = password
            if ssh_key:
                credential_data["inputs"]["ssh_key_data"] = ssh_key
            if ssh_passphrase:
                credential_data["inputs"]["ssh_key_unlock"] = ssh_passphrase

        elif kind == "token":  # PATs (GitHub, GitLab)
            token = self.query_one("#token", Input).value.strip()

            if not token:
                self.notify("Token is required", severity="error", timeout=3)
                self.query_one("#token", Input).focus()
                return

            credential_data["inputs"]["token"] = token

        elif kind == "vault":  # Vault
            vault_password = self.query_one("#vault_password", Input).value.strip()
            vault_id = self.query_one("#vault_id", Input).value.strip()

            if not vault_password:
                self.notify("Vault password is required", severity="error", timeout=3)
                self.query_one("#vault_password", Input).focus()
                return

            credential_data["inputs"]["vault_password"] = vault_password
            if vault_id:
                credential_data["inputs"]["vault_id"] = vault_id

        elif kind == "kubernetes":  # Kubernetes
            k8s_host = self.query_one("#k8s_host", Input).value.strip()
            k8s_bearer_token = self.query_one("#k8s_bearer_token", Input).value.strip()
            k8s_ca_cert = self.query_one("#k8s_ca_cert", Input).value.strip()
            k8s_verify_ssl = self.query_one("#k8s_verify_ssl", Checkbox).value

            if not k8s_bearer_token:
                self.notify("Bearer token is required", severity="error", timeout=3)
                self.query_one("#k8s_bearer_token", Input).focus()
                return

            if k8s_host:
                credential_data["inputs"]["host"] = k8s_host
            credential_data["inputs"]["bearer_token"] = k8s_bearer_token
            if k8s_ca_cert:
                credential_data["inputs"]["ssl_ca_cert"] = k8s_ca_cert
            credential_data["inputs"]["verify_ssl"] = k8s_verify_ssl

        # Create the credential via API (async)
        self.run_worker(self._create_credential_async(credential_data, name))

    async def _create_credential_async(self, credential_data: dict, name: str) -> None:
        """Async method to create credential via API"""
        try:
            self.notify(f"Creating credential '{name}'...", timeout=2)

            instance_manager = self.app.instance_manager
            client = instance_manager.get_current_client()

            async with client:
                # POST to /api/v2/credentials/
                response = await client.post("credentials/", data=credential_data)
                credential_id = response.get("id")
                credential_name = response.get("name")

                # Clear state after successful creation
                self._clear_state()

                # Show success notification
                self.notify(
                    f"[green]✓[/green] Credential '{credential_name}' created (ID: {credential_id})",
                    severity="information",
                    timeout=5,
                )

                # Close the screen
                self.app.pop_screen()

        except Exception as e:
            # Show error notification
            error_msg = str(e)
            self.notify(f"[red]✗[/red] Failed to create credential: {error_msg}", severity="error", timeout=10)

    def action_clear_form(self) -> None:
        """Clear all form fields"""
        # Clear text inputs
        for field_id in [
            "name",
            "description",
            "username",
            "password",
            "token",
            "vault_password",
            "vault_id",
            "priv_username",
            "priv_password",
            "ssh_passphrase",
            "k8s_host",
            "k8s_bearer_token",
            "k8s_ca_cert",
        ]:
            widget = self.query_one(f"#{field_id}", Input)
            widget.value = ""

        # Reset checkboxes
        k8s_verify_widget = self.query_one("#k8s_verify_ssl", Checkbox)
        k8s_verify_widget.value = True  # Default to verified

        # Reset select widgets to first option
        org_widget = self.query_one("#organization", Select)
        if org_widget._options:
            org_widget.value = org_widget._options[0][1]

        type_widget = self.query_one("#credential_type", Select)
        if type_widget._options:
            type_widget.value = type_widget._options[0][1]

        priv_method_widget = self.query_one("#priv_method", Select)
        priv_method_widget.value = "sudo"

        # Clear SSH key TextArea
        ssh_key_widget = self.query_one("#ssh_key_area", TextArea)
        ssh_key_widget.text = ""

        # Clear saved state
        self._clear_state()

        # Update authentication panel for new type
        self._update_authentication_panel()

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
        await self._populate_credential_types()
        self.notify("Dropdown data reloaded", timeout=2)

    def action_preview_json(self) -> None:
        """Preview the JSON payload that will be sent to the API"""
        from awx_tui.modals.json_preview import JsonPreviewModal

        # Build credential data from current form values (no validation)
        credential_data, notes = self._build_credential_data_for_preview()

        # Show the JSON preview modal
        self.app.push_screen(
            JsonPreviewModal(
                json_data=credential_data,
                title="Credential Creation - API Payload Preview",
                endpoint="/api/v2/credentials/",
                method="POST",
                notes=notes,
            )
        )

    def _build_credential_data_for_preview(self) -> tuple:
        """Build credential data dict from current form values (for preview, no validation)

        Returns:
            tuple: (credential_data dict, notes list)
        """
        # Get basic fields
        name = self.query_one("#name", Input).value.strip()
        description = self.query_one("#description", Input).value.strip()

        # Get Select values
        organization_id = self.query_one("#organization", Select).value
        if organization_id is Select.BLANK:
            organization_id = None

        credential_type_id = self.query_one("#credential_type", Select).value
        if credential_type_id is Select.BLANK:
            credential_type_id = None

        # Get the kind for the credential type
        kind = self.credential_type_map.get(credential_type_id, "") if credential_type_id else ""

        # Build credential data
        credential_data = {
            "name": name or "REQUIRED",
            "description": description,
            "organization": organization_id or "REQUIRED",
            "credential_type": credential_type_id or "REQUIRED",
            "inputs": {},
        }

        # Add type-specific fields based on kind
        if kind == "ssh":  # Machine
            username = self.query_one("#username", Input).value.strip()
            password = self.query_one("#password", Input).value.strip()
            ssh_key = self.query_one("#ssh_key_area", TextArea).text.strip()
            ssh_passphrase = self.query_one("#ssh_passphrase", Input).value.strip()
            priv_method = self.query_one("#priv_method", Select).value
            priv_username = self.query_one("#priv_username", Input).value.strip()
            priv_password = self.query_one("#priv_password", Input).value.strip()

            if username:
                credential_data["inputs"]["username"] = username
            if password:
                credential_data["inputs"]["password"] = password
            if ssh_key:
                credential_data["inputs"]["ssh_key_data"] = ssh_key
            if ssh_passphrase:
                credential_data["inputs"]["ssh_key_unlock"] = ssh_passphrase
            if priv_method:
                credential_data["inputs"]["become_method"] = priv_method
            if priv_username:
                credential_data["inputs"]["become_username"] = priv_username
            if priv_password:
                credential_data["inputs"]["become_password"] = priv_password

        elif kind == "scm":  # Source Control
            username = self.query_one("#username", Input).value.strip()
            password = self.query_one("#password", Input).value.strip()
            ssh_key = self.query_one("#ssh_key_area", TextArea).text.strip()
            ssh_passphrase = self.query_one("#ssh_passphrase", Input).value.strip()

            if username:
                credential_data["inputs"]["username"] = username
            if password:
                credential_data["inputs"]["password"] = password
            if ssh_key:
                credential_data["inputs"]["ssh_key_data"] = ssh_key
            if ssh_passphrase:
                credential_data["inputs"]["ssh_key_unlock"] = ssh_passphrase

        elif kind == "token":  # PATs
            token = self.query_one("#token", Input).value.strip()
            if token:
                credential_data["inputs"]["token"] = token
            else:
                credential_data["inputs"]["token"] = "REQUIRED"  # NOSONAR

        elif kind == "vault":  # Vault
            vault_password = self.query_one("#vault_password", Input).value.strip()
            vault_id = self.query_one("#vault_id", Input).value.strip()

            if vault_password:
                credential_data["inputs"]["vault_password"] = vault_password
            else:
                credential_data["inputs"]["vault_password"] = "REQUIRED"
            if vault_id:
                credential_data["inputs"]["vault_id"] = vault_id

        elif kind == "kubernetes":  # Kubernetes
            k8s_host = self.query_one("#k8s_host", Input).value.strip()
            k8s_bearer_token = self.query_one("#k8s_bearer_token", Input).value.strip()
            k8s_ca_cert = self.query_one("#k8s_ca_cert", Input).value.strip()
            k8s_verify_ssl = self.query_one("#k8s_verify_ssl", Checkbox).value

            if k8s_host:
                credential_data["inputs"]["host"] = k8s_host
            if k8s_bearer_token:
                credential_data["inputs"]["bearer_token"] = k8s_bearer_token
            else:
                credential_data["inputs"]["bearer_token"] = "REQUIRED"
            if k8s_ca_cert:
                credential_data["inputs"]["ssl_ca_cert"] = k8s_ca_cert
            credential_data["inputs"]["verify_ssl"] = k8s_verify_ssl

        # No additional notes for credentials
        notes = []

        return credential_data, notes

    def action_close(self) -> None:
        """Close create credential screen and save state"""
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
        """Export credential as Ansible task using awx.awx.credential module"""
        from awx_tui.modals.task_export import TaskExportModal
        from awx_tui.utils.ansible_mapper import credential_to_ansible_task

        # Build credential data with resolved names
        credential_data = self._build_ansible_task_data()

        # Convert to Ansible task YAML
        yaml_str, notes = credential_to_ansible_task(credential_data)

        # Show export modal
        self.app.push_screen(
            TaskExportModal(
                task_yaml=yaml_str,
                title="Export AP Task - Credential",
                module_name="credential",
                notes=notes,
            )
        )

    def _build_ansible_task_data(self) -> dict:
        """Build credential data dict with resolved dropdown names for Ansible task export

        Returns:
            dict: Credential data with names instead of IDs where possible
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

        # Get credential type ID and resolve to name
        credential_type_id = self.query_one("#credential_type", Select).value
        credential_type_name = None
        if credential_type_id and credential_type_id is not Select.BLANK:
            ct_select = self.query_one("#credential_type", Select)
            # Find the selected option's display name
            for option in ct_select._options:
                if option[1] == credential_type_id:
                    credential_type_name = option[0]
                    break

        # Build credential data
        credential_data = {
            "name": name,
        }

        if description:
            credential_data["description"] = description

        # Add organization (prefer name, fallback to ID)
        if organization_name:
            credential_data["organization_name"] = organization_name
        elif organization_id and organization_id is not Select.BLANK:
            credential_data["organization"] = organization_id

        # Add credential type (prefer name, fallback to ID)
        if credential_type_name:
            credential_data["credential_type_name"] = credential_type_name
        elif credential_type_id and credential_type_id is not Select.BLANK:
            credential_data["credential_type"] = credential_type_id

        # Collect inputs (sensitive data)
        inputs = {}

        # Try to get common input fields (these may or may not exist depending on credential type)
        input_field_ids = [
            "username",
            "password",
            "ssh_key_data",
            "ssh_key_unlock",
            "vault_password",
            "vault_id",
            "become_method",
            "become_username",
            "become_password",
            "authorize",
            "authorize_password",
        ]

        for field_id in input_field_ids:
            try:
                widget = self.query_one(f"#{field_id}", Input)
                value = widget.value.strip()
                if value:
                    inputs[field_id] = value
            except Exception:
                # Field doesn't exist for this credential type, skip
                pass

        # Add inputs if any were found
        if inputs:
            credential_data["inputs"] = inputs

        return credential_data
