"""Entry point for the GPT hotkey Windows application."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

import keyboard

from .config import load_config
from .hotkeys import HotkeyManager
from .logger import setup_logging
from .runner import Runner
from .single_instance import ensure_single_instance
from .tray import TrayManager


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

    ensure_single_instance(logger=logger)

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

    runner = Runner(config, tray_manager, stop_event, logger)
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
