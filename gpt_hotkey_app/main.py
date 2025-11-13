"""Entry point for the GPT hotkey Windows application."""
from __future__ import annotations

import ctypes
import logging
import platform
import threading
import time
from pathlib import Path
from typing import Optional

import keyboard

from .config import load_config
from .hotkeys import HotkeyManager
from .logger import setup_logging
from .preview_ui import ensure_ui_thread, process_ui_events
from .runner import Runner
from .single_instance import ensure_single_instance
from .tray import TrayManager


def detach_console_if_needed() -> None:
    """If on Windows, detach from the console."""
    if platform.system() == "Windows":
        try:
            ctypes.windll.kernel32.FreeConsole()
        except Exception:
            pass


def run_app() -> bool:
    """Run the application once.

    Returns:
        True if the user requested a clean exit (F12).
        False if the app stopped unexpectedly and should be restarted.
    """
    detach_console_if_needed()
    should_exit = False

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass  # Ignore for non-Windows systems

    ensure_ui_thread()

    config = load_config()
    log_dir = Path.cwd()
    logger = setup_logging(config.log_level, log_dir)
    app_instance = None

    try:
        logger.info("Application starting")
        app_instance = ensure_single_instance(logger=logger)

        stop_event = threading.Event()
        tray_manager = TrayManager(on_exit=stop_event.set, logger=logger)
        tray_manager.start()

        if not config.openai_api_key:
            msg = "OPENAI_API_KEY missing. Application will exit."
            logger.error(msg)
            tray_manager.notify(msg)
            time.sleep(2)
            tray_manager.stop()
            return True

        runner = Runner(config, tray_manager, stop_event, logger)
        hotkeys: Optional[HotkeyManager] = None

        def on_exit() -> None:
            nonlocal should_exit
            if stop_event.is_set():
                return
            should_exit = True
            logger.info("Shutdown requested")
            stop_event.set()
            tray_manager.notify("Shutting down...")
            if hotkeys:
                hotkeys.unregister()
            runner.shutdown()
            tray_manager.stop()
            keyboard.clear_all_hotkeys()

        hotkeys = HotkeyManager(
            on_trigger=runner.trigger,
            on_ocr_region=runner.run_ocr_region_select,
            on_ocr_window=runner.run_ocr_pipeline,
            on_object_discovery=runner.run_region_object_discovery,
            on_exit=on_exit,
            logger=logger,
        )
        hotkeys.register()
        tray_manager.set_exit_callback(on_exit)
        tray_manager.notify("GPT Hotkey running (F8, F9, F10, F12 to exit)")

        while not stop_event.is_set():
            process_ui_events()
            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        on_exit()
    except Exception as e:
        logger.exception("Fatal error in app.run(): %s", e)
        return False  # Indicate crash
    finally:
        if "on_exit" in locals() and not stop_event.is_set():
            on_exit()
        if app_instance:
            app_instance.close()
        logger.info("Application terminated")

    return should_exit


def main() -> None:
    """Original entry point for direct execution."""
    run_app()


if __name__ == "__main__":
    main()
