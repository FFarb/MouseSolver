from __future__ import annotations
import queue
import threading
import tkinter as tk
from typing import Any, Callable, Tuple

# Singleton UI thread for Tk
_UI_THREAD: threading.Thread | None = None
_UI_ROOT: tk.Tk | None = None
_JOBS: "queue.Queue[Tuple[Callable[..., Any], tuple, dict, threading.Event, list[Any]]]" = queue.Queue()


def _ui_loop() -> None:
    global _UI_ROOT
    _UI_ROOT = tk.Tk()
    _UI_ROOT.withdraw()  # hidden root
    _UI_ROOT.title("HiddenRoot")

    def pump() -> None:
        try:
            while True:
                try:
                    func, args, kwargs, done_evt, out_box = _JOBS.get_nowait()
                except queue.Empty:
                    break
                try:
                    res = func(*args, **kwargs)
                    out_box.append(res)
                except Exception as exc:  # pragma: no cover - passthrough
                    out_box.append(exc)
                finally:
                    done_evt.set()
        finally:
            _UI_ROOT.after(15, pump)

    _UI_ROOT.after(15, pump)
    _UI_ROOT.mainloop()


def ensure_ui_thread() -> None:
    global _UI_THREAD
    if _UI_THREAD and _UI_THREAD.is_alive():
        return
    _UI_THREAD = threading.Thread(target=_ui_loop, name="TkUI", daemon=True)
    _UI_THREAD.start()


def call_on_ui_thread(func: Callable[..., Any], *args, **kwargs) -> Any:
    """Synchronously run func on the Tk UI thread. Returns func() result or raises if func raised."""
    ensure_ui_thread()
    done = threading.Event()
    out: list[Any] = []
    _JOBS.put((func, args, kwargs, done, out))
    done.wait()
    if out and isinstance(out[0], Exception):
        raise out[0]
    return out[0] if out else None


def get_root() -> tk.Tk:
    ensure_ui_thread()
    while _UI_ROOT is None:
        pass
    return _UI_ROOT
