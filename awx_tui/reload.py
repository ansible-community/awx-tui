"""
Hot Reload Support for Development Mode

This module provides hot reload functionality for development only.
All hot reload logic is isolated here to keep app.py clean.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from textual.app import App


# Hot reload state file path
HOT_RELOAD_STATE_FILE = Path("/tmp/awx-tui-hot-reload-state.json")


class HotReloadManager:
    """
    Manages hot reload state persistence and screen restoration.

    Only active when app is running in dev mode (textual run --dev).
    """

    def __init__(self, app: "App"):
        """
        Initialize hot reload manager.

        Args:
            app: The Textual app instance
        """
        import os

        self.app = app

        # Check both app.dev and AWX_TUI_DEV environment variable
        self._enabled = getattr(app, "dev", False) or os.environ.get("AWX_TUI_DEV", "").lower() == "true"

        # Auto-start periodic save if enabled
        if self._enabled:
            self.app.set_timer(2.0, self._periodic_save)

    def is_enabled(self) -> bool:
        """Check if hot reload is enabled (dev mode)."""
        return self._enabled

    def _periodic_save(self) -> None:
        """Periodically save hot reload state."""
        self.save_state()
        # Schedule next save in 2 seconds
        self.app.set_timer(2.0, self._periodic_save)

    def save_state(self) -> None:
        """Save current screen state for hot reload restoration."""
        if not self._enabled:
            return

        try:
            # Check if app is mounted and has a screen
            if not hasattr(self.app, "screen") or not self.app.screen:
                return

            current_screen = self.app.screen
            screen_class_name = current_screen.__class__.__name__

            # Get current instance name if available
            current_instance = None
            if hasattr(self.app, "instance_manager") and self.app.instance_manager:
                current_instance = self.app.instance_manager.current_instance

            # Save state to file
            state = {
                "screen_class": screen_class_name,
                "current_instance": current_instance,
            }

            with open(HOT_RELOAD_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)

        except Exception:
            # Silently fail - don't spam logs with hot reload errors
            pass

    async def try_restore_screen(self) -> None:
        """
        Attempt to restore screen from hot reload state file.

        This method pushes the restored screen on top of the current screen stack.
        Should be called after the base screen (InstanceSelectionScreen) is pushed.
        """
        if not self._enabled:
            return

        try:
            if not HOT_RELOAD_STATE_FILE.exists():
                return

            # Read state file
            async with await anyio.open_file(HOT_RELOAD_STATE_FILE, "r") as f:
                state = await json.load(f)

            screen_class_name = state.get("screen_class")
            if not screen_class_name:
                return

            # Don't restore InstanceSelectionScreen (it's already pushed as base)
            if screen_class_name == "InstanceSelectionScreen":
                return

            # Restore current instance if available
            current_instance = state.get("current_instance")
            if current_instance and hasattr(self.app, "instance_manager") and self.app.instance_manager:
                # Set the current instance before restoring the screen
                self.app.instance_manager.current_instance = current_instance

            # Build screen map dynamically by discovering all screen modules
            screen_map = self._build_screen_map()

            if screen_class_name not in screen_map:
                self.app.log.warning(f"Unknown screen class for hot reload: {screen_class_name}")
                return

            module_path, class_name, kwargs = screen_map[screen_class_name]

            # Import and instantiate the screen
            import importlib

            module = importlib.import_module(module_path)
            screen_class = getattr(module, class_name)
            restored_screen = screen_class(**kwargs)

            # Push the restored screen on top of instance selection
            await self.app.push_screen(restored_screen)

        except Exception as e:
            self.app.log.error(f"Failed to restore hot reload screen: {e}")
            # If restoration fails, user will just see instance selection (which is fine)

    def _build_screen_map(self) -> dict:
        """
        Dynamically build a map of screen class names to their module paths.

        Returns:
            dict: Mapping of class names to (module_path, class_name, kwargs) tuples
        """
        import importlib
        import pkgutil
        from pathlib import Path

        from textual.screen import Screen

        screen_map = {}

        # Scan multiple directories: screens and dashboards
        scan_locations = [
            ("awx_tui.screens", Path(__file__).parent / "screens"),
            ("awx_tui.dashboards", Path(__file__).parent / "dashboards"),
        ]

        for package_name, package_path in scan_locations:
            # Skip if directory doesn't exist
            if not package_path.exists():
                continue

            # Iterate over all modules in the directory
            for _importer, module_name, _is_pkg in pkgutil.iter_modules([str(package_path)]):
                # Skip __init__.py and non-Python files
                if module_name.startswith("_"):
                    continue

                full_module_path = f"{package_name}.{module_name}"

                try:
                    # Import the module
                    module = importlib.import_module(full_module_path)

                    # Find all Screen subclasses in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)

                        # Check if it's a class and inherits from Screen
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, Screen)
                            and attr is not Screen
                            and attr.__module__ == full_module_path
                        ):  # Only classes defined in this module

                            # Add to screen map
                            screen_map[attr_name] = (full_module_path, attr_name, {})

                except Exception as e:
                    # Log but don't fail if a module can't be imported
                    self.app.log.warning(f"Could not import screen module {full_module_path}: {e}")
                    continue

        return screen_map
