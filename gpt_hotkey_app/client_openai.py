"""Wrapper around the OpenAI Chat Completion API."""
from __future__ import annotations

import logging

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
)

from .config import AppConfig


class OpenAIChatClient:
    """Encapsulates interactions with the OpenAI chat completions endpoint."""

    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self._logger = logger
        self._model = config.openai_model
        self._system_prompt = config.system_prompt
        self._timeout = config.request_timeout
        self._client = OpenAI(api_key=config.openai_api_key)

    def chat(self, user_content: str) -> str:
        """Send the selected text to the model and return its response."""
        self._logger.info("Sending request to OpenAI model '%s'", self._model)
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_content},
                ],
                timeout=self._timeout,
            )
        except (APIConnectionError, APIError, APITimeoutError, AuthenticationError, OpenAIError) as exc:
            self._logger.error("OpenAI API error: %s", exc, exc_info=True)
            raise

        message: str = ""
        if response.choices:
            content = response.choices[0].message.content
            if isinstance(content, list):
                message = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            elif content is not None:
                message = str(content)

        if not message:
            self._logger.warning("Empty response received from OpenAI")
            return ""
        self._logger.info("Received response with %d characters", len(message))
        return message
