"""Utilities for retrieving selected text from the active window."""
from __future__ import annotations

import random
import time
from typing import Optional

import keyboard

from .clipboard_io import read_clipboard_text

WAIT_MIN_SECONDS = 0.05
WAIT_MAX_SECONDS = 0.15


def get_selected_text(previous_clipboard: str) -> Optional[str]:
    """Copy the currently selected text via simulated ``Ctrl+C``.

    Args:
        previous_clipboard: The clipboard content before triggering ``Ctrl+C``.

    Returns:
        The newly copied text, or ``None`` if the clipboard did not change.
    """

    keyboard.send("ctrl+c")
    time.sleep(random.uniform(WAIT_MIN_SECONDS, WAIT_MAX_SECONDS))
    current_clipboard = read_clipboard_text()
    if not current_clipboard or current_clipboard == previous_clipboard:
        return None
    return current_clipboard
