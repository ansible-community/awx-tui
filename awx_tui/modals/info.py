"""
AWX TUI - Info/About Modal

Shows application info with cowsay per INFO_MODAL.md
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from awx_tui import TAGLINE, __version__


class InfoModal(ModalScreen):
    """Info/About modal showing app info, version, and credits"""

    CSS = """
    InfoModal {
        align: center middle;
    }

    #info-dialog {
        width: 76;
        height: 29;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        width: 100%;
    }

    #tagline {
        text-align: center;
        color: $text-muted;
        width: 100%;
    }

    #cowsay-version {
        text-align: left;
        width: 100%;
        margin-bottom: 1;
    }

    #info-content {
        width: 100%;
        text-align: left;
    }

    #button-container {
        width: 100%;
        align: center middle;
    }

    #close-button {
        width: auto;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("enter", "dismiss", "Close"),
    ]

    def __init__(self, app_name: str):
        """
        Initialize info modal

        Args:
            app_name: Current application name (rotates)
        """
        super().__init__()
        self.app_name = app_name

    def compose(self) -> ComposeResult:
        """Create modal layout per INFO_MODAL.md"""
        with Container(id="info-dialog"):
            # Title
            title = self._get_title()
            yield Static(title, id="title")

            # Tagline
            yield Static(TAGLINE, id="tagline")

            # Cowsay version
            yield Static(self._get_cowsay_version(), id="cowsay-version")

            # Info content - formatted with right-aligned labels
            info_text = """        Maintainers:  Andrew Potozniak <potozniak@redhat.com>
                      John Mitchell <jmitchel@redhat.com>
                      John Barker <jobarker@redhat.com>
                      Daniel Brennand <dbrenuk@redhat.com>
            License:  MIT
                AIA:  EAI Hin R Claude Code [Sonnet, Opus] v1.0
         Repository:  github.com/ansible-community/awx-tui

"""
            yield Static(info_text, id="info-content")

            # Close button
            with Vertical(id="button-container"):
                yield Button("Close", variant="primary", id="close-button")

    def _get_title(self) -> str:
        """Get title with rotating name"""
        # If name already contains "TUI", use it as-is
        if "TUI" in self.app_name:
            return self.app_name
        # Otherwise format as "AWX TUI - [Name] Edition"
        return f"AWX TUI - {self.app_name} Edition"

    def _get_cowsay_version(self) -> str:
        """Generate cowsay output with version info, or fallback ASCII art"""
        # version_text = f"Version: {__version__}\nReleased: 2026-02-01"  # Unused for now

        return f"""                     _______________________________
                    /  Version: {__version__}           \\
                    \\ Released: 2026-02-01           /
                     -------------------------------
                            \\   ^__^
                             \\  (oo)\\_______
                                (__)\\       )\\/\\
                                    ||----w |
                                    ||     ||"""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        self.dismiss()

    def action_dismiss(self) -> None:
        """Dismiss the modal"""
        self.dismiss()
