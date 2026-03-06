"""
Tests for AWX API client
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from awx_tui.client import (
    AWXAuthenticationError,
    AWXClient,
    AWXClientError,
    AWXNotFoundError,
    AWXServerError,
    AWXTimeoutError,
    AWXVersion,
)
from awx_tui.config import InstanceConfig


@pytest.fixture
def token_instance():
    """Instance config with token auth"""
    return InstanceConfig(
        name="test-awx", url="https://awx.example.com", auth_method="token", username="admin", token="test-token-123"
    )


@pytest.fixture
def password_instance():
    """Instance config with password auth"""
    return InstanceConfig(
        name="test-awx",
        url="https://awx.example.com",
        auth_method="password",
        username="admin",
        password="test-password",
    )


class TestAWXVersion:
    """Test AWXVersion dataclass"""

    def test_version_string_ha(self):
        """Test version string for HA cluster"""
        version = AWXVersion(
            version="23.1.0",
            ha_enabled=True,
            active_node="controller-001",
            install_uuid="test-uuid",
            instances=[],
            instance_groups=[],
        )

        assert str(version) == "AWX 23.1.0 (HA Cluster)"

    def test_version_string_standalone(self):
        """Test version string for standalone"""
        version = AWXVersion(
            version="23.1.0",
            ha_enabled=False,
            active_node="controller-001",
            install_uuid="test-uuid",
            instances=[],
            instance_groups=[],
        )

        assert str(version) == "AWX 23.1.0 (Standalone)"


class TestAWXClientInit:
    """Test AWXClient initialization"""

    def test_token_auth_headers(self, token_instance):
        """Test headers with token auth"""
        client = AWXClient(token_instance)

        assert client.headers["Authorization"] == "Bearer test-token-123"
        assert client.headers["Content-Type"] == "application/json"
        assert client.headers["Accept"] == "application/json"

    def test_password_auth_no_bearer(self, password_instance):
        """Test password auth doesn't set Bearer header"""
        client = AWXClient(password_instance)

        assert "Authorization" not in client.headers
        assert client.headers["Content-Type"] == "application/json"

    def test_custom_timeout(self, token_instance):
        """Test custom timeout"""
        client = AWXClient(token_instance, timeout=60.0)

        assert client.timeout == 60.0

    def test_default_timeout(self, token_instance):
        """Test default timeout"""
        client = AWXClient(token_instance)

        assert client.timeout == 30.0


class TestAWXClientContext:
    """Test async context manager"""

    @pytest.mark.asyncio
    async def test_context_manager_creates_session(self, token_instance):
        """Test session created on entry"""
        async with AWXClient(token_instance) as client:
            assert client.session is not None
            assert isinstance(client.session, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_session_persists_across_context_entries(self, token_instance):
        """Test session is NOT recreated on repeated context entry (persistent session)"""
        client = AWXClient(token_instance)

        async with client:
            session1 = client.session
            assert session1 is not None

        # Enter context again - should reuse same session
        async with client:
            session2 = client.session
            assert session2 is session1

    @pytest.mark.asyncio
    async def test_session_not_closed_on_context_exit(self, token_instance):
        """Test session remains open after exiting context manager"""
        client = AWXClient(token_instance)

        async with client:
            session = client.session
            assert session is not None

        # Session should still be open after context exit
        assert client.session is not None
        assert not client.session.is_closed

    @pytest.mark.asyncio
    async def test_explicit_close_closes_session(self, token_instance):
        """Test explicit close() tears down the session"""
        client = AWXClient(token_instance)

        async with client:
            assert client.session is not None

        await client.close()

        # Session should be None after close
        assert client.session is None

    @pytest.mark.asyncio
    async def test_reopen_after_close(self, token_instance):
        """Test entering context after close() creates a new session"""
        client = AWXClient(token_instance)

        async with client:
            session1 = client.session

        await client.close()
        assert client.session is None

        # Re-entering context should create a new session
        async with client:
            session2 = client.session
            assert session2 is not None
            assert session2 is not session1

    @pytest.mark.asyncio
    async def test_connection_pool_limits_configured(self, token_instance):
        """Test httpx client has explicit connection pool limits"""
        client = AWXClient(token_instance)

        async with client:
            pool = client.session._transport._pool
            assert pool._max_connections == 20
            assert pool._max_keepalive_connections == 10

        await client.close()

    @pytest.mark.asyncio
    async def test_password_auth_uses_basic_auth(self, password_instance):
        """Test password auth creates BasicAuth"""
        async with AWXClient(password_instance) as client:
            # Session should have auth configured
            assert client.session.auth is not None
        await client.close()


class TestSensitiveDataMasking:
    """Test sensitive data masking"""

    def test_mask_bearer_token(self, token_instance):
        """Test Bearer token masking"""
        client = AWXClient(token_instance)

        masked = client._mask_sensitive_data("Authorization: Bearer abc123xyz")
        assert "abc123xyz" not in masked
        assert "***MASKED***" in masked

    def test_mask_basic_auth(self, token_instance):
        """Test Basic Auth masking"""
        client = AWXClient(token_instance)

        masked = client._mask_sensitive_data("Authorization: Basic dXNlcjpwYXNz")
        assert "dXNlcjpwYXNz" not in masked
        assert "***MASKED***" in masked

    def test_mask_password_field(self, token_instance):
        """Test password field masking in JSON"""
        client = AWXClient(token_instance)

        masked = client._mask_sensitive_data('{"password": "secret123"}')
        assert "secret123" not in masked
        assert "***MASKED***" in masked

    def test_mask_token_field(self, token_instance):
        """Test token field masking in JSON"""
        client = AWXClient(token_instance)

        masked = client._mask_sensitive_data('{"token": "secret-token"}')
        assert "secret-token" not in masked
        assert "***MASKED***" in masked


class TestAWXClientRequests:
    """Test HTTP requests"""

    @pytest.mark.asyncio
    async def test_request_without_context_raises(self, token_instance):
        """Test request without context manager raises error"""
        client = AWXClient(token_instance)

        with pytest.raises(AWXClientError, match="not initialized"):
            await client.get("/api/v2/ping/")

    @pytest.mark.asyncio
    async def test_get_success(self, token_instance):
        """Test successful GET request"""
        async with AWXClient(token_instance) as client:
            # Mock the session.get method
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"version": "23.1.0"}
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            result = await client.get("/api/v2/ping/")

            assert result == {"version": "23.1.0"}
            client.session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_params(self, token_instance):
        """Test GET request with query parameters"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            params = {"page": 1, "page_size": 25}
            await client.get("/api/v2/jobs/", params=params)

            client.session.get.assert_called_once_with("/api/v2/jobs/", params=params)

    @pytest.mark.asyncio
    async def test_post_request(self, token_instance):
        """Test POST request"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": 123}
            mock_response.headers = {}

            client.session.post = AsyncMock(return_value=mock_response)

            data = {"name": "test-job"}
            result = await client.post("/api/v2/jobs/", data=data)

            assert result == {"id": 123}
            client.session.post.assert_called_once_with("/api/v2/jobs/", json=data)

    @pytest.mark.asyncio
    async def test_delete_request(self, token_instance):
        """Test DELETE request"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.headers = {}

            client.session.delete = AsyncMock(return_value=mock_response)

            await client.delete("/api/v2/jobs/123/")

            client.session.delete.assert_called_once()


class TestAWXClientErrors:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self, token_instance):
        """Test 401 raises AWXAuthenticationError"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            with pytest.raises(AWXAuthenticationError, match="Authentication failed"):
                await client.get("/api/v2/ping/")

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self, token_instance):
        """Test 403 raises AWXAuthenticationError"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            with pytest.raises(AWXAuthenticationError, match="forbidden"):
                await client.get("/api/v2/jobs/")

    @pytest.mark.asyncio
    async def test_404_raises_not_found(self, token_instance):
        """Test 404 raises AWXNotFoundError"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            with pytest.raises(AWXNotFoundError, match="not found"):
                await client.get("/api/v2/jobs/999/")

    @pytest.mark.asyncio
    async def test_500_raises_server_error(self, token_instance):
        """Test 500 raises AWXServerError"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            with pytest.raises(AWXServerError, match="server error"):
                await client.get("/api/v2/jobs/")

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self, token_instance):
        """Test timeout raises AWXTimeoutError"""
        async with AWXClient(token_instance, timeout=1.0) as client:
            client.session.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            with pytest.raises(AWXTimeoutError, match="timed out"):
                await client.get("/api/v2/ping/")

    @pytest.mark.asyncio
    async def test_connect_error_raises_client_error(self, token_instance):
        """Test connection error raises AWXClientError"""
        async with AWXClient(token_instance) as client:
            client.session.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(AWXClientError, match="Failed to connect"):
                await client.get("/api/v2/ping/")


class TestAWXClientPagination:
    """Test pagination handling"""

    @pytest.mark.asyncio
    async def test_get_all_pages_single_page(self, token_instance):
        """Test get_all_pages with single page"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "count": 5,
                "next": None,
                "previous": None,
                "results": [{"id": i} for i in range(5)],
            }
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            results = await client.get_all_pages("/api/v2/jobs/")

            assert len(results) == 5
            assert results[0]["id"] == 0
            assert results[4]["id"] == 4

    @pytest.mark.asyncio
    async def test_get_all_pages_multiple_pages(self, token_instance):
        """Test get_all_pages with multiple pages"""
        async with AWXClient(token_instance) as client:
            # Mock responses for 3 pages
            responses = [
                {
                    "count": 75,
                    "next": "/api/v2/jobs/?page=2",
                    "previous": None,
                    "results": [{"id": i} for i in range(25)],
                },
                {
                    "count": 75,
                    "next": "/api/v2/jobs/?page=3",
                    "previous": "/api/v2/jobs/?page=1",
                    "results": [{"id": i} for i in range(25, 50)],
                },
                {
                    "count": 75,
                    "next": None,
                    "previous": "/api/v2/jobs/?page=2",
                    "results": [{"id": i} for i in range(50, 75)],
                },
            ]

            call_count = 0

            async def mock_get(endpoint, params=None):
                nonlocal call_count
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = responses[call_count]
                mock_response.headers = {}
                call_count += 1
                return mock_response

            client.session.get = mock_get

            results = await client.get_all_pages("/api/v2/jobs/")

            assert len(results) == 75
            assert results[0]["id"] == 0
            assert results[74]["id"] == 74


class TestAWXClientPing:
    """Test ping and version detection"""

    @pytest.mark.asyncio
    async def test_ping_success(self, token_instance):
        """Test successful ping"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "version": "23.1.0",
                "ha": True,
                "active_node": "controller-001",
                "install_uuid": "test-uuid",
                "instances": [{"node": "controller-001", "capacity": 136}],
                "instance_groups": [{"name": "default", "capacity": 136}],
            }
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            version = await client.ping()

            assert isinstance(version, AWXVersion)
            assert version.version == "23.1.0"
            assert version.ha_enabled is True
            assert version.active_node == "controller-001"
            assert len(version.instances) == 1
            assert len(version.instance_groups) == 1

            # Version info should be cached
            assert client.version_info == version

    @pytest.mark.asyncio
    async def test_test_connection_success(self, token_instance):
        """Test test_connection returns True on success"""
        async with AWXClient(token_instance) as client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "version": "23.1.0",
                "ha": False,
                "active_node": "test",
                "install_uuid": "test",
            }
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            result = await client.test_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, token_instance):
        """Test test_connection returns False on failure"""
        async with AWXClient(token_instance) as client:
            client.session.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            result = await client.test_connection()

            assert result is False


class TestDebugLogging:
    """Test debug logging functionality"""

    @pytest.mark.asyncio
    async def test_logging_with_logger(self, token_instance):
        """Test requests are logged when api_call_log is provided"""
        mock_log = []

        async with AWXClient(token_instance, api_call_log=mock_log) as client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"version": "23.1.0"}
            mock_response.text = '{"version": "23.1.0"}'
            mock_response.headers = {"X-API-Node": "controller-001"}

            client.session.get = AsyncMock(return_value=mock_response)

            await client.get("/api/v2/ping/")

            # Should have logged exactly 1 entry for the request
            assert len(mock_log) == 1

    @pytest.mark.asyncio
    async def test_no_logging_without_logger(self, token_instance):
        """Test no logging when api_call_log is None"""
        # Should not raise any errors
        async with AWXClient(token_instance, api_call_log=None) as client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"version": "23.1.0"}
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            await client.get("/api/v2/ping/")

            # No errors = success

    @pytest.mark.asyncio
    async def test_sensitive_data_masked_in_logs(self, token_instance):
        """Test sensitive data is masked in logs"""
        mock_log = []

        async with AWXClient(token_instance, api_call_log=mock_log) as client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.text = "{}"
            mock_response.headers = {}

            client.session.get = AsyncMock(return_value=mock_response)

            await client.get("/api/v2/ping/")

            # Check that token is not in logs
            for entry in mock_log:
                log_str = str(entry)
                assert "test-token-123" not in log_str
