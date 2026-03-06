"""
AWX TUI - The Loaf Screen

Notification history debugger - view all toast messages that have been displayed.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class NotificationDetailsPanel(Static):
    """Right panel showing detailed notification information"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_info = None

    def update_notification_info(self, notification_info: dict):
        """Update the displayed notification information"""
        self.notification_info = notification_info
        if notification_info:
            timestamp = notification_info["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            severity = notification_info["severity"]
            message = str(notification_info["message"]).replace("[", "\\[")
            title = str(notification_info.get("title", "")).replace("[", "\\[")
            source = notification_info.get("source", "Unknown")
            timeout = notification_info.get("timeout", "N/A")

            # Severity emoji (using single-width characters)
            severity_emoji = {
                "error": "[red]✗[/red]",
                "warning": "⚠ ",
                "information": "ℹ ",
                "success": "✓",
            }.get(severity, "❓")

            title_line = f"\nTitle: {title}" if title else ""

            details = f"""[green]{severity_emoji}[/green] {severity.upper()}
Time: {timestamp}
Source: {source}
Timeout: {timeout}s{title_line}

Message:
{message}"""

            self.update(details)
        else:
            self.update("Select a notification to view details")


class TheLoafScreen(Screen):
    """
    The Loaf - Notification History Debugger

    Shows all toast notifications that have been displayed during the session.
    Useful for reviewing errors that disappeared too quickly.
    """

    CSS = """
    #loaf_top_panel {
        width: 100%;
        height: auto;
        dock: top;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0 1;
    }

    #loaf_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        padding: 0;
    }

    #loaf_content {
        width: 100%;
        height: 1fr;
    }

    #notification_list {
        width: 60%;
        border: solid $primary;
        margin: 1;
    }

    #notification_details {
        width: 40%;
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("backspace", "back", "Back", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("ctrl+x", "purge", "Purge All", show=True),
        Binding("ctrl+o", "no_action", "", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_data = []

    def compose(self) -> ComposeResult:
        """Create the loaf screen layout"""
        yield Header()

        # Top panel with title
        with Container(id="loaf_top_panel"):
            yield Static("🍞 The Loaf", id="loaf_title")

        # Main content area - horizontal split
        with Horizontal(id="loaf_content"):
            # Left panel - notification list
            notification_table = DataTable(id="notification_list", cursor_type="row")
            notification_table.add_columns("Time", "Severity", "Message", "Source")
            yield notification_table

            # Right panel - notification details
            yield NotificationDetailsPanel(id="notification_details")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the loaf screen"""
        self.load_notifications()

        # Auto-select last row (most recent notification) on initial load
        notification_table = self.query_one("#notification_list", DataTable)
        if self.notification_data:
            last_row = len(self.notification_data) - 1
            notification_table.cursor_coordinate = (last_row, 0)
            self.update_details_for_row(last_row)
        else:
            # No notifications yet - show placeholder
            details_panel = self.query_one("#notification_details", NotificationDetailsPanel)
            details_panel.update("Select a notification to view details")

    def load_notifications(self) -> None:
        """Load notifications from app's notification log"""
        notification_table = self.query_one("#notification_list", DataTable)

        # Clear existing data
        notification_table.clear()
        self.notification_data = []

        # Get notifications from app
        notifications = getattr(self.app, "notification_log", [])

        # Add rows in reverse chronological order (newest first)
        for notif in reversed(notifications):
            timestamp = notif["timestamp"].strftime("%H:%M:%S")
            severity = notif["severity"]
            message = notif["message"][:60]  # Truncate for table display
            source = notif.get("source", "Unknown")

            # Severity emoji (using single-width characters)
            severity_emoji = {
                "error": "[red]✗[/red]",
                "warning": "⚠ ",
                "information": "ℹ ",
                "success": "[green]✓[/green]",
            }.get(severity, "❓")

            notification_table.add_row(timestamp, severity_emoji, message, source)
            self.notification_data.append(notif)

    def update_details_for_row(self, row_index: int) -> None:
        """Update the details panel for the given row index"""
        if 0 <= row_index < len(self.notification_data):
            notification = self.notification_data[row_index]
            details_panel = self.query_one("#notification_details", NotificationDetailsPanel)
            details_panel.update_notification_info(notification)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update details when a row is highlighted"""
        if event.data_table.id == "notification_list":
            row_index = event.cursor_row
            self.update_details_for_row(row_index)

    def action_back(self) -> None:
        """Close the loaf screen"""
        self.app.pop_screen()

    def action_refresh(self) -> None:
        """Refresh the table"""
        self.load_notifications()
        self.notify("Refreshed", timeout=1)

    def action_purge(self) -> None:
        """Purge all notification data"""
        if hasattr(self.app, "notification_log"):
            self.app.notification_log.clear()
            self.notify("Notification log purged", severity="warning")
            # Reload the list
            self.load_notifications()

    def action_no_action(self) -> None:
        """Do nothing - used to override Ctrl+O"""
        pass

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()
