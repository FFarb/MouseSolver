from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Any, Callable, Tuple

# Tk must live on the main thread on Windows.  We therefore build a singleton
# dispatcher that executes jobs on the main thread while allowing worker
# threads to synchronously queue work.

_UI_ROOT: tk.Tk | None = None
_ROOT_READY = threading.Event()
_INIT_LOCK = threading.Lock()
_JOBS: "queue.Queue[Tuple[Callable[..., Any], tuple, dict, threading.Event, list[Any]]]" = queue.Queue()


def _init_root_locked() -> None:
    global _UI_ROOT
    if _UI_ROOT is not None:
        return
    root = tk.Tk()
    root.withdraw()  # hidden root
    root.title("HiddenRoot")
    _UI_ROOT = root
    _ROOT_READY.set()


def ensure_ui_thread() -> None:
    """Ensure the hidden Tk root exists on the main thread."""
    if _ROOT_READY.is_set():
        return
    if threading.current_thread() is not threading.main_thread():
        # Wait for the main thread to perform the initialisation.
        _ROOT_READY.wait()
        return
    with _INIT_LOCK:
        if not _ROOT_READY.is_set():
            _init_root_locked()


def _drain_jobs() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("_drain_jobs must run on the main thread")

    ensure_ui_thread()
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
        root = _UI_ROOT
        if root is None:
            return
        try:
            root.update_idletasks()
            root.update()
        except tk.TclError:
            # The root may be in the process of shutting down. Ignore.
            pass


def process_ui_events() -> None:
    """Process any pending Tk events and queued dispatcher jobs."""
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("process_ui_events must be called from the main thread")
    if not _ROOT_READY.is_set():
        ensure_ui_thread()
        if not _ROOT_READY.is_set():
            return
    _drain_jobs()


def call_on_ui_thread(func: Callable[..., Any], *args, **kwargs) -> Any:
    """Synchronously run *func* on the Tk UI thread."""
    ensure_ui_thread()
    if threading.current_thread() is threading.main_thread():
        return func(*args, **kwargs)

    done = threading.Event()
    out: list[Any] = []
    _JOBS.put((func, args, kwargs, done, out))
    done.wait()
    if out and isinstance(out[0], Exception):
        raise out[0]
    return out[0] if out else None


def get_root() -> tk.Tk:
    ensure_ui_thread()
    _ROOT_READY.wait()
    assert _UI_ROOT is not None
    return _UI_ROOT
