"""
Tests for Instance Manager
"""

import pytest

from awx_tui.client import AWXClient
from awx_tui.config import AppConfig, InstanceConfig
from awx_tui.instance_manager import InstanceManager
from awx_tui.mock_data import MockAWXClient


class TestInstanceManagerMockMode:
    """Test InstanceManager in mock mode"""

    def test_mock_mode_creates_seven_instances(self):
        """Test mock mode creates all 7 mock instances"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        assert manager.has_instances()
        assert len(manager.get_instance_names()) == 7
        assert "mock-prod" in manager.get_instance_names()
        assert "mock-dev" in manager.get_instance_names()
        assert "mock-staging" in manager.get_instance_names()

    def test_mock_mode_clients_are_mock(self):
        """Test mock mode creates MockAWXClient instances"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        # Switch to an instance first (no auto-selection anymore)
        manager.switch_to("mock-prod")
        client = manager.get_current_client()
        assert isinstance(client, MockAWXClient)

    def test_mock_mode_is_detected(self):
        """Test is_mock_mode returns True"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        assert manager.is_mock_mode() is True


class TestInstanceManagerRealMode:
    """Test InstanceManager in real mode"""

    def test_real_mode_with_no_instances(self):
        """Test real mode with empty config"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=False)

        assert not manager.has_instances()
        assert manager.get_current_instance_name() is None

    def test_real_mode_loads_instances_from_config(self):
        """Test real mode loads instances from config"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )

        manager = InstanceManager(config, mock_mode=False)

        assert manager.has_instances()
        assert "test-awx" in manager.get_instance_names()

    def test_real_mode_is_not_mock(self):
        """Test is_mock_mode returns False"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=False)

        assert manager.is_mock_mode() is False


class TestInstanceManagerSwitching:
    """Test switching between instances"""

    def test_switch_to_valid_instance(self):
        """Test switching to a valid instance"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        manager.switch_to("mock-dev")

        assert manager.get_current_instance_name() == "mock-dev"

    def test_switch_to_invalid_instance_raises(self):
        """Test switching to invalid instance raises KeyError"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        with pytest.raises(KeyError, match="not found"):
            manager.switch_to("nonexistent")


class TestInstanceManagerAddRemove:
    """Test adding and removing instances"""

    def test_add_instance_real_mode(self):
        """Test adding instance in real mode"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=False)

        instance = InstanceConfig(
            name="new-awx", url="https://new.example.com", auth_method="token", username="admin", token="new-token"
        )

        manager.add_instance(instance)

        assert "new-awx" in manager.get_instance_names()
        assert manager.get_current_instance_name() == "new-awx"

    def test_add_duplicate_instance_raises(self):
        """Test adding duplicate instance raises ValueError"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        instance = InstanceConfig(
            name="mock-prod",  # Already exists
            url="https://test.example.com",
            auth_method="token",
            username="admin",
            token="token",
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.add_instance(instance)

    def test_add_reserved_mock_name_in_real_mode_raises(self):
        """Test adding reserved mock name in real mode raises ValueError"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=False)

        instance = InstanceConfig(
            name="mock-prod",  # Reserved name
            url="https://test.example.com",
            auth_method="token",
            username="admin",
            token="token",
        )

        with pytest.raises(ValueError, match="reserved"):
            manager.add_instance(instance)

    def test_remove_instance(self):
        """Test removing instance"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )
        manager = InstanceManager(config, mock_mode=False)

        manager.add_instance(
            InstanceConfig(
                name="awx-2", url="https://awx2.example.com", auth_method="token", username="admin", token="token2"
            )
        )

        # Switch away from test-awx
        manager.switch_to("awx-2")

        manager.remove_instance("test-awx")

        assert "test-awx" not in manager.get_instance_names()

    def test_remove_nonexistent_instance_raises(self):
        """Test removing nonexistent instance raises KeyError"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        with pytest.raises(KeyError, match="not found"):
            manager.remove_instance("nonexistent")

    def test_remove_current_instance_with_others_raises(self):
        """Test removing current instance when others exist raises ValueError"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        # Switch to an instance first (no auto-selection)
        manager.switch_to("mock-prod")

        with pytest.raises(ValueError, match="Cannot remove current instance"):
            manager.remove_instance(manager.get_current_instance_name())

    def test_remove_last_instance_clears_current(self):
        """Test removing last instance clears current_instance"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )
        manager = InstanceManager(config, mock_mode=False)

        manager.remove_instance("test-awx")

        assert manager.get_current_instance_name() is None
        assert not manager.has_instances()


class TestInstanceManagerClients:
    """Test client management"""

    def test_get_current_client_mock_mode(self):
        """Test get_current_client returns MockAWXClient in mock mode"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        # Switch to an instance first (no auto-selection)
        manager.switch_to("mock-prod")
        client = manager.get_current_client()

        assert isinstance(client, MockAWXClient)

    def test_get_current_client_real_mode(self):
        """Test get_current_client returns AWXClient in real mode"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )
        manager = InstanceManager(config, mock_mode=False)

        # Switch to an instance first (no auto-selection)
        manager.switch_to("test-awx")
        client = manager.get_current_client()

        assert isinstance(client, AWXClient)

    def test_get_current_client_no_instance_raises(self):
        """Test get_current_client raises when no instance selected"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=False)

        with pytest.raises(RuntimeError, match="No instance selected"):
            manager.get_current_client()

    def test_get_current_client_caches_awx_client(self):
        """Test AWXClient is cached after first creation"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )
        manager = InstanceManager(config, mock_mode=False)

        # Switch to an instance first (no auto-selection)
        manager.switch_to("test-awx")
        client1 = manager.get_current_client()
        client2 = manager.get_current_client()

        # Should be the same object (cached)
        assert client1 is client2


class TestInstanceManagerHelpers:
    """Test helper methods"""

    def test_get_current_instance_config(self):
        """Test get_current_instance_config returns config"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )
        manager = InstanceManager(config, mock_mode=False)

        # Switch to an instance first (no auto-selection)
        manager.switch_to("test-awx")
        instance_config = manager.get_current_instance_config()

        assert instance_config is not None
        assert instance_config.name == "test-awx"
        assert instance_config.url == "https://awx.example.com"

    def test_get_all_instances_returns_copy(self):
        """Test get_all_instances returns a copy"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        instances1 = manager.get_all_instances()
        instances2 = manager.get_all_instances()

        # Should be equal but not the same object
        assert instances1 == instances2
        assert instances1 is not instances2

    def test_is_mock_instance_current(self):
        """Test is_mock_instance detects mock instances"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        # Switch to an instance first (no auto-selection)
        manager.switch_to("mock-prod")

        assert manager.is_mock_instance() is True
        assert manager.is_mock_instance("mock-prod") is True
        assert manager.is_mock_instance("mock-dev") is True

    def test_is_mock_instance_real(self):
        """Test is_mock_instance returns False for real instances"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )
        manager = InstanceManager(config, mock_mode=False)

        assert manager.is_mock_instance() is False
        assert manager.is_mock_instance("test-awx") is False

    def test_get_instance_display_name_mock(self):
        """Test display name for mock instances"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        display = manager.get_instance_display_name("mock-prod")

        assert "🧪" in display
        assert "mock-prod" in display

    def test_get_instance_display_name_env_vars(self):
        """Test display name for @env-vars instance"""
        config = AppConfig()
        config.instances["@env-vars"] = InstanceConfig(
            name="@env-vars", url="https://env.example.com", auth_method="token", username="admin", token="token"
        )
        manager = InstanceManager(config, mock_mode=False)

        display = manager.get_instance_display_name("@env-vars")

        assert "🌍" in display
        assert "@env-vars" in display

    def test_get_instance_display_name_real(self):
        """Test display name for real instances"""
        config = AppConfig()
        config.instances["test-awx"] = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token"
        )
        manager = InstanceManager(config, mock_mode=False)

        display = manager.get_instance_display_name("test-awx")

        assert display == "test-awx"
        assert "🧪" not in display
        assert "🌍" not in display


@pytest.mark.asyncio
class TestInstanceManagerAsync:
    """Test async methods"""

    async def test_test_connection_mock_always_succeeds(self):
        """Test connection test for mock instances always succeeds"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=True)

        # Switch to an instance first (no auto-selection)
        manager.switch_to("mock-prod")

        result = await manager.test_connection()

        assert result is True

    async def test_test_connection_no_instance_returns_false(self):
        """Test connection test with no instance returns False"""
        config = AppConfig()
        manager = InstanceManager(config, mock_mode=False)

        result = await manager.test_connection()

        assert result is False


@pytest.mark.asyncio
class TestInstanceManagerCleanup:
    """Test client cleanup and session lifecycle"""

    async def test_close_all_clients(self):
        """Test close_all_clients closes all AWXClient sessions"""
        config = AppConfig()
        config.instances["awx-1"] = InstanceConfig(
            name="awx-1", url="https://awx1.example.com", auth_method="token", username="admin", token="token1"
        )
        config.instances["awx-2"] = InstanceConfig(
            name="awx-2", url="https://awx2.example.com", auth_method="token", username="admin", token="token2"
        )
        manager = InstanceManager(config, mock_mode=False)

        # Get clients to trigger creation and open sessions
        manager.switch_to("awx-1")
        client1 = manager.get_current_client()
        async with client1:
            pass  # Opens the session

        manager.switch_to("awx-2")
        client2 = manager.get_current_client()
        async with client2:
            pass  # Opens the session

        # Both sessions should be open
        assert client1.session is not None
        assert client2.session is not None

        # Close all
        await manager.close_all_clients()

        # Sessions should be torn down
        assert client1.session is None
        assert client2.session is None
