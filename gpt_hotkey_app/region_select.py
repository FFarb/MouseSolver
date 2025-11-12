"""A lightweight, cross-platform screen region selection tool using Tkinter."""
from __future__ import annotations

import tkinter as tk
from typing import Tuple


def select_screen_region(timeout_ms: int = 15000) -> Tuple[int, int, int, int] | None:
    """Show a translucent full-screen overlay to select a screen region.

    Args:
        timeout_ms: The maximum time in milliseconds to wait for the user.

    Returns:
        A tuple of (x1, y1, x2, y2) screen coordinates, or None if canceled.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    selector = _RegionSelector(root, timeout_ms)
    root.mainloop()

    return selector.get_bbox()


class _RegionSelector:
    """Manages the region selection overlay."""

    def __init__(self, master: tk.Tk, timeout_ms: int) -> None:
        self._master = master
        self._bbox: tuple[int, int, int, int] | None = None
        self._start_x = 0
        self._start_y = 0

        # Create a top-level window for the overlay
        self._overlay = tk.Toplevel(master)
        self._overlay.attributes("-fullscreen", True)
        self._overlay.attributes("-alpha", 0.2)  # Translucency
        self._overlay.attributes("-topmost", True)
        self._overlay.overrideredirect(True)  # No window decorations
        self._overlay.config(cursor="crosshair")

        self._canvas = tk.Canvas(self._overlay, highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._rect = self._canvas.create_rectangle(0, 0, 0, 0, outline="red", width=2, dash=(10, 10))

        # Bind events
        self._overlay.bind("<ButtonPress-1>", self._on_mouse_down)
        self._overlay.bind("<B1-Motion>", self._on_mouse_drag)
        self._overlay.bind("<ButtonRelease-1>", self._on_mouse_up)
        self._overlay.bind("<Escape>", self._on_cancel)

        # Set a timer to automatically close the overlay
        self._master.after(timeout_ms, self._on_timeout)

    def get_bbox(self) -> tuple[int, int, int, int] | None:
        """Return the selected bounding box."""
        return self._bbox

    def _on_mouse_down(self, event: tk.Event) -> None:
        self._start_x = event.x_root
        self._start_y = event.y_root
        self._canvas.coords(self._rect, self._start_x, self._start_y, self._start_x, self._start_y)

    def _on_mouse_drag(self, event: tk.Event) -> None:
        self._canvas.coords(self._rect, self._start_x, self._start_y, event.x_root, event.y_root)

    def _on_mouse_up(self, event: tk.Event) -> None:
        x1, y1 = self._start_x, self._start_y
        x2, y2 = event.x_root, event.y_root

        # Normalize coordinates
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        if max_x - min_x >= 5 and max_y - min_y >= 5:
            self._bbox = (min_x, min_y, max_x, max_y)

        self._close()

    def _on_cancel(self, event: tk.Event | None = None) -> None:
        self._bbox = None
        self._close()

    def _on_timeout(self) -> None:
        self._on_cancel()

    def _close(self) -> None:
        self._master.quit()
        self._overlay.destroy()
