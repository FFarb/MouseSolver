"""Core workflow orchestration for the GPT hotkey application."""
from __future__ import annotations

import logging
import threading
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

    def run_ocr_region_select(self) -> None:
        """Trigger the screen region OCR workflow in a background worker."""
        if self._stop_event.is_set():
            self._logger.debug("Trigger ignored because stop event is set")
            return

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
        self._logger.info("F10 pressed — region selection for object discovery")
        self._tray.notify("Select area for object discovery...")
        bbox = select_screen_region()

        if not bbox:
            self._logger.info("Region selection canceled or timed out")
            self._tray.notify("Selection canceled")
            return

        self._logger.info("Selected region for object discovery: %s", bbox)
        self._tray.notify("Detecting objects in selected region...")

        try:
            img = capture_region_image(bbox)
            detections = detect_objects_pil(img)
            if not detections:
                self._logger.warning("No objects found in selection")
                self._tray.notify("No objects found")
                return

            self._logger.info("Detected %d objects", len(detections))
            self._tray.notify(f"{len(detections)} objects detected")
            show_annotation_preview(img, detections)
        except Exception as e:
            self._logger.exception("Error during object discovery pipeline")
            self._tray.notify(f"F10 error: {e}")
        finally:
            with self._future_lock:
                self._current_future = None

    def _run_ocr_region_once(self) -> None:
        self._logger.info("F9 pressed — starting screen region OCR")
        self._tray.notify("Select area (ESC to cancel)...")
        bbox = select_screen_region()

        if not bbox:
            self._logger.info("Region selection canceled or timed out")
            self._tray.notify("Region selection canceled")
            return

        self._logger.info("Selected region: %s", bbox)
        self._tray.notify("Analyzing selected region...")

        try:
            text = extract_text_from_region(bbox)
            if not text.strip():
                self._logger.warning("No readable text found in selection")
                self._tray.notify("No readable text in selection")
                return

            self._logger.info("OCR extracted %d characters from region", len(text))
            reply = ask_gpt(
                system=self._config.system_prompt,
                user=text,
                model=self._config.openai_model,
                timeout=self._config.request_timeout,
            )
            write_clipboard_text(reply)
            self._logger.info("OCR region response written to clipboard (%d chars)", len(reply))
            self._tray.notify(f"OCR → GPT: response copied ({len(reply)} chars)")
        except Exception as e:
            self._logger.exception("Error during screen region OCR pipeline")
            self._tray.notify(f"OCR region error: {e}")
        finally:
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
