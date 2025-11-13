# gpt_hotkey_app/launcher.py
from __future__ import annotations
import time, logging
from .main import run_app  # you may need to expose a function in main.py

logger = logging.getLogger("gpt_hotkey_app.launcher")

def main():
    """
    Watchdog loop:
      - starts the main app
      - if it exits unexpectedly (error), logs and restarts
      - if it exits with a "should_exit" flag (F12), stops
    """
    while True:
        try:
            logger.info("Launching main app loop")
            should_exit = run_app()  # bool: True = user-requested exit
            if should_exit:
                logger.info("Main app requested clean exit (F12); stopping watchdog")
                break
            else:
                logger.warning("Main app stopped unexpectedly; restarting in 2 seconds...")
                time.sleep(2.0)
        except Exception as e:
            logger.exception("Unhandled exception in main loop: %s", e)
            logger.warning("Restarting after crash in 5 seconds...")
            time.sleep(5.0)

if __name__ == "__main__":
    main()
