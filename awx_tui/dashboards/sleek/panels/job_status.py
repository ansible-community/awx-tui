"""
AWX TUI - Sleek Dashboard Job Status Panel

Displays job success/failure graphs over the last 7 days.
"""

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from textual.widgets import DataTable, Static

if TYPE_CHECKING:
    from awx_tui.dashboards.sleek.dashboard import SleekDashboard


class JobStatusPanel:
    """
    Manages the JOB STATUS panel showing success/failure trends.

    Two views:
    - DataTable with date, success bar (count), failed bar (count)
    - Visual ASCII graph with success/failed markers
    """

    def __init__(self, dashboard: "SleekDashboard"):
        self.dashboard = dashboard

    def setup_table(self) -> None:
        """Configure DataTable columns for job status graph."""
        try:
            table = self.dashboard.query_one("#jobs-graph-table", DataTable)
            table.add_columns("Date", "Successful", "Failed")
            table.show_header = True
        except Exception:
            pass

    def update(self, jobs: list) -> None:
        """Update combined jobs graph DataTable with last 7 days success/failed data."""
        # Initialize counters for last 7 days (today = day 0, yesterday = day 1, etc.)
        success_counts = [0] * 7
        failed_counts = [0] * 7
        dates = []

        # Get current date (ignore time)
        today = datetime.now().date()

        # Build date list (7 days ago to today)
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            dates.append(date)

        # Count jobs by day
        for job in jobs:
            finished = job.get("finished")
            if not finished:
                continue

            try:
                # Parse finished timestamp (ISO 8601 format from AWX API)
                job_date = datetime.fromisoformat(finished.replace("Z", "+00:00")).date()

                # Calculate days ago
                days_ago = (today - job_date).days

                # Only count jobs from last 7 days
                if 0 <= days_ago < 7:
                    status = job.get("status", "")
                    if status == "successful":
                        success_counts[6 - days_ago] += 1  # Reverse index
                    elif status == "failed":
                        failed_counts[6 - days_ago] += 1  # Reverse index
            except (ValueError, AttributeError):
                # Skip jobs with invalid timestamps
                continue

        # Find max count for relative scaling (unified across both columns)
        max_success = max(success_counts) if success_counts else 0
        max_failed = max(failed_counts) if failed_counts else 0
        max_value = max(max_success, max_failed)  # Use same scale for both columns

        # Update combined jobs graph table (most recent first)
        jobs_graph_table = self.dashboard.query_one("#jobs-graph-table", DataTable)
        jobs_graph_table.clear()

        # Calculate bar width based on max count from either column (for alignment)
        max_digits = len(str(max_value)) if max_value > 0 else 1
        bar_width = max(1, 8 - max_digits)  # At least 1 block

        for i in range(len(dates) - 1, -1, -1):  # Reverse order (today first)
            date = dates[i]
            success_count = success_counts[i]
            failed_count = failed_counts[i]

            # Format date as "Mon 2025-11-18"
            date_str = date.strftime("%a %Y-%m-%d")

            # Build cells with unified relative scaling (both columns use same max)
            success_cell = self._build_status_cell(success_count, max_value, "#008000", bar_width)
            failed_cell = self._build_status_cell(failed_count, max_value, "red", bar_width)

            jobs_graph_table.add_row(date_str, success_cell, failed_cell)

        # Update visual graph
        self._update_visual(dates, success_counts, failed_counts, max_success, max_failed)

    def _build_status_cell(self, count: int, max_value: int, color: str, bar_width: int) -> str:
        """
        Build a status cell with bar and count.

        Format: "bar (count)" where bar width is provided for alignment.
        Uses relative scaling - highest value fills the bar completely.
        """
        count_str = str(count)
        bar = self._build_relative_bar(count, max_value, color, bar_width)
        return f"{bar} ({count_str})"

    def _build_relative_bar(self, count: int, max_value: int, color: str, num_blocks: int = 7) -> str:
        """
        Build relative-scaled bar.

        The highest value in the dataset fills the bar completely.
        Other values are scaled proportionally.
        - SOLID: Proportional fill based on value/max
        - DITHERED: Partial block fill
        - EMPTY: No value in this portion
        """
        # Calculate percentage of max value (relative scaling)
        pct = (count / max_value * 100) if max_value > 0 else 0

        # Build bar with num_blocks blocks
        block_pct = 100 / num_blocks  # Each block's percentage
        full_blocks = int(pct / block_pct)
        remainder = pct % block_pct

        bar = ""
        for i in range(num_blocks):
            if i < full_blocks:
                bar += "█"  # Solid - fully filled
            elif i == full_blocks and remainder > 0:
                # Dithered - partial fill
                if remainder >= block_pct * 0.7:
                    bar += "▓"
                elif remainder >= block_pct * 0.35:
                    bar += "▒"
                else:
                    bar += "░"
            else:
                bar += "░"  # Empty

        return f"[{color}]{bar}[/{color}]"

    def _update_visual(self, dates, success_counts, failed_counts, max_success, max_failed):
        """
        Update visual graph display showing success/failed jobs over time.
        Creates a multi-row ASCII line graph with Y-axis and dates on X-axis.
        """
        # Handle empty data case
        if not dates or len(dates) == 0:
            try:
                visual_widget = self.dashboard.query_one("#jobs-graph-visual", Static)
                visual_widget.update("No data available")
            except Exception:
                pass
            return

        # Determine max value for scaling
        max_val = max(max_success, max_failed, 1)

        # Graph dimensions
        height = 6  # Number of rows for the graph area
        panel_width = 46
        num_dates = len(dates)

        # Calculate Y-axis label space
        y_labels_temp = []
        for row in range(height):
            value = int(max_val * (height - row) / height) if height > 0 else 0
            y_labels_temp.append(str(value))
        max_label_width = max(len(label) for label in y_labels_temp)

        # Available width for graph
        y_axis_space = max_label_width
        available_width = panel_width - y_axis_space

        # Calculate spacing between date columns
        col_spacing = available_width // num_dates if num_dates > 0 else 1
        col_spacing = max(col_spacing, 5)  # At least 5 chars per date for "mm/dd"
        graph_width = col_spacing * num_dates

        # Initialize graph grid
        grid = [[" " for _ in range(graph_width)] for _ in range(height)]

        # Plot success and failed points at evenly spaced columns
        for i in range(num_dates):
            col_pos = i * col_spacing + (col_spacing // 2) - 1

            # Calculate row position (0 = top, height-1 = bottom)
            if max_val > 0:
                success_row = height - 1 - int((success_counts[i] / max_val) * (height - 1))
                failed_row = height - 1 - int((failed_counts[i] / max_val) * (height - 1))
            else:
                success_row = height - 1
                failed_row = height - 1

            # Mark the points (skip if count is 0)
            has_success = success_counts[i] > 0
            has_failed = failed_counts[i] > 0

            if has_success and has_failed and success_row == failed_row:
                grid[success_row][col_pos] = "B"  # Both on same row
            else:
                if has_success:
                    grid[success_row][col_pos] = "S"  # Success
                if has_failed:
                    grid[failed_row][col_pos] = "F"  # Failed

        # Build the visual output
        lines = []

        # Build each row with Y-axis label
        for row in range(height):
            label = y_labels_temp[row].rjust(max_label_width)
            row_chars = []

            for col in range(graph_width):
                char = grid[row][col]
                if char == "S":
                    row_chars.append("[#008000]✓[/#008000]")
                elif char == "F":
                    row_chars.append("[red]✗[/red]")
                elif char == "B":
                    row_chars.append("[yellow]~[/yellow]")  # Tilde for both success and failure
                elif col < graph_width - 1:
                    if (col + 1) % 3 == 0:
                        dot_char = random.choice(["⊹", "·"])  # NOSONAR
                        row_chars.append(f"[dim]{dot_char}[/dim]")
                    else:
                        row_chars.append(" ")

            lines.append(f"{label}│{''.join(row_chars)}")

        # Add X-axis separator with 0 label on left
        x_axis = "0".rjust(max_label_width) + "└" + "─" * (graph_width - 1)
        lines.append(x_axis)

        # Add date labels (mm/dd format) - "/" aligned with data points
        date_label_line = " " * max_label_width
        for i in range(num_dates):
            date_str = dates[i].strftime("%m/%d")
            slash_offset = 2
            center_of_column = col_spacing // 2
            padding_before = center_of_column - slash_offset
            padding_after = col_spacing - len(date_str) - padding_before

            date_label_line += " " * padding_before + date_str + " " * padding_after

        lines.append(date_label_line)

        visual = "\n".join(lines)

        # Update the visual widget
        try:
            visual_widget = self.dashboard.query_one("#jobs-graph-visual", Static)
            visual_widget.update(visual)
        except Exception:
            pass
