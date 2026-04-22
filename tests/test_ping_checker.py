"""
Tests for the AWX instance ping checker
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from awx_tui.ping_checker import _prune_api_log, check_instance_ping


class TestPruneApiLog:
    """Test API call log ring buffer pruning"""

    def test_none_log_noop(self):
        """Test None log is handled safely"""
        # Should not raise
        _prune_api_log(None)
        _prune_api_log(None, max_entries=5)

    def test_unlimited_noop(self):
        """Test max_entries=0 means unlimited (no pruning)"""
        log = list(range(10))
        _prune_api_log(log, max_entries=0)
        assert log == list(range(10))

    def test_log_shorter_than_max_unchanged(self):
        """Test log shorter than max_entries is not touched"""
        log = list(range(5))
        _prune_api_log(log, max_entries=10)
        assert log == list(range(5))

    def test_log_equal_to_max_unchanged(self):
        """Test log exactly at max_entries is not touched"""
        log = list(range(10))
        _prune_api_log(log, max_entries=10)
        assert log == list(range(10))

    def test_log_exceeds_max_trimmed_to_tail(self):
        """Test log longer than max is trimmed to most recent entries"""
        log = list(range(100))
        _prune_api_log(log, max_entries=10)
        assert log == list(range(90, 100))

    def test_prune_mutates_in_place(self):
        """Test the caller's list reference is mutated in place, not replaced"""
        log = list(range(20))
        original_id = id(log)
        _prune_api_log(log, max_entries=5)
        assert id(log) == original_id
        assert log == list(range(15, 20))


def _mock_response(status_code=200, json_data=None, text=""):
    """Build a MagicMock httpx.Response with the fields used by check_instance_ping"""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}
    response.text = text
    response.content = text.encode() if text else b""
    response.headers = {}
    response.request = MagicMock()
    response.request.headers = {}
    return response


def _mock_client(response=None, exc=None):
    """Build an AsyncMock httpx.AsyncClient whose .get() returns response or raises exc"""
    client = AsyncMock(spec=httpx.AsyncClient)
    if exc is not None:
        client.get = AsyncMock(side_effect=exc)
    else:
        client.get = AsyncMock(return_value=response)
    return client


class TestCheckInstancePingSuccess:
    """Test successful ping response handling"""

    @pytest.mark.asyncio
    async def test_online_status_and_version_parsed(self):
        """Test 200 response returns status=online and parses version field"""
        client = _mock_client(response=_mock_response(200, {"version": "24.6.1"}, text='{"version":"24.6.1"}'))

        result = await check_instance_ping(url="https://awx.example.com", instance_client=client)

        assert result["status"] == "online"
        assert result["version"] == "24.6.1"
        assert result["error"] is None
        assert result["response_time_ms"] >= 0
        assert result["response_time"].endswith(("ms", "s"))

    @pytest.mark.asyncio
    async def test_missing_version_field_defaults_to_unknown(self):
        """Test response without version key keeps the default 'Unknown'"""
        client = _mock_client(response=_mock_response(200, {}, text="{}"))

        result = await check_instance_ping(url="https://awx.example.com", instance_client=client)

        assert result["status"] == "online"
        assert result["version"] == "Unknown"

    @pytest.mark.asyncio
    async def test_instance_client_called_with_relative_path(self):
        """Test caller-provided client is called with relative path (assumes base_url is set)"""
        client = _mock_client(response=_mock_response(200, {"version": "24.6.1"}, text="{}"))

        await check_instance_ping(
            url="https://awx.example.com",
            api_base_path="/api/controller/v2",
            instance_client=client,
        )

        client.get.assert_awaited_once_with("/api/controller/v2/ping/")

    @pytest.mark.asyncio
    async def test_instance_client_not_closed(self):
        """Test caller-owned client is not closed by check_instance_ping"""
        client = _mock_client(response=_mock_response(200, {"version": "24.6.1"}, text="{}"))

        await check_instance_ping(url="https://awx.example.com", instance_client=client)

        client.aclose.assert_not_called()


class TestCheckInstancePingErrors:
    """Test error and failure path handling"""

    @pytest.mark.asyncio
    async def test_non_2xx_status_sets_error_with_http_code(self):
        """Test HTTP error response sets status=error with HTTP <code>"""
        client = _mock_client(response=_mock_response(500, text="Internal Server Error"))

        result = await check_instance_ping(url="https://awx.example.com", instance_client=client)

        assert result["status"] == "error"
        assert result["error"] == "HTTP 500"

    @pytest.mark.asyncio
    async def test_timeout_exception_sets_offline(self):
        """Test httpx.TimeoutException results in offline status with Timeout response_time"""
        client = _mock_client(exc=httpx.TimeoutException("timed out"))

        result = await check_instance_ping(url="https://awx.example.com", instance_client=client)

        assert result["status"] == "offline"
        assert result["response_time"] == "Timeout"
        assert result["error"] == "Request timeout"

    @pytest.mark.asyncio
    async def test_connect_error_sets_offline(self):
        """Test httpx.ConnectError results in offline status and surfaces connection error"""
        client = _mock_client(exc=httpx.ConnectError("Name or service not known"))

        result = await check_instance_ping(url="https://awx.example.com", instance_client=client)

        assert result["status"] == "offline"
        assert "Connection error" in result["error"]

    @pytest.mark.asyncio
    async def test_generic_exception_sets_error_status(self):
        """Test unexpected exceptions surface as status=error"""
        client = _mock_client(exc=RuntimeError("boom"))

        result = await check_instance_ping(url="https://awx.example.com", instance_client=client)

        assert result["status"] == "error"
        assert result["error"] == "boom"

    @pytest.mark.asyncio
    async def test_unparseable_json_captures_parse_error(self):
        """Test invalid JSON on 2xx response surfaces as a parse error"""
        response = _mock_response(200, text="not json")
        response.json.side_effect = ValueError("Expecting value")
        client = _mock_client(response=response)

        result = await check_instance_ping(url="https://awx.example.com", instance_client=client)

        # Status is still online (HTTP was fine) but error describes the parse failure
        assert result["status"] == "online"
        assert result["error"] is not None
        assert "Failed to parse response" in result["error"]


class TestCheckInstancePingLogging:
    """Test api_call_log population"""

    @pytest.mark.asyncio
    async def test_successful_call_appends_entry(self):
        """Test api_call_log gains a structured entry on successful ping"""
        client = _mock_client(response=_mock_response(200, {"version": "24.6.1"}, text='{"version":"24.6.1"}'))
        log: list = []

        await check_instance_ping(
            url="https://awx.example.com",
            api_call_log=log,
            instance_name="prod",
            instance_client=client,
        )

        assert len(log) == 1
        entry = log[0]
        assert entry["method"] == "GET"
        assert entry["instance_name"] == "prod"
        assert entry["status_code"] == 200
        assert entry["endpoint"] == "/api/v2/ping/"

    @pytest.mark.asyncio
    async def test_http_error_appends_entry(self):
        """Test api_call_log gains an entry on non-2xx response"""
        client = _mock_client(response=_mock_response(503, text="upstream down"))
        log: list = []

        await check_instance_ping(
            url="https://awx.example.com",
            api_call_log=log,
            instance_client=client,
        )

        assert len(log) == 1
        assert log[0]["status_code"] == 503
        assert log[0]["error"] == "HTTP 503"

    @pytest.mark.asyncio
    async def test_timeout_appends_entry_with_status_code_zero(self):
        """Test api_call_log gains an entry on timeout with status_code=0"""
        client = _mock_client(exc=httpx.TimeoutException("timed out"))
        log: list = []

        await check_instance_ping(
            url="https://awx.example.com",
            api_call_log=log,
            instance_client=client,
        )

        assert len(log) == 1
        assert log[0]["status_code"] == 0
        assert log[0]["error"] == "Request timeout"

    @pytest.mark.asyncio
    async def test_log_pruned_after_append(self):
        """Test api_call_log is pruned to max_log_entries after the append"""
        client = _mock_client(response=_mock_response(200, {"version": "24.6.1"}, text="{}"))
        log: list = list(range(5))

        await check_instance_ping(
            url="https://awx.example.com",
            api_call_log=log,
            max_log_entries=3,
            instance_client=client,
        )

        # Pre-existing entries are dropped; only the 3 most recent remain
        assert len(log) == 3


class TestCheckInstancePingThrowawayClient:
    """Test throwaway-client lifecycle when no instance_client is provided"""

    @pytest.mark.asyncio
    async def test_throwaway_client_created_and_closed(self, monkeypatch):
        """Test a throwaway AsyncClient is created, used with full URL, then closed"""
        created = AsyncMock(spec=httpx.AsyncClient)
        created.get = AsyncMock(return_value=_mock_response(200, {"version": "24.6.1"}, text="{}"))

        def fake_ctor(*args, **kwargs):
            return created

        monkeypatch.setattr("awx_tui.ping_checker.httpx.AsyncClient", fake_ctor)

        result = await check_instance_ping(url="https://awx.example.com")

        assert result["status"] == "online"
        created.get.assert_awaited_once_with("https://awx.example.com/api/v2/ping/")
        created.aclose.assert_awaited_once()
