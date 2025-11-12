"""Ensures that only one instance of the application is running."""
from __future__ import annotations

import logging
import socket
import sys

_sock = None  # noqa: RUF012


def ensure_single_instance(port: int = 51234, logger: logging.Logger | None = None) -> None:
    """Ensure only one instance of the application is running.

    This is achieved by binding to a specific TCP port. If the port is already
    in use, it's assumed another instance is running, and the application exits.

    The socket is stored in a global variable to prevent it from being garbage
    collected, which would release the lock.

    Args:
        port: The port number to use for the lock.
        logger: An optional logger to record messages.
    """
    global _sock
    _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _sock.bind(("127.0.0.1", port))
    except OSError as e:
        if logger:
            logger.error("Another instance is already running (port %d is in use).", port)
        else:
            print(f"Another instance is already running (port {port} is in use). Error: {e}", file=sys.stderr)
        sys.exit(1)
