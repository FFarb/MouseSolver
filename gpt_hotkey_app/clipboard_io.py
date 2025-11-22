"""Clipboard helpers using pyperclip."""
from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

import pyperclip

_CLIPBOARD_LOCK = threading.Lock()


@dataclass
class ClipboardSnapshot:
    """Represents a snapshot of the clipboard that can be restored."""

    content: str
    restored: bool = False

    def restore(self) -> None:
        """Restore the clipboard to the snapshot's content if not already done."""
        if not self.restored:
            write_clipboard_text(self.content)
            self.restored = True


def read_clipboard_text() -> str:
    """Return text from the clipboard or an empty string if unavailable."""
    with _CLIPBOARD_LOCK:
        try:
            value = pyperclip.paste()
        except pyperclip.PyperclipException:
            return ""
    if value is None:
        return ""
    return str(value)


def write_clipboard_text(text: str) -> None:
    """Write text to the clipboard in a thread-safe manner."""
    with _CLIPBOARD_LOCK:
        pyperclip.copy(text if text is not None else "")


def snapshot_clipboard() -> ClipboardSnapshot:
    """Capture the current clipboard contents for later restoration."""
    return ClipboardSnapshot(content=read_clipboard_text())


@contextmanager
def preserve_clipboard() -> Generator[ClipboardSnapshot, None, None]:
    """Context manager that snapshots and restores the clipboard."""
    snapshot = snapshot_clipboard()
    try:
        yield snapshot
    finally:
        snapshot.restore()
