"""
AWX TUI - The Network Queue Screen

Connection pool management dashboard with live pool status,
per-connection details, and historical event log.
"""

import re
from typing import Any, List, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


def _snapshot_pool_connections(pool) -> Tuple[List[Tuple[str, bool, bool]], int, int]:
    """Capture a point-in-time snapshot of all connections in a pool.

    Returns:
        Tuple of (conn_snapshot, idle_count, active_count) where conn_snapshot
        is a list of (info_str, is_idle, is_closed) tuples.
    """
    conn_snapshot = []
    idle = 0
    for conn in pool.connections:
        info_str = str(conn.info())
        is_idle = conn.is_idle()
        is_closed = conn.is_closed()
        if is_idle:
            idle += 1
        conn_snapshot.append((info_str, is_idle, is_closed))

    active = len(conn_snapshot) - idle
    return conn_snapshot, idle, active


def _parse_connection_info(info_str: str) -> Tuple[str, str, str]:
    """Parse an httpcore connection info string into components.

    Args:
        info_str: String like "'host:port', HTTP/1.1, IDLE, Request Count: 5"

    Returns:
        Tuple of (origin, http_version, request_count)
    """
    origin = "unknown"
    http_ver = "unknown"
    req_count = "0"

    origin_match = re.search(r"'([^']+)'", info_str)
    if origin_match:
        origin = origin_match.group(1)

    http_match = re.search(r"(HTTP/[\d.]+)", info_str)
    if http_match:
        http_ver = http_match.group(1)

    count_match = re.search(r"Request Count:\s*(\d+)", info_str)
    if count_match:
        req_count = count_match.group(1)

    return origin, http_ver, req_count


def _connection_state_label(is_idle: bool, is_closed: bool) -> str:
    """Return a colored state label for a connection."""
    if is_closed:
        return "[red]CLOSED[/red]"
    if is_idle:
        return "[green]IDLE[/green]"
    return "[yellow]ACTIVE[/yellow]"


class TheNetworkQueueScreen(Screen):
    """
    The Network Queue - Connection Pool Management Dashboard

    Three sections:
    1. Pool Overview - all pools with high-level stats
    2. Connections - individual connections in the selected pool
    3. Event Log - historical connection events
    """

    CSS = """
    #nq_title_bar {
        width: 100%;
        height: auto;
        dock: top;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0 1;
    }

    #nq_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        padding: 0;
    }

    #nq_main {
        width: 100%;
        height: 1fr;
    }

    #pool_table {
        height: auto;
        max-height: 12;
        border: solid $primary;
        margin: 0 1;
    }

    #conn_label {
        padding: 0 1;
        color: $text-muted;
        height: auto;
    }

    #conn_table {
        height: 12;
        border: solid $secondary;
        margin: 0 1;
    }

    #event_label {
        padding: 0 1;
        color: $text-muted;
        height: auto;
    }

    #event_list {
        height: 7;
        border: solid $primary;
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("backspace", "back", "Back", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("ctrl+k", "close_pool", "Close Pool", show=True),
        Binding("ctrl+x", "purge", "Purge Log", show=True),
        Binding("ctrl+n", "no_action", "", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_data = []
        self.pool_data = []  # List of (instance_name, client, conn_snapshot) tuples
        self.selected_pool_name = None

    def compose(self) -> ComposeResult:
        """Create the network queue dashboard layout"""
        yield Header()

        # Title bar
        with Container(id="nq_title_bar"):
            yield Static("The Network Queue", id="nq_title")

        # Main content - vertically stacked sections
        with Vertical(id="nq_main"):
            # Section 1: Pool overview table
            pool_table = DataTable(id="pool_table", cursor_type="row")
            pool_table.add_columns("Instance", "Status", "Conns", "Active", "Idle", "Max", "Keepalive")
            yield pool_table

            # Section 2: Connection detail table
            yield Static("Connections: Select a pool above", id="conn_label")
            conn_table = DataTable(id="conn_table", cursor_type="row")
            conn_table.add_columns("Origin", "HTTP Version", "State", "Request Count")
            yield conn_table

            # Section 3: Pool event log
            yield Static("Pool Event Log", id="event_label")
            event_table = DataTable(id="event_list", cursor_type="row")
            event_table.add_columns("Time", "Instance", "Event", "Details")
            yield event_table

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the dashboard"""
        self.refresh_all()

    def refresh_all(self) -> None:
        """Load all three sections"""
        self.load_pools()
        self.load_connections()
        self.load_events()

        # Auto-select first pool if available
        pool_table = self.query_one("#pool_table", DataTable)
        if self.pool_data:
            pool_table.cursor_coordinate = (0, 0)
            self.selected_pool_name = self.pool_data[0][0]
            self.load_connections()

        # Auto-select last event row
        event_table = self.query_one("#event_list", DataTable)
        if self.event_data:
            last_row = len(self.event_data) - 1
            event_table.cursor_coordinate = (last_row, 0)

    def _get_pool_row(self, name, client) -> Tuple[tuple, Any, list]:
        """Build a pool table row and snapshot for a single client.

        Returns:
            Tuple of (row_values, client_ref, conn_snapshot)
        """
        from awx_tui.client import AWXClient
        from awx_tui.config import InstanceConfig
        from awx_tui.mock_data import MockAWXClient

        if isinstance(client, AWXClient) and client.session and not client.session.is_closed:
            try:
                pool = client.session._transport._pool
                conn_snapshot, idle, active = _snapshot_pool_connections(pool)
                row = (
                    name,
                    "[green]●[/green] Active",
                    str(len(conn_snapshot)),
                    str(active),
                    str(idle),
                    str(pool._max_connections),
                    str(pool._max_keepalive_connections),
                )
                return row, client, conn_snapshot
            except Exception:
                row = (name, "[yellow]●[/yellow] Unknown", "-", "-", "-", "-", "-")
                return row, client, []

        if isinstance(client, AWXClient):
            row = (
                name,
                "[dim]○[/dim] No session",
                "0",
                "0",
                "0",
                str(client.max_connections),
                str(client.max_keepalive_connections),
            )
            return row, client, []

        if isinstance(client, InstanceConfig):
            row = (name, "[dim]○[/dim] Not connected", "-", "-", "-", "-", "-")
            return row, None, []

        if isinstance(client, MockAWXClient):
            row = (name, "[dim]○[/dim] Mock", "-", "-", "-", "-", "-")
            return row, None, []

        row = (name, "[dim]○[/dim] Unknown", "-", "-", "-", "-", "-")
        return row, None, []

    def load_pools(self) -> None:
        """Load pool overview table"""
        pool_table = self.query_one("#pool_table", DataTable)
        prev_selected = self.selected_pool_name

        pool_table.clear()
        self.pool_data = []

        instance_manager = getattr(self.app, "instance_manager", None)
        if not instance_manager:
            return

        for name in instance_manager.get_instance_names():
            client = instance_manager.clients.get(name)
            row, client_ref, conn_snapshot = self._get_pool_row(name, client)
            pool_table.add_row(*row)
            self.pool_data.append((name, client_ref, conn_snapshot))

        # Restore selection
        if prev_selected:
            for i, (pname, _, _snapshot) in enumerate(self.pool_data):
                if pname == prev_selected:
                    pool_table.cursor_coordinate = (i, 0)
                    break

    def load_connections(self) -> None:
        """Load connections for the selected pool from the snapshot captured by load_pools"""
        conn_table = self.query_one("#conn_table", DataTable)
        conn_label = self.query_one("#conn_label", Static)

        conn_table.clear()

        if not self.selected_pool_name:
            conn_label.update("Connections: Select a pool above")
            return

        # Find the snapshot for the selected pool
        conn_snapshot = None
        for pname, _pclient, snapshot in self.pool_data:
            if pname == self.selected_pool_name:
                conn_snapshot = snapshot
                break

        if conn_snapshot is None:
            conn_label.update(f"Connections: {self.selected_pool_name} (no active session)")
            return

        conn_label.update(f"Connections: {self.selected_pool_name} ({len(conn_snapshot)} total)")

        for info_str, is_idle, is_closed in conn_snapshot:
            origin, http_ver, req_count = _parse_connection_info(info_str)
            state = _connection_state_label(is_idle, is_closed)
            conn_table.add_row(origin, http_ver, state, req_count)

    def load_events(self) -> None:
        """Load connection events from app's connection event log"""
        event_table = self.query_one("#event_list", DataTable)

        # Remember selection
        prev_row = None
        if hasattr(event_table, "cursor_coordinate") and event_table.cursor_coordinate:
            prev_row = event_table.cursor_coordinate[0]

        event_table.clear()
        self.event_data = []

        events = getattr(self.app, "connection_event_log", [])

        for event in reversed(events):
            timestamp = event.get("timestamp", "Unknown")
            instance = event.get("instance", "Unknown")
            event_type = event.get("event", "Unknown")
            details = str(event.get("details", ""))[:60]

            event_emoji = {
                "POOL_CREATED": "[green]✓[/green]",
                "POOL_CLOSED": "[yellow]✗[/yellow]",
                "POOL_EXHAUSTED": "[red]✗[/red]",
                "PING_CONN_OPENED": "[cyan]↔[/cyan]",
            }.get(event_type, "ℹ ")

            event_table.add_row(timestamp, instance, f"{event_emoji} {event_type}", details)
            self.event_data.append(event)

        # Restore selection
        if prev_row is not None and prev_row < len(self.event_data):
            event_table.cursor_coordinate = (prev_row, 0)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight in any table"""
        if event.data_table.id == "pool_table":
            row_index = event.cursor_row
            if 0 <= row_index < len(self.pool_data):
                self.selected_pool_name = self.pool_data[row_index][0]
                self.load_connections()

    def action_back(self) -> None:
        """Close the network queue screen"""
        self.app.pop_screen()

    def action_refresh(self) -> None:
        """Manual refresh all sections"""
        self.refresh_all()
        self.notify("Network Queue refreshed", timeout=1)

    def action_close_pool(self) -> None:
        """Close the selected pool's session"""
        if not self.selected_pool_name:
            self.notify("No pool selected", severity="warning", timeout=2)
            return

        for pname, pclient, _snapshot in self.pool_data:
            if pname == self.selected_pool_name:
                from awx_tui.client import AWXClient

                if isinstance(pclient, AWXClient) and pclient.session and not pclient.session.is_closed:
                    self.run_worker(self._do_close_pool(pclient, pname))
                else:
                    self.notify(f"{pname}: No active session to close", severity="warning", timeout=2)
                return

    async def _do_close_pool(self, client, name: str) -> None:
        """Actually close an AWXClient pool"""
        await client.close()
        self.notify(f"Pool closed: {name}", timeout=2)
        self.refresh_all()

    def action_purge(self) -> None:
        """Purge all connection event data"""
        if hasattr(self.app, "connection_event_log"):
            self.app.connection_event_log.clear()
            self.notify("Connection event log purged", severity="warning")
            self.load_events()

    def action_no_action(self) -> None:
        """Do nothing - used to override Ctrl+N"""
        pass

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()
