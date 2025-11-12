"""System tray icon management using pystray."""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from PIL import Image, ImageDraw
import pystray


class TrayManager:
    """Manage the system tray icon, menu, and notifications."""

    def __init__(self, on_exit: Callable[[], None], logger: logging.Logger) -> None:
        self._on_exit = on_exit
        self._logger = logger
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._create_icon()

    def _create_icon(self) -> None:
        image = Image.new("RGB", (64, 64), color=(30, 30, 30))
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill=(86, 170, 255))
        menu = pystray.Menu(
            pystray.MenuItem("Running", lambda icon, item: None, enabled=False),
            pystray.MenuItem("Exit (F12)", lambda icon, item: self._handle_exit()),
        )
        self._icon = pystray.Icon("GPT-Hotkey", image, "GPT Hotkey", menu)

    def start(self) -> None:
        """Start the tray icon in a background thread."""
        if self._icon is None:
            raise RuntimeError("Tray icon not initialized")
        if self._thread and self._thread.is_alive():
            return

        def run_icon() -> None:
            self._logger.debug("Starting tray icon thread")
            assert self._icon is not None
            self._icon.run()

        self._thread = threading.Thread(target=run_icon, name="tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the tray icon if it is running."""
        if self._icon is not None:
            self._logger.debug("Stopping tray icon")
            self._icon.stop()
        if self._thread:
            self._thread.join(timeout=2)

    def notify(self, message: str) -> None:
        """Show a system notification via the tray icon."""
        if self._icon is None:
            self._logger.warning("Tray notification requested before icon initialization")
            return
        self._logger.info("Tray notification: %s", message)
        try:
            self._icon.notify(message)
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Unable to show tray notification: %s", exc, exc_info=True)

    def set_exit_callback(self, callback: Callable[[], None]) -> None:
        """Update the callback invoked when the user chooses Exit."""
        self._on_exit = callback

    def _handle_exit(self) -> None:
        self._logger.debug("Tray menu exit selected")
        self._on_exit()
