"""Entry point for the GPT hotkey Windows application."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import List, Optional

import keyboard
import psutil

from .client_openai import OpenAIChatClient
from .config import load_config
from .hotkeys import HotkeyManager
from .logger import setup_logging
from .runner import Runner
from .tray import TrayManager

APP_IDENTIFIER = "GPT-Hotkey"


def ensure_single_instance(identifiers: List[str], logger: logging.Logger) -> bool:
    """Ensure only one instance of the application is running."""
    try:
        current = psutil.Process()
        for proc in psutil.process_iter(["pid", "cmdline"]):
            if proc.pid == current.pid:
                continue
            cmdline = proc.info.get("cmdline") or []
            merged = " ".join(cmdline)
            if any(identifier and identifier in merged for identifier in identifiers):
                logger.error("Another instance of the application is already running")
                return False
    except psutil.Error as exc:
        logger.warning("Unable to verify single instance: %s", exc)
    return True


def _exit_application(
    stop_event: threading.Event,
    hotkeys: HotkeyManager,
    runner: Runner,
    tray: TrayManager,
    logger: logging.Logger,
) -> None:
    if stop_event.is_set():
        return
    logger.info("Shutdown requested")
    stop_event.set()
    tray.notify("Shutting down...")
    hotkeys.unregister()
    runner.shutdown()
    tray.stop()
    keyboard.clear_all_hotkeys()


def main() -> None:
    """Application entry point."""
    config = load_config()
    log_dir = Path.cwd()
    logger = setup_logging(config.log_level, log_dir)
    logger.info("Application starting")

    identifier_candidates = [APP_IDENTIFIER, Path(__file__).stem]
    if not ensure_single_instance(identifier_candidates, logger):
        logger.error("Application already running; exiting")
        return

    stop_event = threading.Event()

    tray_manager = TrayManager(on_exit=lambda: stop_event.set(), logger=logger)
    tray_manager.start()

    if not config.openai_api_key:
        message = "OPENAI_API_KEY missing. Application will exit."
        logger.error(message)
        tray_manager.notify(message)
        time.sleep(2)
        tray_manager.stop()
        return

    client = OpenAIChatClient(config, logger)
    runner = Runner(client, tray_manager, stop_event, logger)
    hotkeys: Optional[HotkeyManager] = None

    def on_exit() -> None:
        if stop_event.is_set():
            return
        if hotkeys is None:
            stop_event.set()
            runner.shutdown()
            tray_manager.stop()
            keyboard.clear_all_hotkeys()
            return
        _exit_application(stop_event, hotkeys, runner, tray_manager, logger)

    hotkeys = HotkeyManager(on_trigger=runner.trigger, on_exit=on_exit, logger=logger)
    hotkeys.register()
    tray_manager.set_exit_callback(on_exit)

    tray_manager.notify("GPT Hotkey running (F8 to query, F12 to exit)")

    try:
        while not stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        on_exit()
    finally:
        if not stop_event.is_set():
            on_exit()
        logger.info("Application terminated")


if __name__ == "__main__":
    main()
