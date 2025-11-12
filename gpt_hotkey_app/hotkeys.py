"""Global hotkey registration using the keyboard package."""
from __future__ import annotations

import logging
from typing import Callable, List

import keyboard


class HotkeyManager:
    """Registers and manages global hotkeys for the application."""

    def __init__(
        self,
        on_trigger: Callable[[], None],
        on_exit: Callable[[], None],
        logger: logging.Logger,
    ) -> None:
        self._on_trigger = on_trigger
        self._on_exit = on_exit
        self._logger = logger
        self._hotkey_refs: List[int] = []

    def register(self) -> None:
        """Register F8 and F12 hotkeys."""
        self._logger.info("Registering hotkeys F8 and F12")
        trigger_ref = keyboard.add_hotkey("F8", self._handle_trigger)
        exit_ref = keyboard.add_hotkey("F12", self._handle_exit)
        self._hotkey_refs = [trigger_ref, exit_ref]

    def unregister(self) -> None:
        """Unregister previously registered hotkeys."""
        self._logger.info("Unregistering hotkeys")
        for ref in self._hotkey_refs:
            keyboard.remove_hotkey(ref)
        self._hotkey_refs.clear()

    def _handle_trigger(self) -> None:
        self._logger.debug("F8 pressed")
        self._on_trigger()

    def _handle_exit(self) -> None:
        self._logger.debug("F12 pressed")
        self._on_exit()
