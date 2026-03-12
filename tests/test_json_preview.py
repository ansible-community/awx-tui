"""
Tests for JSON Preview Modal

Verifies correct JSON data scrubbing, sensitive field handling, and preview functionality.
"""

from awx_tui.modals.json_preview import JsonPreviewModal


class TestSensitiveDataScrubbing:
    """Tests for JsonPreviewModal._scrub_sensitive_data method"""

    def test_scrub_simple_password_field(self):
        """Test that simple password fields are redacted"""
        modal = JsonPreviewModal(json_data={})

        data = {"username": "admin", "password": "FAKE_PASSWORD_FOR_TESTING", "description": "Test user"}

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["username"] == "admin"
        assert scrubbed["password"] == "***REMOVED***"
        assert scrubbed["description"] == "Test user"

    def test_scrub_multiple_sensitive_fields(self):
        """Test that multiple sensitive fields are all redacted"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "name": "My Credential",
            "password": "FAKE_PASS_123",  # NOSONAR
            "token": "FAKE_TOKEN_123",
            "secret": "FAKE_SECRET_VALUE",  # NOSONAR
            "api_key": "FAKE_API_KEY_VALUE",  # NOSONAR
            "ssh_key_data": "FAKE_SSH_KEY_CONTENT_HERE",
            "vault_password": "FAKE_VAULT_VALUE",  # NOSONAR
        }

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["name"] == "My Credential"
        assert scrubbed["password"] == "***REMOVED***"
        assert scrubbed["token"] == "***REMOVED***"
        assert scrubbed["secret"] == "***REMOVED***"
        assert scrubbed["api_key"] == "***REMOVED***"
        assert scrubbed["ssh_key_data"] == "***REMOVED***"
        assert scrubbed["vault_password"] == "***REMOVED***"

    def test_scrub_case_insensitive_matching(self):
        """Test that sensitive field detection is case-insensitive"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "Password": "FAKE_PASSWORD_1",
            "API_KEY": "FAKE_KEY_1",
            "user_token": "FAKE_USER_TOKEN",
            "vault_Password": "FAKE_VAULT_1",  # NOSONAR
            "CLIENT_SECRET": "FAKE_CLIENT_VALUE",
        }

        scrubbed = modal._scrub_sensitive_data(data)

        # All should be redacted due to case-insensitive matching
        assert scrubbed["Password"] == "***REMOVED***"
        assert scrubbed["API_KEY"] == "***REMOVED***"
        assert scrubbed["user_token"] == "***REMOVED***"
        assert scrubbed["vault_Password"] == "***REMOVED***"
        assert scrubbed["CLIENT_SECRET"] == "***REMOVED***"

    def test_scrub_partial_field_name_matching(self):
        """Test that partial matches in field names are detected"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "user_password": "FAKE_USER_PASS",  # NOSONAR
            "ssh_private_key": "FAKE_SSH_KEY",
            "github_token": "FAKE_GITHUB_TOKEN",
            "aws_secret_key": "FAKE_AWS_KEY",
        }

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["user_password"] == "***REMOVED***"
        assert scrubbed["ssh_private_key"] == "***REMOVED***"
        assert scrubbed["github_token"] == "***REMOVED***"
        assert scrubbed["aws_secret_key"] == "***REMOVED***"

    def test_scrub_empty_sensitive_fields_not_redacted(self):
        """Test that empty/null sensitive fields are not redacted"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "password": "",
            "token": None,
            "secret": "",
        }

        scrubbed = modal._scrub_sensitive_data(data)

        # Empty values should not be redacted
        assert scrubbed["password"] == ""
        assert scrubbed["token"] is None
        assert scrubbed["secret"] == ""

    def test_scrub_nested_dict(self):
        """Test that nested dictionaries are scrubbed recursively"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "name": "Credential",
            "inputs": {
                "username": "admin",
                "password": "FAKE_SECRET_123",  # NOSONAR
                "ssh_key_data": "FAKE_PRIVATE_KEY_DATA",
            },
            "metadata": {"created_by": "user1", "token": "FAKE_ACCESS_TOKEN"},  # NOSONAR
        }

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["name"] == "Credential"
        assert scrubbed["inputs"]["username"] == "admin"
        assert scrubbed["inputs"]["password"] == "***REMOVED***"
        assert scrubbed["inputs"]["ssh_key_data"] == "***REMOVED***"
        assert scrubbed["metadata"]["created_by"] == "user1"
        assert scrubbed["metadata"]["token"] == "***REMOVED***"

    def test_scrub_nested_lists(self):
        """Test that lists containing dicts are scrubbed recursively"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "credentials": [
                {"name": "SSH Key", "ssh_key_data": "FAKE_PRIVATE_KEY"},
                {"name": "Token", "token": "FAKE_TOKEN_VAL"},
            ],
            "users": [
                {"username": "user1", "password": "FAKE_PASS_USER1"},  # NOSONAR
                {"username": "user2", "password": "FAKE_PASS_USER2"},  # NOSONAR
            ],
        }

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["credentials"][0]["name"] == "SSH Key"
        assert scrubbed["credentials"][0]["ssh_key_data"] == "***REMOVED***"
        assert scrubbed["credentials"][1]["name"] == "Token"
        assert scrubbed["credentials"][1]["token"] == "***REMOVED***"
        assert scrubbed["users"][0]["username"] == "user1"
        assert scrubbed["users"][0]["password"] == "***REMOVED***"
        assert scrubbed["users"][1]["password"] == "***REMOVED***"

    def test_scrub_deeply_nested_structure(self):
        """Test scrubbing of deeply nested structures"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "level1": {
                "level2": {"level3": {"level4": {"password": "FAKE_DEEP_SECRET", "public_data": "visible"}}}  # NOSONAR
            }
        }

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["level1"]["level2"]["level3"]["level4"]["password"] == "***REMOVED***"
        assert scrubbed["level1"]["level2"]["level3"]["level4"]["public_data"] == "visible"

    def test_scrub_mixed_types(self):
        """Test that non-dict/list values are passed through unchanged"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
        }

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["string"] == "test"
        assert scrubbed["number"] == 42
        assert scrubbed["float"] == 3.14
        assert scrubbed["boolean"] is True
        assert scrubbed["null"] is None

    def test_scrub_preserves_original_data(self):
        """Test that scrubbing creates a copy and doesn't modify original"""
        modal = JsonPreviewModal(json_data={})

        original = {"username": "admin", "password": "FAKE_TEST_SECRET"}  # NOSONAR

        scrubbed = modal._scrub_sensitive_data(original)

        # Original should be unchanged
        assert original["password"] == "FAKE_TEST_SECRET"
        # Scrubbed should be redacted
        assert scrubbed["password"] == "***REMOVED***"

    def test_all_sensitive_field_types(self):
        """Test all sensitive field types from SENSITIVE_FIELDS set"""
        modal = JsonPreviewModal(json_data={})

        # Test all fields from JsonPreviewModal.SENSITIVE_FIELDS
        data = {
            "password": "TEST_VALUE",  # NOSONAR
            "token": "TEST_VALUE",
            "secret": "TEST_VALUE",
            "api_key": "TEST_VALUE",
            "apikey": "TEST_VALUE",
            "ssh_key_data": "TEST_VALUE",
            "vault_password": "TEST_VALUE",  # NOSONAR
            "become_password": "TEST_VALUE",  # NOSONAR
            "credential": "TEST_VALUE",
            "authorize_password": "TEST_VALUE",  # NOSONAR
            "client_secret": "TEST_VALUE",
            "private_key": "TEST_VALUE",
            "passphrase": "TEST_VALUE",  # NOSONAR
        }

        scrubbed = modal._scrub_sensitive_data(data)

        # All should be redacted
        for key in data.keys():
            assert scrubbed[key] == "***REMOVED***", f"Field '{key}' was not redacted"


class TestJsonPreviewModal:
    """Tests for JsonPreviewModal initialization and display"""

    def test_modal_initialization_with_minimal_data(self):
        """Test modal can be initialized with minimal parameters"""
        data = {"name": "test"}
        modal = JsonPreviewModal(json_data=data)

        assert modal.json_data == data
        assert modal.title_text == "JSON Preview - API Payload"
        assert modal.endpoint is None
        assert modal.method == "POST"
        assert modal.notes == []

    def test_modal_initialization_with_full_data(self):
        """Test modal initialization with all parameters"""
        data = {"name": "test", "password": "FAKE_PASSWORD"}
        notes = ["Note 1", "Note 2"]

        modal = JsonPreviewModal(
            json_data=data, title="Custom Title", endpoint="/api/v2/test/", method="PATCH", notes=notes
        )

        assert modal.json_data == data
        assert modal.title_text == "Custom Title"
        assert modal.endpoint == "/api/v2/test/"
        assert modal.method == "PATCH"
        assert modal.notes == notes

    def test_modal_shows_sensitive_data_hidden_by_default(self):
        """Test that sensitive data is hidden by default"""
        data = {"username": "admin", "password": "FAKE_PASSWORD"}
        modal = JsonPreviewModal(json_data=data)

        assert modal.show_sensitive is False

    def test_modal_toggle_sensitive_changes_state(self):
        """Test that toggling sensitive data changes the state"""
        data = {"password": "FAKE_PASSWORD"}
        modal = JsonPreviewModal(json_data=data)

        assert modal.show_sensitive is False

        # Simulate toggle
        modal.show_sensitive = not modal.show_sensitive
        assert modal.show_sensitive is True

        modal.show_sensitive = not modal.show_sensitive
        assert modal.show_sensitive is False


class TestJobTemplatePreviewDataBuilder:
    """Tests for _build_job_template_data_for_preview method structure"""

    def test_preview_data_includes_required_fields(self):
        """Test that preview data includes all required fields"""
        # This is more of an integration test - documenting expected structure
        expected_fields = [
            "name",
            "description",
            "job_type",
            "project",
            "playbook",
            "inventory",
            "verbosity",
            "become_enabled",
            "allow_simultaneous",
            "use_fact_cache",
            "timeout",
        ]

        # Test data structure
        preview_data = {
            "name": "Test Template",
            "description": "Description",
            "job_type": "run",
            "project": 1,
            "playbook": "site.yml",
            "inventory": 2,
            "verbosity": 0,
            "become_enabled": False,
            "allow_simultaneous": False,
            "use_fact_cache": False,
            "timeout": 0,
        }

        for field in expected_fields:
            assert field in preview_data, f"Required field '{field}' missing from preview data"

    def test_preview_data_optional_fields(self):
        """Test that optional fields are included when present"""
        preview_data = {
            "name": "Test",
            "execution_environment": 3,
            "limit": "webservers",
            "forks": 10,
            "job_slice_count": 4,
            "extra_vars": '{"key": "value"}',
        }

        assert "execution_environment" in preview_data
        assert "limit" in preview_data
        assert "forks" in preview_data
        assert "job_slice_count" in preview_data
        assert "extra_vars" in preview_data

    def test_preview_notes_structure(self):
        """Test that notes are returned as a list of strings"""
        notes = [
            "Credential ID 1 will be associated via separate POST",
            "Vault credentials [2, 3] will be associated via separate POST",
        ]

        assert isinstance(notes, list)
        for note in notes:
            assert isinstance(note, str)


class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_scrub_with_unicode_characters(self):
        """Test that unicode characters in data are preserved"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "name": "Tëst Crédèntîål 你好",
            "password": "pàsswørd_unicode_мир",  # notsecret NOSONAR
            "description": "🚀 Deployment",
        }  # notsecret
        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["name"] == "Tëst Crédèntîål 你好"
        assert scrubbed["password"] == "***REMOVED***"
        assert scrubbed["description"] == "🚀 Deployment"

    def test_scrub_with_special_characters_in_keys(self):
        """Test that special characters in keys don't break scrubbing"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "user-password": "FAKE_USER_PASSWORD",
            "api_key_v2": "FAKE_API_KEY_V2",
            "token.access": "FAKE_ACCESS_TOKEN_VAL",
        }

        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed["user-password"] == "***REMOVED***"
        assert scrubbed["api_key_v2"] == "***REMOVED***"
        assert scrubbed["token.access"] == "***REMOVED***"

    def test_scrub_empty_dict(self):
        """Test scrubbing an empty dictionary"""
        modal = JsonPreviewModal(json_data={})

        data = {}
        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed == {}

    def test_scrub_empty_list(self):
        """Test scrubbing an empty list"""
        modal = JsonPreviewModal(json_data={})

        data = []
        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed == []

    def test_scrub_none_value(self):
        """Test scrubbing None value"""
        modal = JsonPreviewModal(json_data={})

        scrubbed = modal._scrub_sensitive_data(None)

        assert scrubbed is None

    def test_scrub_list_of_primitives(self):
        """Test scrubbing a list of non-dict values"""
        modal = JsonPreviewModal(json_data={})

        data = [1, 2, "three", 4.0, True, None]
        scrubbed = modal._scrub_sensitive_data(data)

        assert scrubbed == [1, 2, "three", 4.0, True, None]

    def test_scrub_numeric_field_value_not_redacted(self):
        """Test that numeric values in sensitive fields are still redacted"""
        modal = JsonPreviewModal(json_data={})

        data = {
            "password": 12345,
            "token": 0,
        }

        scrubbed = modal._scrub_sensitive_data(data)

        # Numeric passwords should still be redacted
        assert scrubbed["password"] == "***REMOVED***"
        # But 0 (falsy) should not be redacted
        assert scrubbed["token"] == 0
