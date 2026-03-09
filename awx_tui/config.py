"""
AWX TUI - Configuration Management

Handles loading, saving, and managing instance configurations.
"""

import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from httpx import URL


@dataclass
class InstanceConfig:
    """Configuration for a single AWX instance"""

    name: str
    url: str
    auth_method: Optional[str] = None  # "token", "password", or None for no auth
    username: Optional[str] = None
    token: Optional[str] = None
    password: Optional[str] = None
    verify_ssl: bool = True
    api_base_path: str = "/api/v2"
    description: str = ""
    dashboard: str = "classic"  # Dashboard layout to use for this instance
    last_status: Optional[str] = None
    last_checked: Optional[str] = None
    last_response_time: Optional[str] = None

    def validate(self) -> None:
        """
        Validate instance configuration

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate name
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
            raise ValueError(
                f"Instance name '{self.name}' contains invalid characters. "
                "Use only alphanumeric, hyphens, and underscores."
            )

        if len(self.name) > 64:
            raise ValueError(f"Instance name '{self.name}' exceeds 64 characters")

        # Check for reserved names
        reserved = ["mock-prod", "mock-dev", "mock-staging", "@env-vars", "@cli-args"]
        if self.name in reserved:
            raise ValueError(f"Instance name '{self.name}' is reserved")

        # Validate URL
        if not self.url.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://, got: {self.url}")

        # Normalize the URL using httpx.URL (same normalization httpx applies to response.url).
        # This strips redundant default ports (https:443, http:80) so that error-path
        # log entries (which use self.config.url) are consistent with success-path log
        # entries (which use str(response.url) from httpx).
        self.url = str(URL(self.url))

        # Validate auth method (if provided)
        if self.auth_method is not None and self.auth_method not in ("token", "password"):
            raise ValueError(f"auth_method must be 'token', 'password', or None, got: {self.auth_method}")

        # Validate credentials only if auth method is set
        if self.auth_method == "token":
            if not self.token:
                raise ValueError("Token is required when auth_method is 'token'")
            if not self.username:
                raise ValueError("Username is required when auth_method is 'token'")

        if self.auth_method == "password":
            if not self.password:
                raise ValueError("Password is required when auth_method is 'password'")
            if not self.username:
                raise ValueError("Username is required when auth_method is 'password'")

        # Validate username length if provided
        if self.username and len(self.username) > 150:
            raise ValueError("Username exceeds 150 characters")


@dataclass
class AppConfig:
    """Application configuration"""

    instances: Dict[str, InstanceConfig] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(
        default_factory=lambda: {
            "instance_selection_refresh_interval": 5,  # Seconds to refresh instance list
            "dashboard_refresh_interval": 5,  # Seconds to auto-refresh dashboard
            "dashboard_refresh_timeout": 30,  # Seconds before considering refresh stuck
            "dashboard_refresh_interval_running": 1,
            "dashboard_refresh_interval_capacity": 1,
            "dashboard_refresh_interval_recent": 1,
            "dashboard_refresh_interval_graphs": 1,
            "dashboard_refresh_interval_stats": 1,
            "dashboard_auto_refresh": True,
            "job_detail_refresh_interval": 1,
            "job_detail_auto_follow": True,
            "show_instance_in_header": True,
            "mock_mode": False,
        }
    )


class ConfigManager:
    """
    Manages application configuration

    - Loads config from ~/.config/awx-tui/config.yaml
    - Saves config with 0600 permissions
    - Handles environment variable overrides
    - Validates instance configurations
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".config" / "awx-tui"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager

        Args:
            config_path: Path to config file (default: ~/.config/awx-tui/config.yaml)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_FILE
        self.config: Optional[AppConfig] = None

    def load(self, cli_args=None) -> AppConfig:
        """
        Load configuration from file, environment variables, and CLI args

        Args:
            cli_args: Command-line arguments for creating @cli-args instance

        Returns:
            AppConfig with merged configuration

        Note:
            If config file doesn't exist, returns default config
            Creates @env-vars instance if AWX_HOST is set
            Creates @cli-args instance if --host is provided
        """
        # Start with default config
        config = AppConfig()

        # Load from file if exists
        if self.config_path.exists():
            config = self._load_from_file()

        # Merge environment variables (creates @env-vars instance)
        self._merge_env_vars(config)

        # Merge CLI arguments (creates @cli-args instance)
        if cli_args:
            self._merge_cli_args(config, cli_args)

        self.config = config
        return config

    def _load_from_file(self) -> AppConfig:
        """Load configuration from YAML file"""
        # Validate file permissions before reading
        self._validate_file_permissions()

        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {self.config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error reading {self.config_path}: {e}")

        try:

            # Parse instances
            instances = {}
            for name, instance_data in data.get("instances", {}).items():
                # Expand environment variables in config values
                instance_data = self._expand_env_vars(instance_data)

                # Handle nested auth structure
                auth = instance_data.get("auth", {})
                instance = InstanceConfig(
                    name=name,
                    url=instance_data.get("url", ""),
                    auth_method=auth.get("method", instance_data.get("auth_method")),
                    username=auth.get("username", instance_data.get("username")),
                    token=auth.get("token", instance_data.get("token")),
                    password=auth.get("password", instance_data.get("password")),
                    verify_ssl=instance_data.get("verify_ssl", True),
                    api_base_path=instance_data.get("api_base_path", "/api/v2"),
                    description=instance_data.get("description", ""),
                    dashboard=instance_data.get("dashboard", "classic"),
                    last_status=instance_data.get("last_status"),
                    last_checked=instance_data.get("last_checked"),
                    last_response_time=instance_data.get("last_response_time"),
                )

                # Validate (skip credential check - env vars may provide them)
                # Full validation happens after env var merging
                try:
                    instance.validate()
                except ValueError as e:
                    # If only credential is missing, allow it (env vars may provide)
                    if (
                        "Token is required" not in str(e)
                        and "Password is required" not in str(e)
                        and "Username is required" not in str(e)
                    ):
                        # Re-raise for other validation errors (invalid name, URL, etc.)
                        # But log a warning and skip this instance instead of crashing
                        import logging

                        logging.warning(f"Skipping invalid instance '{name}': {e}")
                        continue
                instances[name] = instance

            # Parse preferences
            preferences = data.get("preferences", {})

            # Merge with defaults
            config = AppConfig()
            config.preferences.update(preferences)
            config.instances = instances

            return config

        except Exception as e:
            # Catch parsing errors and provide helpful message
            raise ValueError(f"Error parsing config from {self.config_path}: {e}")

    def _expand_env_vars(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand environment variables in config values

        Supports ${VAR_NAME} syntax

        Args:
            data: Dictionary with potential ${VAR} references

        Returns:
            Dictionary with expanded values
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Replace ${VAR} with environment variable value
                result[key] = re.sub(r"\$\{([^}]+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), value)
            elif isinstance(value, dict):
                result[key] = self._expand_env_vars(value)
            else:
                result[key] = value
        return result

    def _merge_env_vars(self, config: AppConfig) -> None:
        """
        Merge environment variables into config

        Precedence (highest to lowest):
        1. Instance-specific env vars (AWX_PROD_HOST, AWX_PROD_TOKEN)
        2. Generic env vars (AWX_HOST, AWX_TOKEN)
        3. Config file

        Creates temporary "@env-vars" instance if AWX_HOST is set
        """
        # Check for generic env vars (AWX_HOST + AWX_TOKEN/PASSWORD)
        awx_host = os.environ.get("AWX_HOST")
        awx_token = os.environ.get("AWX_TOKEN")
        awx_password = os.environ.get("AWX_PASSWORD")
        awx_user = os.environ.get("AWX_USER", "admin")
        awx_dashboard = os.environ.get("AWX_DASHBOARD", "classic")

        if awx_host and (awx_token or awx_password):
            # Create temporary instance from env vars
            auth_method = "token" if awx_token else "password"
            env_instance = InstanceConfig(
                name="@env-vars",
                url=awx_host,
                auth_method=auth_method,
                username=awx_user,
                token=awx_token,
                password=awx_password,
                verify_ssl=os.environ.get("AWX_VERIFY_SSL", "true").lower() != "false",
                dashboard=awx_dashboard,
                description="From AWX_* environment variables",
            )

            # Don't validate (might be incomplete for testing)
            config.instances["@env-vars"] = env_instance

        # Check for instance-specific env vars (AWX_{NAME}_HOST pattern)
        # These override generic env vars for specific instances
        for instance_name, instance in list(config.instances.items()):
            # Skip special instances (already handled above/below)
            if instance_name.startswith("@"):
                continue

            # Build env var prefix (e.g., "PROD" from "prod-tower")
            # Convert to uppercase and replace hyphens with underscores
            prefix = instance_name.upper().replace("-", "_")

            # Check for instance-specific overrides
            instance_host = os.environ.get(f"AWX_{prefix}_HOST")
            instance_token = os.environ.get(f"AWX_{prefix}_TOKEN")
            instance_password = os.environ.get(f"AWX_{prefix}_PASSWORD")
            instance_user = os.environ.get(f"AWX_{prefix}_USER")
            instance_dashboard = os.environ.get(f"AWX_{prefix}_DASHBOARD")

            # Apply overrides if present
            if instance_host:
                instance.url = instance_host

            if instance_token:
                instance.token = instance_token
                instance.auth_method = "token"

            if instance_password:
                instance.password = instance_password
                instance.auth_method = "password"

            if instance_user:
                instance.username = instance_user

            if instance_dashboard:
                instance.dashboard = instance_dashboard

            # Generic env vars as fallback (if not in config and not instance-specific)
            if not instance.token and not instance.password:
                if awx_token:
                    instance.token = awx_token
                    instance.auth_method = "token"
                elif awx_password:
                    instance.password = awx_password
                    instance.auth_method = "password"

            # Generic dashboard env var as fallback (if not instance-specific)
            if not instance_dashboard and awx_dashboard and instance.dashboard == "classic":
                instance.dashboard = awx_dashboard

        # Check for AWX_MOCK env var
        mock_mode = os.environ.get("AWX_MOCK", "").lower() in ("true", "1", "yes")
        if mock_mode:
            config.preferences["mock_mode"] = True

    def _merge_cli_args(self, config: AppConfig, cli_args) -> None:
        """
        Merge CLI arguments into config

        Creates temporary "@cli-args" instance if --host is provided

        Args:
            config: AppConfig to merge into
            cli_args: Parsed command-line arguments
        """
        # Only create @cli-args instance if --host is provided
        if not cli_args.host:
            return

        # Require either --token or --password
        if not (cli_args.token or cli_args.password):
            return

        # Create temporary instance from CLI args
        auth_method = "token" if cli_args.token else "password"
        cli_instance = InstanceConfig(
            name="@cli-args",
            url=cli_args.host,
            auth_method=auth_method,
            username=cli_args.user or "admin",
            token=cli_args.token,
            password=cli_args.password,
            verify_ssl=not cli_args.no_verify_ssl,
            dashboard=cli_args.dashboard if hasattr(cli_args, "dashboard") and cli_args.dashboard else "classic",
            description="From command-line arguments",
        )

        # Don't validate (might be incomplete for testing)
        config.instances["@cli-args"] = cli_instance

    def save(self, config: Optional[AppConfig] = None) -> None:
        """
        Save configuration to file

        Args:
            config: Config to save (uses self.config if None)
        """
        if config is None:
            config = self.config

        if config is None:
            raise ValueError("No config to save")

        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Build YAML structure
        data = {
            "instances": {},
            "preferences": config.preferences,
        }

        # Convert instances to dict format
        for name, instance in config.instances.items():
            # Skip temporary instances (@env-vars, @cli-args)
            if name.startswith("@"):
                continue

            data["instances"][name] = {
                "url": instance.url,
                "auth": {
                    "method": instance.auth_method,
                    "username": instance.username,
                },
                "verify_ssl": instance.verify_ssl,
                "dashboard": instance.dashboard,
                "description": instance.description,
            }

            # Add credentials
            if instance.token:
                data["instances"][name]["auth"]["token"] = instance.token
            if instance.password:
                data["instances"][name]["auth"]["password"] = instance.password

            # Add cached status
            if instance.last_status:
                data["instances"][name]["last_status"] = instance.last_status
            if instance.last_checked:
                data["instances"][name]["last_checked"] = instance.last_checked

        # Write to file
        with open(self.config_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        # Set permissions to 0600 (owner read/write only)
        os.chmod(self.config_path, 0o600)

    def add_instance(self, instance: InstanceConfig) -> None:
        """
        Add or update instance configuration

        Args:
            instance: Instance configuration to add

        Raises:
            ValueError: If instance name already exists (use update instead)
        """
        if self.config is None:
            self.config = self.load()

        # Validate instance
        instance.validate()

        # Check for duplicates
        if instance.name in self.config.instances:
            raise ValueError(f"Instance '{instance.name}' already exists")

        # Add instance
        self.config.instances[instance.name] = instance

    def update_instance(self, instance: InstanceConfig) -> None:
        """
        Update existing instance configuration

        Args:
            instance: Instance configuration to update

        Raises:
            ValueError: If instance doesn't exist
        """
        if self.config is None:
            self.config = self.load()

        if instance.name not in self.config.instances:
            raise ValueError(f"Instance '{instance.name}' not found")

        # Validate
        instance.validate()

        # Update
        self.config.instances[instance.name] = instance

    def remove_instance(self, name: str) -> None:
        """
        Remove instance configuration

        Args:
            name: Instance name to remove

        Raises:
            ValueError: If instance doesn't exist
        """
        if self.config is None:
            self.config = self.load()

        if name not in self.config.instances:
            raise ValueError(f"Instance '{name}' not found")

        # Remove
        del self.config.instances[name]

    def get_instance(self, name: str) -> Optional[InstanceConfig]:
        """
        Get instance configuration by name

        Args:
            name: Instance name

        Returns:
            InstanceConfig if found, None otherwise
        """
        if self.config is None:
            self.config = self.load()

        return self.config.instances.get(name)

    def get_all_instances(self) -> Dict[str, InstanceConfig]:
        """
        Get all instance configurations

        Returns:
            Dictionary of instance name -> InstanceConfig
        """
        if self.config is None:
            self.config = self.load()

        return self.config.instances

    def _validate_file_permissions(self) -> None:
        """
        Validate that config file has secure permissions (0600).

        Checks that only the owner has read/write access, with no group
        or other permissions. This prevents credential leakage to other
        users on the system.

        Raises:
            ValueError: If file permissions allow group or other access
        """
        # Skip on Windows (different permission model)
        if os.name == "nt":
            return

        # Skip if file doesn't exist
        if not self.config_path.exists():
            return

        # Get file permissions
        file_stat = self.config_path.stat()
        mode = file_stat.st_mode

        # Check for any group or other permissions (security risk)
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            current_mode = oct(mode)[-3:]
            raise ValueError(
                f"Configuration file {self.config_path} has insecure permissions: {current_mode}\n"
                f"For security, config file must not be readable by group or others.\n"
                f"Fix with: chmod 0600 {self.config_path}"
            )
