"""
AWX TUI - Terminal User Interface for AWX

Rage Tater Edition - Multi-instance job monitoring and debugging

AI Attribution (AIA): EAI Hin R Claude Code v1.0
Model: Claude Sonnet 4.5
Vibe-Coder: Andrew Potozniak <potozniak@redhat.com>
"""

from importlib.metadata import version

__version__ = version("awx-tui")
__author__ = "Andrew Potozniak"
__email__ = "potozniak@redhat.com"
__license__ = "MIT"

# Rotating application names (see ARCHITECTURE.md)
ROTATING_NAMES = [
    "AWX TUI",
    "Rage Tater Automation Interface",
    "The Angry Spud TUI",
    "Angry Automation Potato",
    "The Starchy API Front End",
]

TAGLINE = "Automation at Your Fingertips"
