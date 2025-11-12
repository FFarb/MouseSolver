"""Core workflow orchestration for the GPT hotkey application."""
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

from .clipboard_io import snapshot_clipboard, write_clipboard_text
from .config import AppConfig
from .openai_client import ask_gpt
from .selection import get_selected_text


class Runner:
    """Handles the workflow when the trigger hotkey is activated."""

    def __init__(
        self,
        config: AppConfig,
        tray,
        stop_event: threading.Event,
        logger: logging.Logger,
    ) -> None:
        self._config = config
        self._tray = tray
        self._stop_event = stop_event
        self._logger = logger
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="runner")
        self._future_lock = threading.Lock()
        self._current_future: Optional[Future] = None

    def trigger(self) -> None:
        """Trigger the workflow in a background worker thread."""
        if self._stop_event.is_set():
            self._logger.debug("Trigger ignored because stop event is set")
            return

        with self._future_lock:
            if self._current_future and not self._current_future.done():
                self._logger.info("Processing already in progress; ignoring new trigger")
                self._tray.notify("Processing already in progress")
                return
            self._current_future = self._executor.submit(self._run_once)

    def shutdown(self) -> None:
        """Shutdown the executor and wait for active jobs to finish."""
        self._logger.debug("Shutting down runner executor")
        with self._future_lock:
            if self._current_future:
                self._current_future.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run_once(self) -> None:
        self._logger.info("Hotkey trigger received; starting workflow")
        snapshot = snapshot_clipboard()
        previous_content = snapshot.content

        try:
            if self._stop_event.is_set():
                self._logger.debug("Stop event set before selection; aborting")
                snapshot.restore()
                return

            selected_text = get_selected_text(previous_content)
            if not selected_text:
                self._logger.info("No new text detected on clipboard")
                snapshot.restore()
                self._tray.notify("No text selected")
                return

            self._logger.info("Selected text length: %d", len(selected_text))
            snapshot.restore()

            if self._stop_event.is_set():
                self._logger.debug("Stop event set before API call; aborting")
                return

            try:
                response = ask_gpt(
                    system=self._config.system_prompt,
                    user=selected_text,
                    model=self._config.openai_model,
                    timeout=self._config.request_timeout,
                )
            except Exception as exc:  # noqa: BLE001
                self._logger.exception("Error while calling OpenAI API")
                self._tray.notify(f"OpenAI error: {exc}")
                snapshot.restore()
                return

            if self._stop_event.is_set():
                self._logger.debug("Stop event set after API call; aborting clipboard write")
                return

            write_clipboard_text(response)
            self._logger.info("Response written to clipboard (%d chars)", len(response))
            self._tray.notify(f"Response copied to clipboard ({len(response)} chars)")
        finally:
            with self._future_lock:
                self._current_future = None
