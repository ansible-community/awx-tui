"""
AWX TUI - Instance Manager

Manages multiple AWX instances and their API clients.
"""

from typing import Dict, List, Optional, Union

import httpx

from awx_tui.client import AWXClient
from awx_tui.config import AppConfig, InstanceConfig
from awx_tui.mock_data import MOCK_INSTANCES, MockAWXClient


class InstanceManagerError(Exception):
    """Base exception for instance manager errors"""

    pass


class InstanceManager:
    """
    Manages multiple AWX instances

    - Creates and maintains AWXClient for each instance
    - Switches between instances
    - Provides current active client
    - Supports mock mode with test instances
    """

    def __init__(
        self,
        config: AppConfig,
        mock_mode: bool = False,
        api_call_log: Optional[list] = None,
        connection_event_log: Optional[list] = None,
    ):
        """
        Initialize instance manager

        Args:
            config: Application configuration
            mock_mode: If True, use mock clients instead of real AWX
            api_call_log: Optional list to log API calls for debug console
            connection_event_log: Optional list to log connection pool events
        """
        self.config = config
        self.mock_mode = mock_mode
        self.api_call_log = api_call_log
        self.connection_event_log = connection_event_log
        self.clients: Dict[str, Union[AWXClient, MockAWXClient]] = {}
        self.current_instance: Optional[str] = None
        self.ping_client: Optional[httpx.AsyncClient] = None

        # Initialize instances
        if mock_mode:
            self._setup_mock_instances()
        else:
            self._setup_real_instances()

        # Don't auto-select an instance - let user choose from instance dashboard

    def _setup_mock_instances(self) -> None:
        """Set up mock instances for development/testing"""
        # Create mock instance configs and clients
        for mock_name, mock_data in MOCK_INSTANCES.items():
            # Create a minimal config for the mock instance
            # Mock instances have credentials (for testing auth flows)
            instance_config = InstanceConfig(
                name=mock_name,
                url=f"https://{mock_name}.example.com",
                auth_method="token",
                username="admin",
                token="mock-token",
                api_base_path="/api/v2",  # Mock instances use standard path
                description=mock_data["description"],
                last_status=mock_data.get("status", "unknown"),
                last_checked="2025-11-20 10:30:00",
            )

            # Add to config
            self.config.instances[mock_name] = instance_config

            # Create mock client
            self.clients[mock_name] = MockAWXClient(mock_name, api_call_log=self.api_call_log)

    def _setup_real_instances(self) -> None:
        """Set up real AWX instances from config"""
        for name, instance_config in self.config.instances.items():
            # Skip reserved mock names
            if name in MOCK_INSTANCES:
                continue

            # Create real AWX client (not connected yet - will connect on first use)
            # We'll use context manager when actually making requests
            # For now, just store the config
            self.clients[name] = instance_config

    def add_instance(self, instance_config: InstanceConfig) -> None:
        """
        Add instance and create client

        Args:
            instance_config: Instance configuration

        Raises:
            ValueError: If instance already exists
            ValueError: If trying to add mock instance in real mode
        """
        # Validate
        if instance_config.name in self.clients:
            raise ValueError(f"Instance '{instance_config.name}' already exists")

        if not self.mock_mode and instance_config.name in MOCK_INSTANCES:
            raise ValueError(f"Cannot add reserved mock instance '{instance_config.name}' in real mode")

        # Add to config
        self.config.instances[instance_config.name] = instance_config

        # Create client
        if self.mock_mode and instance_config.name in MOCK_INSTANCES:
            self.clients[instance_config.name] = MockAWXClient(instance_config.name)
        else:
            # Store config - will create AWXClient when needed
            self.clients[instance_config.name] = instance_config

        # If this is the first instance, make it current
        if self.current_instance is None:
            self.current_instance = instance_config.name

    def remove_instance(self, instance_name: str) -> None:
        """
        Remove instance

        Args:
            instance_name: Name of instance to remove

        Raises:
            KeyError: If instance not found
            ValueError: If trying to remove current instance
        """
        if instance_name not in self.clients:
            raise KeyError(f"Instance '{instance_name}' not found")

        if instance_name == self.current_instance and len(self.clients) > 1:
            raise ValueError(f"Cannot remove current instance '{instance_name}'. " "Switch to another instance first.")

        # Remove from clients and config
        del self.clients[instance_name]
        if instance_name in self.config.instances:
            del self.config.instances[instance_name]

        # If this was the current instance, clear it
        if instance_name == self.current_instance:
            self.current_instance = None
            # Set new default if instances remain
            if self.clients:
                self.current_instance = list(self.clients.keys())[0]

    def switch_to(self, instance_name: str) -> None:
        """
        Switch active instance

        Args:
            instance_name: Name of instance to switch to

        Raises:
            KeyError: If instance not found
        """
        if instance_name not in self.clients:
            raise KeyError(f"Instance '{instance_name}' not found. " f"Available: {', '.join(self.clients.keys())}")

        self.current_instance = instance_name

    def get_client(self, instance_name: str) -> Union[AWXClient, MockAWXClient]:
        """
        Get client for a specific instance

        Args:
            instance_name: Name of instance to get client for

        Returns:
            AWXClient or MockAWXClient for the instance

        Raises:
            KeyError: If instance not found
            RuntimeError: If client not initialized
        """
        if instance_name not in self.clients:
            raise KeyError(f"Instance '{instance_name}' not found. " f"Available: {', '.join(self.clients.keys())}")

        client = self.clients.get(instance_name)
        if client is None:
            raise RuntimeError(f"Client for '{instance_name}' not initialized")

        # If client is an InstanceConfig (real mode), create AWXClient
        if isinstance(client, InstanceConfig):
            # Create and cache the AWXClient
            awx_client = AWXClient(
                client,
                api_call_log=self.api_call_log,
                app_config=self.config,
                connection_event_log=self.connection_event_log,
            )
            self.clients[instance_name] = awx_client
            return awx_client

        # Otherwise it's already a client (mock or previously created AWXClient)
        return client

    def get_current_client(self) -> Union[AWXClient, MockAWXClient]:
        """
        Get client for current instance

        Returns:
            AWXClient or MockAWXClient for current instance

        Raises:
            RuntimeError: If no instance selected
        """
        if self.current_instance is None:
            raise RuntimeError("No instance selected. Add an instance or enable mock mode.")

        return self.get_client(self.current_instance)

    def get_current_instance_name(self) -> Optional[str]:
        """
        Get name of current instance

        Returns:
            Name of current instance, or None if no instance selected
        """
        return self.current_instance

    def get_current_instance_config(self) -> Optional[InstanceConfig]:
        """
        Get config for current instance

        Returns:
            InstanceConfig for current instance, or None if no instance selected
        """
        if self.current_instance is None:
            return None

        return self.config.instances.get(self.current_instance)

    def get_all_instances(self) -> Dict[str, InstanceConfig]:
        """
        Get all configured instances

        Returns:
            Dictionary of instance name -> InstanceConfig
        """
        return self.config.instances.copy()

    def get_instance_names(self) -> List[str]:
        """
        Get list of all instance names

        Returns:
            List of instance names
        """
        return list(self.config.instances.keys())

    def has_instances(self) -> bool:
        """
        Check if any instances are configured

        Returns:
            True if at least one instance exists
        """
        return len(self.clients) > 0

    def is_mock_mode(self) -> bool:
        """
        Check if manager is in mock mode

        Returns:
            True if using mock clients
        """
        return self.mock_mode

    def is_mock_instance(self, instance_name: Optional[str] = None) -> bool:
        """
        Check if an instance is a mock instance

        Args:
            instance_name: Name of instance (uses current if None)

        Returns:
            True if instance is a mock instance
        """
        name = instance_name or self.current_instance
        if name is None:
            return False

        return name in MOCK_INSTANCES

    async def test_connection(self, instance_name: Optional[str] = None) -> bool:
        """
        Test connection to an instance

        Args:
            instance_name: Name of instance to test (uses current if None)

        Returns:
            True if connection successful, False otherwise
        """
        name = instance_name or self.current_instance
        if name is None:
            return False

        # Mock instances always succeed
        if self.is_mock_instance(name):
            return True

        # Get or create client
        client = self.clients.get(name)
        if isinstance(client, InstanceConfig):
            client = AWXClient(client, debug_logger=self.debug_logger)
            self.clients[name] = client

        # Test connection
        if isinstance(client, AWXClient):
            async with client:
                return await client.test_connection()

        # MockAWXClient doesn't need async context
        return True

    async def get_ping_client(self) -> httpx.AsyncClient:
        """Get or create the persistent ping-pool client"""
        if self.ping_client is None or self.ping_client.is_closed:
            from awx_tui.ping_checker import _log_ping_connection_event

            self.ping_client = httpx.AsyncClient(
                verify=False,
                timeout=10.0,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
            _log_ping_connection_event(
                self.connection_event_log, "ping-pool", "POOL_CREATED", "max_connections=10, max_keepalive=5"
            )
        return self.ping_client

    async def close_all_clients(self) -> None:
        """Close all persistent AWXClient sessions and ping pool (for app shutdown)"""
        for client in self.clients.values():
            if isinstance(client, AWXClient):
                await client.close()
        if self.ping_client and not self.ping_client.is_closed:
            from awx_tui.ping_checker import _log_ping_connection_event

            _log_ping_connection_event(
                self.connection_event_log, "ping-pool", "POOL_CLOSED", "Session explicitly closed"
            )
            await self.ping_client.aclose()
            self.ping_client = None

    def get_instance_display_name(self, instance_name: Optional[str] = None) -> str:
        """
        Get display name for instance (with mock indicator if applicable)

        Args:
            instance_name: Name of instance (uses current if None)

        Returns:
            Display name string
        """
        name = instance_name or self.current_instance
        if name is None:
            return "No instance"

        # Add emoji indicators for special instances
        if name == "@env-vars":
            return f"🌍 {name}"
        elif name == "@cli-args":
            return f"⌨️  {name}"
        elif self.is_mock_instance(name):
            return f"🧪 {name}"
        else:
            return name
