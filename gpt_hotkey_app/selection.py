"""Utilities for retrieving selected text from the active window."""
from __future__ import annotations

import logging
import random
import time
from typing import Optional

import keyboard
import win32con
import win32gui
from.clipboard_io import read_clipboard_text

WAIT_MIN_SECONDS = 0.05
WAIT_MAX_SECONDS = 0.15

_logger = logging.getLogger(__name__)


def get_selected_text_invisible() -> Optional[str]:
    """Try to get the selected text by sending a WM_COPY message."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            _logger.warning("No foreground window found.")
            return None

        # Send WM_COPY message to the window
        win32gui.SendMessage(hwnd, win32con.WM_COPY)
        time.sleep(random.uniform(WAIT_MIN_SECONDS, WAIT_MAX_SECONDS))
        return read_clipboard_text()
    except Exception as e:
        _logger.error(f"Failed to get selected text invisibly: {e}")
        return None


def get_selected_text_visible(previous_clipboard: str) -> Optional[str]:
    """Copy the currently selected text via simulated Ctrl+C."""
    keyboard.send("ctrl+c")
    time.sleep(random.uniform(WAIT_MIN_SECONDS, WAIT_MAX_SECONDS))
    current_clipboard = read_clipboard_text()
    if not current_clipboard or current_clipboard == previous_clipboard:
        return None
    return current_clipboard


def get_selected_text(previous_content: str) -> Optional[str]:
    """
    Get the selected text, trying the invisible method first and falling back
    to the visible method.
    """
    selected_text = get_selected_text_invisible()

    if not selected_text or selected_text == previous_content:
        _logger.info("Invisible selection failed, falling back to visible method.")
        selected_text = get_selected_text_visible(previous_content)

    return selected_text
