"""
Tests for configuration management
"""

import os

import pytest

from awx_tui.config import AppConfig, ConfigManager, InstanceConfig


class TestInstanceConfig:
    """Test InstanceConfig validation"""

    def test_valid_instance(self):
        """Test valid instance config"""
        instance = InstanceConfig(
            name="test-awx",
            url="https://awx.example.com",
            auth_method="token",
            username="admin",
            token="test-token-123",
        )

        # Should not raise
        instance.validate()

    def test_invalid_name_characters(self):
        """Test instance name with invalid characters"""
        instance = InstanceConfig(
            name="test awx",  # Space is invalid
            url="https://awx.example.com",
            auth_method="token",
            username="admin",
            token="test-token",
        )

        with pytest.raises(ValueError, match="invalid characters"):
            instance.validate()

    def test_invalid_name_too_long(self):
        """Test instance name exceeds max length"""
        instance = InstanceConfig(
            name="a" * 65,  # 65 characters
            url="https://awx.example.com",
            auth_method="token",
            username="admin",
            token="test-token",
        )

        with pytest.raises(ValueError, match="exceeds 64 characters"):
            instance.validate()

    def test_reserved_name(self):
        """Test reserved instance names"""
        instance = InstanceConfig(
            name="mock-prod",  # Reserved
            url="https://awx.example.com",
            auth_method="token",
            username="admin",
            token="test-token",
        )

        with pytest.raises(ValueError, match="reserved"):
            instance.validate()

    def test_invalid_url(self):
        """Test invalid URL"""
        instance = InstanceConfig(
            name="test-awx",
            url="awx.example.com",  # Missing http://
            auth_method="token",
            username="admin",
            token="test-token",
        )

        with pytest.raises(ValueError, match="http://"):
            instance.validate()

    def test_token_missing_for_token_auth(self):
        """Test token required when auth_method is token"""
        instance = InstanceConfig(
            name="test-awx",
            url="https://awx.example.com",
            auth_method="token",
            username="admin",
            # token missing!
        )

        with pytest.raises(ValueError, match="Token is required"):
            instance.validate()

    def test_password_missing_for_password_auth(self):
        """Test password required when auth_method is password"""
        instance = InstanceConfig(
            name="test-awx",
            url="https://awx.example.com",
            auth_method="password",
            username="admin",
            # password missing!
        )

        with pytest.raises(ValueError, match="Password is required"):
            instance.validate()

    def test_url_normalizes_default_https_port(self):
        """Test that https with explicit port 443 is normalized"""
        instance = InstanceConfig(
            name="test-awx",
            url="https://awx.example.com:443",
            auth_method="token",
            username="admin",
            token="test-token-123",
        )
        instance.validate()
        assert instance.url == "https://awx.example.com"

    def test_url_normalizes_default_http_port(self):
        """Test that http with explicit port 80 is normalized"""
        instance = InstanceConfig(
            name="test-awx",
            url="http://awx.example.com:80",
            auth_method="token",
            username="admin",
            token="test-token-123",
        )
        instance.validate()
        assert instance.url == "http://awx.example.com"

    def test_url_preserves_non_default_port(self):
        """Test that non-default ports are preserved"""
        instance = InstanceConfig(
            name="test-awx",
            url="https://awx.example.com:8443",
            auth_method="token",
            username="admin",
            token="test-token-123",
        )
        instance.validate()
        assert instance.url == "https://awx.example.com:8443"


class TestConfigManager:
    """Test ConfigManager functionality"""

    def test_load_empty_config(self, tmp_path):
        """Test loading when no config file exists"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        config = manager.load()

        assert isinstance(config, AppConfig)
        assert len(config.instances) == 0
        assert config.preferences["dashboard_auto_refresh"] is True

    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading config"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        # Create test instance
        instance = InstanceConfig(
            name="test-awx",
            url="https://awx.example.com",
            auth_method="token",
            username="admin",
            token="test-token-123",
            description="Test instance",
        )

        # Add and save
        config = AppConfig()
        config.instances["test-awx"] = instance
        manager.save(config)

        # Verify file exists and has correct permissions
        assert config_file.exists()
        assert oct(config_file.stat().st_mode)[-3:] == "600"

        # Load and verify
        manager2 = ConfigManager(config_path=config_file)
        loaded_config = manager2.load()

        assert "test-awx" in loaded_config.instances
        loaded = loaded_config.instances["test-awx"]
        assert loaded.url == "https://awx.example.com"
        assert loaded.token == "test-token-123"
        assert loaded.description == "Test instance"

    def test_env_var_substitution_in_config(self, tmp_path, monkeypatch):
        """Test ${ENV_VAR} substitution in config file"""
        config_file = tmp_path / "config.yaml"

        # Write config with env var reference
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: ${TEST_TOKEN}
    verify_ssl: true
    description: Test instance
""")

        # Set secure permissions
        config_file.chmod(0o600)

        # Set environment variable
        monkeypatch.setenv("TEST_TOKEN", "secret-token-from-env")

        # Load and verify substitution
        manager = ConfigManager(config_path=config_file)
        config = manager.load()

        assert config.instances["test-awx"].token == "secret-token-from-env"

    def test_generic_env_vars_create_instance(self, tmp_path, monkeypatch):
        """Test AWX_HOST + AWX_TOKEN create @env-vars instance"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        # Set environment variables
        monkeypatch.setenv("AWX_HOST", "https://env-awx.example.com")
        monkeypatch.setenv("AWX_TOKEN", "env-token-123")
        monkeypatch.setenv("AWX_USER", "envuser")

        config = manager.load()

        # Should create @env-vars instance
        assert "@env-vars" in config.instances
        env_instance = config.instances["@env-vars"]
        assert env_instance.url == "https://env-awx.example.com"
        assert env_instance.token == "env-token-123"
        assert env_instance.username == "envuser"
        assert env_instance.description == "From AWX_* environment variables"

    def test_instance_specific_env_vars_override(self, tmp_path, monkeypatch):
        """Test AWX_{NAME}_TOKEN overrides config"""
        config_file = tmp_path / "config.yaml"

        # Write config with test-awx instance
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: config-token
    verify_ssl: true
""")

        # Set secure permissions
        config_file.chmod(0o600)

        # Set instance-specific override
        monkeypatch.setenv("AWX_TEST_AWX_TOKEN", "override-token")

        manager = ConfigManager(config_path=config_file)
        config = manager.load()

        # Should use env var token, not config file token
        assert config.instances["test-awx"].token == "override-token"

    def test_generic_env_var_fallback(self, tmp_path, monkeypatch):
        """Test generic AWX_TOKEN as fallback"""
        config_file = tmp_path / "config.yaml"

        # Write config WITHOUT token
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
    verify_ssl: true
""")

        # Set secure permissions
        config_file.chmod(0o600)

        # Set generic token (fallback)
        monkeypatch.setenv("AWX_TOKEN", "fallback-token")

        manager = ConfigManager(config_path=config_file)
        config = manager.load()

        # Should use fallback token
        assert config.instances["test-awx"].token == "fallback-token"

    def test_add_instance(self, tmp_path):
        """Test adding instance"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        instance = InstanceConfig(
            name="new-awx", url="https://new.example.com", auth_method="token", username="admin", token="new-token"
        )

        manager.load()  # Load empty config
        manager.add_instance(instance)

        assert "new-awx" in manager.config.instances

    def test_add_duplicate_instance_fails(self, tmp_path):
        """Test adding duplicate instance raises error"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        instance = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="token"
        )

        manager.load()
        manager.add_instance(instance)

        # Try to add again
        with pytest.raises(ValueError, match="already exists"):
            manager.add_instance(instance)

    def test_update_instance(self, tmp_path):
        """Test updating instance"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        instance = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="old-token"
        )

        manager.load()
        manager.add_instance(instance)

        # Update
        instance.token = "new-token"
        manager.update_instance(instance)

        assert manager.config.instances["test-awx"].token == "new-token"

    def test_remove_instance(self, tmp_path):
        """Test removing instance"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        instance = InstanceConfig(
            name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="token"
        )

        manager.load()
        manager.add_instance(instance)
        assert "test-awx" in manager.config.instances

        # Remove
        manager.remove_instance("test-awx")
        assert "test-awx" not in manager.config.instances

    def test_env_vars_instance_not_saved(self, tmp_path, monkeypatch):
        """Test @env-vars instance is not saved to config"""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        # Set environment variables to create @env-vars instance
        monkeypatch.setenv("AWX_HOST", "https://env-awx.example.com")
        monkeypatch.setenv("AWX_TOKEN", "env-token")

        config = manager.load()
        assert "@env-vars" in config.instances

        # Save
        manager.save()

        # Clear env vars before reloading
        monkeypatch.delenv("AWX_HOST", raising=False)
        monkeypatch.delenv("AWX_TOKEN", raising=False)

        # Re-load from file (without env vars)
        manager2 = ConfigManager(config_path=config_file)
        config2 = manager2.load()

        # @env-vars should not be in loaded config (since env vars are gone)
        assert "@env-vars" not in config2.instances

    def test_load_accepts_0600_permissions(self, tmp_path):
        """Test that loading config with 0600 permissions succeeds"""
        config_file = tmp_path / "config.yaml"

        # Create config with valid content
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: test-token-123
    verify_ssl: true
""")

        # Set secure permissions (0600)
        config_file.chmod(0o600)

        # Should load successfully
        manager = ConfigManager(config_path=config_file)
        config = manager.load()

        assert "test-awx" in config.instances
        assert config.instances["test-awx"].token == "test-token-123"

    def test_load_rejects_0644_permissions(self, tmp_path):
        """Test that loading config with 0644 permissions fails (world-readable)"""
        config_file = tmp_path / "config.yaml"

        # Create config
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: test-token-123
    verify_ssl: true
""")

        # Set insecure permissions (world-readable)
        config_file.chmod(0o644)

        # Should raise ValueError
        manager = ConfigManager(config_path=config_file)
        with pytest.raises(ValueError, match="insecure permissions"):
            manager.load()

    def test_load_rejects_0664_permissions(self, tmp_path):
        """Test that loading config with 0664 permissions fails (group-writable)"""
        config_file = tmp_path / "config.yaml"

        # Create config
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: test-token-123
    verify_ssl: true
""")

        # Set insecure permissions (group-writable, world-readable)
        config_file.chmod(0o664)

        # Should raise ValueError
        manager = ConfigManager(config_path=config_file)
        with pytest.raises(ValueError, match="insecure permissions"):
            manager.load()

    def test_load_accepts_0400_permissions(self, tmp_path):
        """Test that loading config with 0400 permissions succeeds (more restrictive)"""
        config_file = tmp_path / "config.yaml"

        # Create config
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: test-token-123
    verify_ssl: true
""")

        # Set more restrictive permissions (read-only by owner)
        config_file.chmod(0o400)

        # Should load successfully (0400 is more secure than 0600)
        manager = ConfigManager(config_path=config_file)
        config = manager.load()

        assert "test-awx" in config.instances

    def test_load_nonexistent_file_no_permission_check(self, tmp_path):
        """Test that loading non-existent config doesn't raise permission error"""
        config_file = tmp_path / "nonexistent.yaml"

        # Should not raise permission error for non-existent file
        manager = ConfigManager(config_path=config_file)
        config = manager.load()

        # Should return default config
        assert len(config.instances) == 0

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_load_skips_permission_check_on_windows(self, tmp_path):
        """Test that permission check is skipped on Windows"""
        config_file = tmp_path / "config.yaml"

        # Create config
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: test-token-123
    verify_ssl: true
""")

        # On Windows, permissions work differently
        # This test just verifies the check is skipped
        manager = ConfigManager(config_path=config_file)
        config = manager.load()

        assert "test-awx" in config.instances

    def test_permission_error_message_includes_fix_command(self, tmp_path):
        """Test that permission error includes chmod fix command"""
        config_file = tmp_path / "config.yaml"

        # Create config
        config_file.write_text("""
instances:
  test-awx:
    url: https://awx.example.com
    auth:
      method: token
      username: admin
      token: test-token-123
    verify_ssl: true
""")

        # Set insecure permissions
        config_file.chmod(0o644)

        # Should raise error with fix command
        manager = ConfigManager(config_path=config_file)
        with pytest.raises(ValueError) as exc_info:
            manager.load()

        error_msg = str(exc_info.value)
        assert "chmod 0600" in error_msg
        assert str(config_file.resolve()) in error_msg  # Check for absolute path
        assert "644" in error_msg
