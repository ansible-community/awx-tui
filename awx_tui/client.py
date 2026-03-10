"""
AWX TUI - AWX API Client

Handles HTTP communication with AWX REST API.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

from awx_tui.config import InstanceConfig

if TYPE_CHECKING:
    from awx_tui.config import AppConfig


@dataclass
class AWXVersion:
    """AWX version information from /api/v2/ping/"""

    version: str
    ha_enabled: bool
    active_node: str
    install_uuid: str
    instances: List[Dict[str, Any]]
    instance_groups: List[Dict[str, Any]]

    def __str__(self) -> str:
        ha_status = "HA Cluster" if self.ha_enabled else "Standalone"
        return f"AWX {self.version} ({ha_status})"


class AWXClientError(Exception):
    """Base exception for AWX client errors"""

    pass


class AWXAuthenticationError(AWXClientError):
    """Authentication failed"""

    pass


class AWXNotFoundError(AWXClientError):
    """Resource not found (404)"""

    pass


class AWXServerError(AWXClientError):
    """Server error (5xx)"""

    pass


class AWXTimeoutError(AWXClientError):
    """Request timeout"""

    pass


class AWXClient:
    """
    AWX API client

    - Async HTTP requests to AWX REST API
    - Token or password authentication
    - Request/response logging to debug console
    - Pagination handling
    - Error handling
    - Version detection
    """

    def __init__(
        self,
        instance_config: InstanceConfig,
        api_call_log: Optional[list] = None,
        timeout: float = 30.0,
        app_config: Optional["AppConfig"] = None,
        connection_event_log: Optional[list] = None,
    ):
        """
        Initialize AWX client

        Args:
            instance_config: Instance configuration
            api_call_log: Optional list to log API calls for debug console
            timeout: Request timeout in seconds (default: 30)
            app_config: Optional application configuration for preferences
            connection_event_log: Optional list to log connection pool events
        """
        self.config = instance_config
        self.api_call_log = api_call_log
        self.connection_event_log = connection_event_log
        self.timeout = timeout
        self.app_config = app_config
        self.session: Optional[httpx.AsyncClient] = None
        self.version_info: Optional[AWXVersion] = None

        # Pool limits: runtime overlay > instance config > global preferences > hardcoded
        # Runtime overlay is set by modifying these attributes directly
        global_max = 20
        global_keepalive = 10
        if app_config:
            global_max = app_config.preferences.get("pool_max_connections", 20)
            global_keepalive = app_config.preferences.get("pool_max_keepalive_connections", 10)

        self.max_connections = getattr(instance_config, "pool_max_connections", None) or global_max
        self.max_keepalive_connections = (
            getattr(instance_config, "pool_max_keepalive_connections", None) or global_keepalive
        )

        # Build authentication headers
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "python-httpx-awx-tui",
        }

        if self.config.auth_method == "token":
            self.headers["Authorization"] = f"Bearer {self.config.token}"
        # Password auth uses HTTP Basic Auth (handled in session creation)

    async def __aenter__(self):
        """Async context manager entry - creates session only if not already open"""
        if self.session is None or self.session.is_closed:
            auth = None
            if self.config.auth_method == "password":
                auth = httpx.BasicAuth(username=self.config.username, password=self.config.password or "")

            self.session = httpx.AsyncClient(
                base_url=self.config.url,
                headers=self.headers,
                auth=auth,
                verify=self.config.verify_ssl,
                timeout=self.timeout,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=self.max_connections,
                    max_keepalive_connections=self.max_keepalive_connections,
                ),
            )

            self._log_connection_event(
                "POOL_CREATED",
                f"max_connections={self.max_connections}, max_keepalive={self.max_keepalive_connections}",
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - no-op to keep session persistent"""
        # Session stays open for reuse across refresh cycles.
        # Use close() for explicit teardown.
        pass

    async def close(self):
        """Explicitly close the persistent httpx session"""
        if self.session and not self.session.is_closed:
            self._log_connection_event("POOL_CLOSED", "Session explicitly closed")
            await self.session.aclose()
        self.session = None

    def _get_pool_snapshot(self) -> Optional[Dict[str, Any]]:
        """Capture current connection pool state"""
        if not self.session or self.session.is_closed:
            return None
        try:
            pool = self.session._transport._pool
            connections = pool.connections
            idle = sum(1 for c in connections if c.is_idle())
            active = len(connections) - idle
            return {
                "total": len(connections),
                "idle": idle,
                "active": active,
                "max_connections": pool._max_connections,
                "max_keepalive": pool._max_keepalive_connections,
            }
        except (Exception):
            return None

    def _log_connection_event(self, event: str, details: str) -> None:
        """Log a connection pool event to the connection event log"""
        if self.connection_event_log is None:
            return

        instance_name = self.config.name if (hasattr(self.config, "name") and self.config.name) else "unknown"

        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "instance": instance_name,
            "event": event,
            "details": details,
            "pool_snapshot": self._get_pool_snapshot(),
        }

        self.connection_event_log.append(entry)

        # Ring buffer - cap at 1000 entries
        max_entries = 1000
        if self.app_config:
            max_entries = self.app_config.preferences.get("network_queue_max_entries", 1000)
        if max_entries > 0 and len(self.connection_event_log) > max_entries:
            self.connection_event_log[:] = self.connection_event_log[-max_entries:]

    def _mask_sensitive_data(self, data: str) -> str:
        """
        Mask sensitive data in logs

        Masks tokens, passwords, and other credentials

        Args:
            data: String to mask

        Returns:
            Masked string
        """
        # Mask Bearer tokens
        data = re.sub(r"(Bearer\s+)([A-Za-z0-9_\-\.]+)", r"\1***MASKED***", data)

        # Mask Basic Auth
        data = re.sub(r"(Basic\s+)([A-Za-z0-9+/=]+)", r"\1***MASKED***", data)

        # Mask password fields in JSON
        data = re.sub(r'("password"\s*:\s*)"[^"]*"', r'\1"***MASKED***"', data)

        # Mask token fields in JSON
        data = re.sub(r'("token"\s*:\s*)"[^"]*"', r'\1"***MASKED***"', data)

        # Mask SSH key data in JSON (credential fields)
        data = re.sub(r'("ssh_key_data"\s*:\s*)"[^"]*"', r'\1"***MASKED***"', data)

        # Mask SSH key passphrase in JSON
        data = re.sub(r'("ssh_key_unlock"\s*:\s*)"[^"]*"', r'\1"***MASKED***"', data)

        # Mask privilege escalation password in JSON
        data = re.sub(r'("become_password"\s*:\s*)"[^"]*"', r'\1"***MASKED***"', data)

        # Mask vault password in JSON
        data = re.sub(r'("vault_password"\s*:\s*)"[^"]*"', r'\1"***MASKED***"', data)

        # Mask Kubernetes bearer token in JSON
        data = re.sub(r'("bearer_token"\s*:\s*)"[^"]*"', r'\1"***MASKED***"', data)

        return data

    def _log_api_call(
        self,
        method: str,
        endpoint: str,
        full_url: str,
        status_code: int = 0,
        duration_ms: int = 0,
        request_headers: Optional[Dict] = None,
        request_body: Optional[Dict] = None,
        response_headers: Optional[Dict] = None,
        response_text: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log API call to debug console"""
        if self.api_call_log is None:
            return

        from datetime import datetime

        # Get instance name from config, fallback to 'unknown' if not set
        instance_name = self.config.name if (hasattr(self.config, "name") and self.config.name) else "unknown"

        # Build API call entry with milliseconds in timestamp
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],  # Include milliseconds
            "method": method,
            "instance": self.config.url,
            "instance_name": instance_name,  # Store instance name for switching
            "endpoint": endpoint,
            "url": full_url,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "size_bytes": len(response_text) if response_text else 0,
        }

        # Add headers if available (mask sensitive data)
        if request_headers:
            masked_request_headers = dict(request_headers)
            # Mask Authorization header
            if "authorization" in masked_request_headers:
                masked_request_headers["authorization"] = "***MASKED***"
            if "Authorization" in masked_request_headers:
                masked_request_headers["Authorization"] = "***MASKED***"
            entry["request_headers"] = masked_request_headers

        # Add request body if available (for POST/PUT/PATCH)
        if request_body:
            import json as json_module

            # Mask sensitive data in request body
            masked_body = self._mask_sensitive_data(json_module.dumps(request_body))
            entry["request_body"] = masked_body

        if response_headers:
            entry["response_headers"] = dict(response_headers)

        # Add response content if available
        if response_text:
            # Mask sensitive data in response
            masked_text = self._mask_sensitive_data(response_text)
            entry["content_preview"] = masked_text[:500]
            entry["response_content_full"] = masked_text

        # Add error if present
        if error:
            entry["error"] = error

        self.api_call_log.append(entry)

        # Auto-prune old entries if max size exceeded (ring buffer behavior)
        # Configurable via debug_console_max_entries (default: 1000, 0 = unlimited)
        max_entries = 1000  # Default
        if self.app_config:
            max_entries = self.app_config.preferences.get("debug_console_max_entries", 1000)

        if max_entries > 0 and len(self.api_call_log) > max_entries:
            # Keep only the most recent max_entries
            self.api_call_log[:] = self.api_call_log[-max_entries:]

    async def _request(
        self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Internal request handler

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
            endpoint: API endpoint (e.g., '/api/v2/jobs/' or just '/jobs/')
            params: Query parameters
            data: Request body (for POST/PUT/PATCH)

        Returns:
            JSON response as dict

        Raises:
            AWXAuthenticationError: 401 unauthorized
            AWXNotFoundError: 404 not found
            AWXServerError: 5xx server error
            AWXTimeoutError: Request timeout
            AWXClientError: Other errors
        """
        if not self.session:
            raise AWXClientError("Client not initialized. Use 'async with' context manager.")

        # Normalize endpoint to use configured api_base_path
        # Replace hardcoded /api/v2 or /api/controller/v2 with configured path
        if endpoint.startswith("/api/v2/"):
            endpoint = endpoint.replace("/api/v2/", f"{self.config.api_base_path}/", 1)
        elif endpoint.startswith("/api/controller/v2/"):
            endpoint = endpoint.replace("/api/controller/v2/", f"{self.config.api_base_path}/", 1)
        # If endpoint doesn't have an API base path, prepend configured one
        elif not endpoint.startswith(self.config.api_base_path):
            # Ensure there's a slash between base path and endpoint
            if not endpoint.startswith("/"):
                endpoint = f"/{endpoint}"
            endpoint = f"{self.config.api_base_path}{endpoint}"

        try:
            # Make request
            start_time = datetime.now()

            if method == "GET":
                response = await self.session.get(endpoint, params=params)
            elif method == "POST":
                response = await self.session.post(endpoint, json=data)
            elif method == "PUT":
                response = await self.session.put(endpoint, json=data)
            elif method == "PATCH":
                response = await self.session.patch(endpoint, json=data)
            elif method == "DELETE":
                response = await self.session.delete(endpoint)
            elif method == "HEAD":
                response = await self.session.head(endpoint, params=params)
            elif method == "OPTIONS":
                response = await self.session.options(endpoint, params=params)
            else:
                raise AWXClientError(f"Unsupported HTTP method: {method}")

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Build full URL for logging
            full_url = str(response.url)

            # Extract error message from response if status code indicates error
            error_msg = None
            if response.status_code >= 400:
                # Try to parse JSON error response from AWX
                try:
                    error_data = response.json()
                    # AWX typically returns errors in 'detail' field
                    if isinstance(error_data, dict):
                        error_msg = error_data.get("detail") or error_data.get("error") or str(error_data)
                    else:
                        error_msg = str(error_data)
                except Exception:
                    # If JSON parsing fails, use response text or generic message
                    error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"

                # Prefix with status code for clarity
                error_msg = f"HTTP {response.status_code}: {error_msg}"

            # Log API call (successful or failed)
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                full_url=full_url,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_headers=dict(response.request.headers) if response.request else None,
                request_body=data if data else None,
                response_headers=dict(response.headers),
                response_text=response.text,
                error=error_msg,
            )

            # Handle HTTP errors
            if response.status_code == 401:
                raise AWXAuthenticationError(
                    f"Authentication failed for {self.config.url}. " f"Check your credentials."
                )

            elif response.status_code == 403:
                raise AWXAuthenticationError(f"Access forbidden. User '{self.config.username}' may lack permissions.")

            elif response.status_code == 404:
                raise AWXNotFoundError(f"Resource not found: {endpoint}")

            elif 500 <= response.status_code < 600:
                raise AWXServerError(f"AWX server error ({response.status_code}): {response.text}")

            elif response.status_code >= 400:
                raise AWXClientError(f"HTTP {response.status_code}: {response.text}")

            # Parse JSON response
            try:
                return response.json()
            except Exception as e:
                # Some endpoints may not return JSON
                if response.status_code == 204:
                    # 204 No Content is valid for any method (DELETE, POST, etc.)
                    return {}
                elif method == "HEAD":
                    # HEAD returns no body, just headers
                    return {"message": "HEAD request successful (no body)", "headers": dict(response.headers)}
                elif method == "OPTIONS":
                    # OPTIONS returns allowed methods in Allow header
                    allow_header = response.headers.get("Allow", "Not specified")
                    return {
                        "message": "OPTIONS request successful",
                        "allowed_methods": allow_header,
                        "headers": dict(response.headers),
                    }
                raise AWXClientError(f"Invalid JSON response: {e}")

        except httpx.TimeoutException as e:
            # Log timeout
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                full_url=f"{self.config.url}{endpoint}",
                status_code=0,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=f"Timeout ({self.timeout}s)",
            )
            raise AWXTimeoutError(f"Request to {self.config.url} timed out after {self.timeout}s") from e

        except httpx.PoolTimeout as e:
            # Log connection pool exhaustion
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                full_url=f"{self.config.url}{endpoint}",
                status_code=0,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=f"Connection pool exhausted: {str(e)}",
            )
            self._log_connection_event("POOL_EXHAUSTED", f"PoolTimeout on {method} {endpoint}: {e}")
            raise AWXClientError(
                f"Connection pool exhausted for {self.config.url}. "
                f"Too many concurrent requests. Try again in a moment."
            ) from e

        except httpx.ConnectError as e:
            # Log connection error
            error_msg = str(e)
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Detect specific connection issues
            if "Connection pool is full" in error_msg or "pool limit" in error_msg.lower():
                self._log_api_call(
                    method=method,
                    endpoint=endpoint,
                    full_url=f"{self.config.url}{endpoint}",
                    status_code=0,
                    duration_ms=duration_ms,
                    error=f"Connection pool full: {error_msg}",
                )
                self._log_connection_event("POOL_EXHAUSTED", f"ConnectError on {method} {endpoint}: {error_msg}")
                raise AWXClientError(
                    f"Too many concurrent connections to {self.config.url}. "
                    f"Connection pool exhausted. Wait for active requests to complete."
                ) from e
            else:
                self._log_api_call(
                    method=method,
                    endpoint=endpoint,
                    full_url=f"{self.config.url}{endpoint}",
                    status_code=0,
                    duration_ms=duration_ms,
                    error=f"Connection failed: {error_msg}",
                )
                raise AWXClientError(
                    f"Failed to connect to {self.config.url}. " f"Check URL and network connectivity. ({error_msg})"
                ) from e

        except httpx.NetworkError as e:
            # Log network errors (DNS, routing, etc.)
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                full_url=f"{self.config.url}{endpoint}",
                status_code=0,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=f"Network error: {str(e)}",
            )
            raise AWXClientError(f"Network error connecting to {self.config.url}: {str(e)}") from e

        except httpx.RemoteProtocolError as e:
            # Log protocol errors (HTTP/2, TLS, etc.)
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                full_url=f"{self.config.url}{endpoint}",
                status_code=0,
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=f"Protocol error: {str(e)}",
            )
            raise AWXClientError(f"HTTP protocol error with {self.config.url}: {str(e)}") from e

        except (AWXClientError, AWXAuthenticationError, AWXNotFoundError, AWXServerError, AWXTimeoutError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            # Log unexpected error with full exception type
            self._log_api_call(
                method=method,
                endpoint=endpoint,
                full_url=f"{self.config.url}{endpoint}",
                status_code=0,
                duration_ms=0,
                error=f"Unexpected error ({type(e).__name__}): {e}",
            )
            raise AWXClientError(f"Unexpected error ({type(e).__name__}): {e}") from e

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        GET request to AWX API

        Args:
            endpoint: API endpoint (e.g., /api/v2/jobs/)
            params: Query parameters

        Returns:
            JSON response as dict
        """
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        POST request to AWX API

        Args:
            endpoint: API endpoint
            data: Request body

        Returns:
            JSON response as dict
        """
        return await self._request("POST", endpoint, data=data)

    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        PUT request to AWX API

        Args:
            endpoint: API endpoint
            data: Request body

        Returns:
            JSON response as dict
        """
        return await self._request("PUT", endpoint, data=data)

    async def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        PATCH request to AWX API

        Args:
            endpoint: API endpoint
            data: Request body

        Returns:
            JSON response as dict
        """
        return await self._request("PATCH", endpoint, data=data)

    async def delete(self, endpoint: str) -> None:
        """
        DELETE request to AWX API

        Args:
            endpoint: API endpoint
        """
        await self._request("DELETE", endpoint)

    async def head(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        HEAD request to AWX API

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Dict with headers (no response body)
        """
        return await self._request("HEAD", endpoint, params=params)

    async def options(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        OPTIONS request to AWX API

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Dict with allowed methods and headers
        """
        return await self._request("OPTIONS", endpoint, params=params)

    async def get_all_pages(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_pages: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all pages from paginated endpoint

        Args:
            endpoint: API endpoint
            params: Query parameters
            max_pages: Maximum pages to fetch (safety limit)

        Returns:
            List of all results from all pages
        """
        all_results = []
        page = 1

        while page <= max_pages:
            # Add page to params
            page_params = params.copy() if params else {}
            page_params["page"] = page

            # Fetch page
            response = await self.get(endpoint, params=page_params)

            # Add results
            results = response.get("results", [])
            all_results.extend(results)

            # Check if there's a next page
            if not response.get("next"):
                break

            page += 1

        return all_results

    async def ping(self) -> AWXVersion:
        """
        Ping AWX instance and get version info

        Returns:
            AWXVersion with instance details

        Raises:
            AWXClientError: If ping fails
        """
        try:
            response = await self.get("/api/v2/ping/")

            version_info = AWXVersion(
                version=response.get("version", "unknown"),
                ha_enabled=response.get("ha", False),
                active_node=response.get("active_node", ""),
                install_uuid=response.get("install_uuid", ""),
                instances=response.get("instances", []),
                instance_groups=response.get("instance_groups", []),
            )

            self.version_info = version_info
            return version_info

        except Exception as e:
            raise AWXClientError(f"Failed to ping AWX instance: {e}") from e

    async def test_connection(self) -> bool:
        """
        Test connection to AWX instance

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self.ping()
            return True
        except Exception:
            return False
