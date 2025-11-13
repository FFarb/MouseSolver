"""Core workflow orchestration for the GPT hotkey application."""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

from .clipboard_io import snapshot_clipboard, write_clipboard_text
from .config import AppConfig
from .object_detection import detect_objects_pil
from .ocr import (
    capture_region_image,
    extract_text_from_active_window,
    extract_text_from_region,
)
from .openai_client import ask_gpt
from .preview import show_annotation_preview
from .region_select import select_screen_region
from .selection import get_selected_text
from .text_detection import detect_text_boxes


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
        self._busy_f9 = threading.Event()
        self._last_f9_ts = 0.0

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

    def run_ocr_region_select(self) -> None:
        """Trigger the screen region OCR workflow in a background worker."""
        now = time.monotonic()
        if now - self._last_f9_ts < 0.25:
            self._logger.info("F9 ignored (debounce)")
            return
        self._last_f9_ts = now

        if self._busy_f9.is_set():
            self.tray.notify("F9 is already running")
            self._logger.info("F9 suppressed: already running")
            return

        if self._stop_event.is_set():
            self._logger.debug("Trigger ignored because stop event is set")
            return

        # Use the generic lock to ensure only one task runs at a time
        with self._future_lock:
            if self._current_future and not self._current_future.done():
                self._logger.info("Processing already in progress; ignoring new trigger")
                self._tray.notify("Processing already in progress")
                return
            self._current_future = self._executor.submit(self._run_ocr_region_once)

    def run_region_object_discovery(self) -> None:
        """Trigger the region object discovery workflow in a background worker."""
        if self._stop_event.is_set():
            self._logger.debug("Trigger ignored because stop event is set")
            return

        with self._future_lock:
            if self._current_future and not self._current_future.done():
                self._logger.info("Processing already in progress; ignoring new trigger")
                self._tray.notify("Processing already in progress")
                return
            self._current_future = self._executor.submit(self._run_region_object_discovery_once)

    def run_ocr_pipeline(self) -> None:
        """Trigger the OCR workflow in a background worker thread."""
        if self._stop_event.is_set():
            self._logger.debug("Trigger ignored because stop event is set")
            return

        with self._future_lock:
            if self._current_future and not self._current_future.done():
                self._logger.info("Processing already in progress; ignoring new trigger")
                self._tray.notify("Processing already in progress")
                return
            self._current_future = self._executor.submit(self._run_ocr_once)

    def shutdown(self) -> None:
        """Shutdown the executor and wait for active jobs to finish."""
        self._logger.debug("Shutting down runner executor")
        with self._future_lock:
            if self._current_future:
                self._current_future.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run_region_object_discovery_once(self) -> None:
        """
        F10: select region -> detect objects (YOLO) + text (OCR) ->
        show annotated preview window.
        """
        try:
            self._logger.info("F10 pressed — region selection for object+text discovery")
            bbox = select_screen_region()
            if not bbox:
                self._tray.notify("Selection canceled")
                return

            img = capture_region_image(bbox)
            self._tray.notify("Detecting objects + text...")

            objects = detect_objects_pil(img, conf=0.3, iou=0.45)
            texts   = detect_text_boxes(img, min_conf=60)
            self._logger.info("Detections — objects: %d, text boxes: %d", len(objects), len(texts))

            if not objects and not texts:
                self._tray.notify("No objects or readable text found")
                return

            show_annotation_preview(img, objects, texts)
            self._tray.notify(f"Objects: {len(objects)} | Text: {len(texts)}")

        except Exception as e:
            self._logger.exception("F10 discovery error: %s", e)
            self._tray.notify(f"F10 error: {e}")
        finally:
            with self._future_lock:
                self._current_future = None

    def _run_ocr_region_once(self) -> None:
        self._busy_f9.set()
        self.logger.info("F9 start")
        try:
            bbox = select_screen_region()
            if not bbox:
                self.tray.notify("Selection canceled")
                self.logger.info("F9 selection canceled")
                return

            self.tray.notify("Analyzing selected region...")
            text = extract_text_from_region(bbox)
            if not text.strip():
                self.tray.notify("No readable text in selection")
                self.logger.info("F9: no OCR text")
                return

            reply = ask_gpt(
                system=self._config.system_prompt,
                user=text,
                model=self._config.openai_model,
                timeout=self._config.request_timeout,
            )
            write_clipboard_text(reply)
            self.tray.notify(f"OCR → GPT: response copied ({len(reply)} chars)")
            self.logger.info("F9 reply length: %d", len(reply))
        except Exception as e:
            self.logger.exception("F9 error: %s", e)
            self.tray.notify(f"F9 error: {e}")
        finally:
            self._busy_f9.clear()
            self.logger.info("F9 end")
            with self._future_lock:
                self._current_future = None

    def _run_ocr_once(self) -> None:
        self._logger.info("F9 pressed — capturing active window for OCR")
        self._tray.notify("GPT OCR mode active — analyzing screen text...")
        try:
            text = extract_text_from_active_window()
            if not text.strip():
                self._logger.warning("No readable text found on screen")
                self._tray.notify("No readable text found on screen")
                return

            self._logger.info("OCR extracted %d characters", len(text))
            reply = ask_gpt(
                system=self._config.system_prompt,
                user=text,
                model=self._config.openai_model,
                timeout=self._config.request_timeout,
            )
            write_clipboard_text(reply)
            self._logger.info("OCR response written to clipboard (%d chars)", len(reply))
            self._tray.notify(f"OCR analyzed — response copied ({len(reply)} chars)")
        except Exception as e:
            self._logger.exception("Error during OCR pipeline")
            self._tray.notify(f"OCR error: {e}")
        finally:
            with self._future_lock:
                self._current_future = None

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
