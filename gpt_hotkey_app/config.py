"""Application configuration loading using environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    """Container for configuration values required by the application."""

    openai_api_key: str
    openai_model: str
    system_prompt: str
    request_timeout: float
    log_level: str


def load_config(dotenv_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from environment variables.

    Args:
        dotenv_path: Optional path to a .env file. When omitted, the default
            python-dotenv lookup rules apply.

    Returns:
        The populated :class:`AppConfig` instance.
    """

    if dotenv_path is not None:
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a concise helpful assistant.")
    request_timeout = float(os.getenv("REQUEST_TIMEOUT", "30"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    return AppConfig(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        system_prompt=system_prompt,
        request_timeout=request_timeout,
        log_level=log_level,
    )
