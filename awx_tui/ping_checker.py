"""
AWX TUI - Ping Checker

Checks AWX instance connectivity and health via /ping/ endpoint.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


def _prune_api_log(api_call_log: Optional[list], max_entries: int = 1000) -> None:
    """
    Prune API call log to keep only most recent entries (ring buffer)

    Args:
        api_call_log: The API call log list to prune
        max_entries: Maximum number of entries to keep (0 = unlimited)
    """
    if api_call_log is not None and max_entries > 0:
        if len(api_call_log) > max_entries:
            api_call_log[:] = api_call_log[-max_entries:]


def _log_ping_connection_event(
    connection_event_log: Optional[list],
    instance_name: Optional[str],
    event: str,
    details: str,
    max_entries: int = 1000,
) -> None:
    """Log a connection event from the ping checker"""
    if connection_event_log is None:
        return

    connection_event_log.append(
        {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "instance": instance_name or "unknown",
            "event": event,
            "details": details,
            "pool_snapshot": None,
        }
    )

    if max_entries > 0 and len(connection_event_log) > max_entries:
        connection_event_log[:] = connection_event_log[-max_entries:]


async def check_instance_ping(
    url: str,
    api_base_path: str = "/api/v2",
    verify_ssl: bool = True,
    timeout: float = 10.0,
    api_call_log: Optional[list] = None,
    instance_name: Optional[str] = None,
    max_log_entries: int = 1000,
    connection_event_log: Optional[list] = None,
    shared_client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """
    Check AWX instance connectivity via ping endpoint

    Args:
        url: Base URL (e.g., https://awx.example.com)
        api_base_path: API base path (e.g., /api/v2 or /api/controller/v2)
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds
        api_call_log: Optional list to log API calls for debug console
        instance_name: Optional instance name for debug logging
        connection_event_log: Optional list to log connection pool events
        shared_client: Optional persistent httpx.AsyncClient to reuse (ping-pool)

    Returns:
        Dictionary with:
        - status: 'online', 'slow', 'very_slow', 'offline', 'error'
        - version: AWX version string or 'Unknown'
        - response_time_ms: Response time in milliseconds
        - response_time: Formatted response time string
        - error: Error message if failed
    """
    ping_url = f"{url}{api_base_path}/ping/"
    start_time = time.time()

    result = {"status": "unknown", "version": "Unknown", "response_time_ms": 0, "response_time": "N/A", "error": None}

    # Use shared client if provided, otherwise create a throwaway one
    client = shared_client
    owns_client = False
    if client is None:
        client = httpx.AsyncClient(verify=verify_ssl, timeout=timeout)
        owns_client = True

    try:
        response = await client.get(ping_url)

        # Calculate response time
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["response_time_ms"] = elapsed_ms

        # Format response time
        if elapsed_ms < 1000:
            result["response_time"] = f"{elapsed_ms}ms"
        else:
            result["response_time"] = f"{elapsed_ms / 1000:.1f}s"

        # Determine status based on response time
        if elapsed_ms < 1000:
            result["status"] = "online"
        elif elapsed_ms < 5000:
            result["status"] = "slow"
        elif elapsed_ms < 10000:
            result["status"] = "very_slow"
        else:
            result["status"] = "offline"

        # Parse response for version - all 2xx codes are success
        if 200 <= response.status_code < 300:
            try:
                data = response.json()
                result["version"] = data.get("version", "Unknown")

                # Log successful API call
                if api_call_log is not None:
                    api_call_log.append(
                        {
                            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                            "method": "GET",
                            "instance": url,
                            "instance_name": instance_name or "unknown",
                            "endpoint": f"{api_base_path}/ping/",
                            "url": ping_url,
                            "status_code": response.status_code,
                            "duration_ms": elapsed_ms,
                            "size_bytes": len(response.content),
                            "request_headers": dict(response.request.headers),
                            "response_headers": dict(response.headers),
                            "content_preview": response.text[:500],
                            "response_content_full": response.text,
                        }
                    )
                    _prune_api_log(api_call_log, max_log_entries)
            except Exception as e:
                result["error"] = f"Failed to parse response: {e}"
        else:
            result["status"] = "error"
            result["error"] = f"HTTP {response.status_code}"

            # Log error API call
            if api_call_log is not None:
                api_call_log.append(
                    {
                        "timestamp": time.strftime("%H:%M:%S"),
                        "method": "GET",
                        "instance": url,
                        "instance_name": instance_name or "unknown",
                        "endpoint": f"{api_base_path}/ping/",
                        "url": ping_url,
                        "status_code": response.status_code,
                        "duration_ms": elapsed_ms,
                        "size_bytes": len(response.content),
                        "request_headers": dict(response.request.headers),
                        "response_headers": dict(response.headers),
                        "content_preview": response.text[:500],
                        "error": f"HTTP {response.status_code}",
                    }
                )
                _prune_api_log(api_call_log, max_log_entries)

    except httpx.TimeoutException:
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["status"] = "offline"
        result["response_time_ms"] = elapsed_ms
        result["response_time"] = "Timeout"
        result["error"] = "Request timeout"

        # Log timeout
        if api_call_log is not None:
            api_call_log.append(
                {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "method": "GET",
                    "instance": url,
                    "instance_name": instance_name or "unknown",
                    "endpoint": f"{api_base_path}/ping/",
                    "url": ping_url,
                    "status_code": 0,
                    "duration_ms": elapsed_ms,
                    "size_bytes": 0,
                    "error": "Request timeout",
                }
            )
            _prune_api_log(api_call_log)

    except httpx.ConnectError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["status"] = "offline"
        result["response_time_ms"] = elapsed_ms
        result["response_time"] = "N/A"
        result["error"] = f"Connection error: {str(e)}"

        # Log connection error
        if api_call_log is not None:
            api_call_log.append(
                {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "method": "GET",
                    "instance": url,
                    "instance_name": instance_name or "unknown",
                    "endpoint": f"{api_base_path}/ping/",
                    "url": ping_url,
                    "status_code": 0,
                    "duration_ms": elapsed_ms,
                    "size_bytes": 0,
                    "error": f"Connection error: {str(e)}",
                }
            )
            _prune_api_log(api_call_log)

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["status"] = "error"
        result["response_time_ms"] = elapsed_ms
        result["response_time"] = "N/A"
        result["error"] = str(e)

        # Log generic error
        if api_call_log is not None:
            api_call_log.append(
                {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "method": "GET",
                    "instance": url,
                    "instance_name": instance_name or "unknown",
                    "endpoint": f"{api_base_path}/ping/",
                    "url": ping_url,
                    "status_code": 0,
                    "duration_ms": elapsed_ms,
                    "size_bytes": 0,
                    "error": str(e),
                }
            )
            _prune_api_log(api_call_log)

    finally:
        # Only close the client if we created it (throwaway)
        if owns_client:
            await client.aclose()

    return result
