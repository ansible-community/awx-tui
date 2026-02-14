"""
AWX TUI - Advanced API Mode Screen

Full-screen API testing tool for AWX developers.
Pre-populates from debug console and allows direct API interaction.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Select, Static, TabbedContent, TabPane, TextArea


class AdvancedAPIModeScreen(Screen):
    """
    Advanced API Mode - Full-screen API testing tool

    Features:
    - Method selection (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
    - Endpoint input
    - Request body editor (editable JSON)
    - Response viewer (read-only JSON)
    - Request/response headers in separate tab
    - JSON validation (blank/empty is valid)
    - Pre-population from debug console
    - Clear response / Clear all
    """

    CSS_PATH = "advanced_api_mode.tcss"

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("ctrl+enter", "send_request", "Send", show=True),
        Binding("ctrl+l", "clear_all", "Clear", show=True),
        Binding("f", "format_json", "Format JSON", show=False),
    ]

    def __init__(self, prepopulate_data: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize Advanced API Mode screen

        Args:
            prepopulate_data: Optional dict with keys:
                - method: HTTP method (GET, POST, etc.)
                - endpoint: API endpoint
                - request_body: Request body JSON string
                - request_headers: Dict of request headers
                - response_body: Previous response JSON string (read-only)
                - response_headers: Dict of response headers (read-only)
                - instance_name: Temporary instance override (from debug console)
        """
        super().__init__(**kwargs)
        self.prepopulate_data = prepopulate_data or {}
        self._last_response_status = None

        # Temporary instance override (used instead of global active instance)
        # This allows replaying API calls from debug console without switching the global instance
        self.instance_override = self.prepopulate_data.get("instance_name")

    def compose(self) -> ComposeResult:
        """Create Advanced API Mode layout"""
        yield Header()

        # Top controls: Instance info + Method + Endpoint + Actions
        with Container(id="controls-container"):
            # Instance info
            yield Static("Instance: Loading...", id="instance-info")

            # Request line: Method + Endpoint
            with Horizontal(id="request-line"):
                yield Select(
                    options=[
                        ("GET", "GET"),
                        ("POST", "POST"),
                        ("PUT", "PUT"),
                        ("PATCH", "PATCH"),
                        ("DELETE", "DELETE"),
                        ("HEAD", "HEAD"),
                        ("OPTIONS", "OPTIONS"),
                    ],
                    value="GET",
                    id="method-select",
                )
                yield Input(placeholder="Endpoint: /api/v2/jobs/", id="endpoint-input")

            # Action buttons
            with Horizontal(id="action-line"):
                yield Button("Send", variant="primary", id="send-button")
                yield Button("Clear Response", variant="default", id="clear-response-button")
                yield Button("Clear All", variant="warning", id="clear-all-button")

        # Tabbed content: Request/Response (default) + Headers
        with TabbedContent(id="content-tabs"):
            # Tab 1: Request/Response (default, split pane)
            with TabPane("Request/Response", id="tab-request-response"):
                with Horizontal(id="request-response-pane"):
                    # Left: Request body (editable)
                    with Vertical(id="request-body-container"):
                        yield Static("Request Body (editable, copyable)", classes="pane-header")
                        yield TextArea(id="request-body", language="json")

                    # Right: Response (read-only)
                    with Vertical(id="response-container"):
                        yield Static("Response (read-only, copyable)", id="response-header", classes="pane-header")
                        yield TextArea(id="response-body", language="json", read_only=True)

            # Tab 2: Headers (split pane)
            with TabPane("Headers", id="tab-headers"):
                with Horizontal(id="headers-pane"):
                    # Left: Request headers (read-only for MVP)
                    with Vertical(id="request-headers-container"):
                        yield Static("Request Headers (read-only, copyable)", classes="pane-header")
                        yield TextArea(id="request-headers", language="json", read_only=True)

                    # Right: Response headers (read-only)
                    with Vertical(id="response-headers-container"):
                        yield Static("Response Headers (read-only, copyable)", classes="pane-header")
                        yield TextArea(id="response-headers", language="json", read_only=True)

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize screen and apply pre-population if provided"""
        # Update instance info
        self._update_instance_info()

        # Apply pre-population if provided
        if self.prepopulate_data:
            self._apply_prepopulation()

        # Focus endpoint input by default
        self.query_one("#endpoint-input", Input).focus()

    def _update_instance_info(self) -> None:
        """Update instance information display"""
        instance_manager = self.app.instance_manager

        # Get app name
        app_name = self.app.current_app_name if hasattr(self.app, "current_app_name") else "AWX TUI"

        # Use instance override if set (from debug console), otherwise use current instance
        # Handle both None and empty string as "not set"
        instance_name = (
            self.instance_override
            if (self.instance_override is not None and self.instance_override != "")
            else instance_manager.current_instance
        )

        if instance_name:
            # Get instance config for base URL and status
            config = self.app.app_config.instances.get(instance_name)

            if config:
                base_url = config.url
                api_base_path = config.api_base_path
                # Add trailing slash to show where endpoints continue
                full_api_url = f"{base_url}{api_base_path}/"
                instance_info = f"{app_name} - Advanced API Mode @ {instance_name} - {full_api_url}"

                # Add status emoji if available
                if hasattr(config, "last_status"):
                    status = config.last_status or "unknown"
                    status_emoji_map = {
                        "online": "[green]✓[/green]",
                        "slow": "⚠",
                        "very_slow": "🐌",
                        "offline": "✗",
                        "error": "[red]✗[/red]",
                        "unknown": "❓",
                        "ready": "[green]✓[/green]",
                    }
                    status_emoji = status_emoji_map.get(status, "❓")
                    instance_info += f" {status_emoji}"
            else:
                instance_info = f"{app_name} - Advanced API Mode @ {instance_name} (no config found)"
        else:
            instance_info = f"{app_name} - Advanced API Mode @ None selected"

        self.query_one("#instance-info", Static).update(instance_info)

    def _apply_prepopulation(self) -> None:
        """Apply pre-population data to form fields"""
        data = self.prepopulate_data

        # Method
        if "method" in data:
            method_select = self.query_one("#method-select", Select)
            method_select.value = data["method"].upper()

        # Endpoint
        if "endpoint" in data:
            endpoint_input = self.query_one("#endpoint-input", Input)
            endpoint_input.value = data["endpoint"]

        # Request body
        if "request_body" in data:
            request_body = self.query_one("#request-body", TextArea)
            body_text = data["request_body"]
            if isinstance(body_text, dict):
                body_text = json.dumps(body_text, indent=2)
            request_body.text = body_text

        # Request headers
        if "request_headers" in data:
            request_headers = self.query_one("#request-headers", TextArea)
            headers_text = json.dumps(data["request_headers"], indent=2)
            request_headers.text = headers_text

        # Response body (previous response, read-only)
        if "response_body" in data:
            response_body = self.query_one("#response-body", TextArea)
            resp_text = data["response_body"]
            if isinstance(resp_text, (dict, list)):
                resp_text = json.dumps(resp_text, indent=2)
            response_body.text = resp_text

        # Response headers (previous response, read-only)
        if "response_headers" in data:
            response_headers = self.query_one("#response-headers", TextArea)
            resp_headers_text = json.dumps(data["response_headers"], indent=2)
            response_headers.text = resp_headers_text

        # Update response header to show it's a previous response
        if "response_body" in data or "response_headers" in data:
            response_header = self.query_one("#response-header", Static)
            response_header.update("Response (Previous Response - read-only, copyable)")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "send-button":
            # Run async action in worker
            self.run_worker(self.action_send_request())
        elif event.button.id == "clear-response-button":
            self.action_clear_response()
        elif event.button.id == "clear-all-button":
            self.action_clear_all()

    async def action_send_request(self) -> None:
        """Send HTTP request to AWX API"""
        # Get form values
        method = self.query_one("#method-select", Select).value
        endpoint = self.query_one("#endpoint-input", Input).value.strip()
        request_body_widget = self.query_one("#request-body", TextArea)
        request_body_text = request_body_widget.text.strip()

        # Validate endpoint
        if not endpoint:
            self.notify("Endpoint is required", severity="error", timeout=3)
            return

        # Parse request body as JSON if present
        request_data = None
        if request_body_text:
            try:
                request_data = json.loads(request_body_text)
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON: {e}", severity="error", timeout=5)
                return

        # Show sending toast
        self.notify("Sending request...", timeout=2)

        # Send request
        try:
            instance_manager = self.app.instance_manager

            # Use instance override if set (from debug console), otherwise use current instance
            # Handle both None and empty string as "not set"
            instance_name = (
                self.instance_override
                if (self.instance_override is not None and self.instance_override != "")
                else instance_manager.current_instance
            )

            # Get client for the target instance (not necessarily the current one)
            client = instance_manager.get_client(instance_name)

            from awx_tui.client import AWXClient

            # Track request timing
            start_time = datetime.now()

            # Make request based on method
            if isinstance(client, AWXClient):
                async with client:
                    response_data = await self._make_request(client, method, endpoint, request_data)
            else:
                response_data = await self._make_request(client, method, endpoint, request_data)

            # Calculate duration
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Update response pane
            self._update_response(response_data, status_code=200, duration_ms=duration_ms)

            # Show success toast
            self.notify("200 OK", timeout=3)

        except Exception as e:
            # Calculate duration for error case
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000) if "start_time" in locals() else 0

            # Extract HTTP status code from exception type or message
            import re

            from awx_tui.client import (
                AWXAuthenticationError,
                AWXClientError,
                AWXNotFoundError,
                AWXServerError,
                AWXTimeoutError,
            )

            status_code = 0
            error_str = str(e)

            # Map exception types to HTTP status codes
            if isinstance(e, AWXNotFoundError):
                status_code = 404
            elif isinstance(e, AWXAuthenticationError):
                # Could be 401 or 403, try to determine from message
                if "forbidden" in error_str.lower() or "lack permissions" in error_str.lower():
                    status_code = 403
                else:
                    status_code = 401
            elif isinstance(e, AWXServerError):
                # Try to extract 5xx code from message
                status_match = re.search(r"(\d{3})", error_str)
                if status_match:
                    code = int(status_match.group(1))
                    if 500 <= code < 600:
                        status_code = code
                    else:
                        status_code = 500
                else:
                    status_code = 500
            elif isinstance(e, (AWXTimeoutError, AWXClientError)):
                # Try to extract HTTP code from message (e.g., "HTTP 400: Bad Request")
                status_match = re.search(r"HTTP (\d{3})", error_str)
                if status_match:
                    status_code = int(status_match.group(1))
                # Otherwise leave as 0 (network error, timeout, etc.)

            # Show error
            error_response = {"error": error_str, "timestamp": datetime.now().isoformat()}
            self._update_response(error_response, status_code=status_code, duration_ms=duration_ms)
            self.notify(f"Request failed: {e}", severity="error", timeout=5)

    async def _make_request(self, client, method: str, endpoint: str, data: Optional[Any]) -> Dict[str, Any]:
        """Make HTTP request using AWX client"""
        if method == "GET":
            return await client.get(endpoint)
        elif method == "POST":
            return await client.post(endpoint, data=data)
        elif method == "PUT":
            return await client.put(endpoint, data=data)
        elif method == "PATCH":
            return await client.patch(endpoint, data=data)
        elif method == "DELETE":
            await client.delete(endpoint)
            return {"message": "Delete successful"}
        elif method == "HEAD":
            return await client.head(endpoint)
        elif method == "OPTIONS":
            return await client.options(endpoint)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def _update_response(self, response_data: Dict[str, Any], status_code: int, duration_ms: int = 0) -> None:
        """Update response pane with new response"""
        # Update response body
        response_body = self.query_one("#response-body", TextArea)
        response_text = json.dumps(response_data, indent=2)
        response_body.text = response_text

        # Calculate response size
        size_bytes = len(response_text)
        if size_bytes > 1024:
            size_str = f"{size_bytes / 1024:.1f}KB"
        else:
            size_str = f"{size_bytes}B"

        # Update response header with status code, duration, and size
        response_header = self.query_one("#response-header", Static)
        if status_code >= 200 and status_code < 300:
            # Successful response (2xx)
            response_header.update(
                f"Response (Status: {status_code} - {duration_ms}ms - {size_str} - read-only, copyable)"
            )
        elif status_code >= 300:
            # Error response (3xx, 4xx, 5xx)
            response_header.update(
                f"Response (Status: {status_code} - {duration_ms}ms - {size_str} - read-only, copyable)"
            )
        else:
            # status_code == 0 or unknown - network error, not HTTP error
            response_header.update(f"Response (Error - {duration_ms}ms - {size_str} - read-only, copyable)")

        self._last_response_status = status_code

        # TODO: Update response headers tab when we have access to response headers
        # For now, leave response headers empty

    def action_clear_response(self) -> None:
        """Clear only response body and headers (keep request)"""
        # Clear response body
        self.query_one("#response-body", TextArea).text = ""

        # Clear response headers
        self.query_one("#response-headers", TextArea).text = ""

        # Reset response header
        self.query_one("#response-header", Static).update("Response (read-only, copyable)")

        self.notify("Cleared response", timeout=2)

    def action_clear_all(self) -> None:
        """Clear all fields (endpoint, request body, response body, headers)"""
        # Clear endpoint
        self.query_one("#endpoint-input", Input).value = ""

        # Clear request body
        self.query_one("#request-body", TextArea).text = ""

        # Clear response body
        self.query_one("#response-body", TextArea).text = ""

        # Clear response headers
        self.query_one("#response-headers", TextArea).text = ""

        # Reset response header
        self.query_one("#response-header", Static).update("Response (read-only, copyable)")

        # Don't clear request headers (they're auto-populated from client defaults)

        self.notify("Cleared all fields", timeout=2)

    def action_format_json(self) -> None:
        """Format JSON in focused pane (request or response)"""
        # Try to format the currently focused TextArea
        focused = self.app.focused

        if isinstance(focused, TextArea) and not focused.read_only:
            # Only format editable text areas (request body)
            try:
                current_text = focused.text.strip()
                if current_text:
                    parsed = json.loads(current_text)
                    formatted = json.dumps(parsed, indent=2)
                    focused.text = formatted
                    self.notify("JSON formatted", timeout=2)
                else:
                    self.notify("No content to format", timeout=2)
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON: {e}", severity="error", timeout=3)
        else:
            self.notify("Focus an editable field to format JSON", timeout=2)

    def action_close(self) -> None:
        """Close Advanced API Mode and return to previous screen"""
        self.app.pop_screen()
