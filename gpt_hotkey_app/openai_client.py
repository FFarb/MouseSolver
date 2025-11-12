"""Wrapper around the OpenAI Responses API."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, Any

from openai import OpenAI, APIError
from .config import load_config

_config = load_config()


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Return a singleton OpenAI client instance."""
    return OpenAI(api_key=_config.openai_api_key)


def ask_gpt(system: str, user: str, *, model: str | None = None, timeout: int | None = None) -> str:
    """
    Sends a request to the OpenAI Responses API and returns the text from the first output item.

    Args:
        system: The system prompt.
        user: The user prompt.
        model: The model to use (defaults to gpt-5).
        timeout: The request timeout in seconds.

    Returns:
        The text content of the response.

    Raises:
        RuntimeError: If the API response is missing the expected content.
    """
    client = get_openai_client()
    model_to_use = model or _config.openai_model or "gpt-5"
    request_timeout = timeout or _config.request_timeout

    logging.info("Sending request to OpenAI model '%s' with timeout %s", model_to_use, request_timeout)

    try:
        resp = client.responses.create(
            model=model_to_use,
            reasoning={"effort": "low"},
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout=request_timeout,
        )

        if hasattr(resp, "output_text") and resp.output_text:
            return resp.output_text

        for item in getattr(resp, "output", []):
            if item.get("type") == "message":
                parts = item.get("content", [])
                for p in parts:
                    if p.get("type") == "output_text" and "text" in p:
                        return p["text"]
                    if p.get("type") in ("text", "output_text") and "text" in p:
                        return p["text"]

        raise RuntimeError("No text content in model response.")
    except APIError as e:
        logging.exception("OpenAI API error: %s", e)
        raise RuntimeError(f"OpenAI API error: {e}") from e
