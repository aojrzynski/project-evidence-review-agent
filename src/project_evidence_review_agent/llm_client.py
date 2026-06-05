"""LLM client boundary for bounded claim review.

The default workflow can use an LLM, but deterministic package import and tests must
not require OpenAI. This module defines a small protocol that fake test clients can
implement and keeps the OpenAI import inside ``OpenAIReviewClient``. The production
client sends plain bounded prompt text through the Responses API without tools,
file uploads, function calling, streaming, web search, code interpreter, or MCP.
"""

from __future__ import annotations

import os
from typing import Protocol

DEFAULT_LLM_MODEL = "gpt-4.1-mini"


class LLMConfigurationError(RuntimeError):
    """Raised when LLM review is requested but no usable client is configured."""


class ReviewLLMClient(Protocol):
    """Protocol implemented by real and fake review clients."""

    def review_claims(self, prompt: str, *, model: str) -> str:
        """Return model text for a bounded claim-review prompt."""


class OpenAIReviewClient:
    """OpenAI Responses API wrapper for bounded claim review.

    The import is local so ``--no-llm`` and tests keep working without the optional
    dependency. The API key is checked before import so the CLI can give a clean
    deterministic-mode hint instead of a confusing stack trace.
    """

    def __init__(self) -> None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMConfigurationError(
                "OPENAI_API_KEY is not set. Install/configure the optional LLM "
                "client, or rerun with --no-llm for deterministic evidence-pack mode."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError(
                "The optional OpenAI package is not installed. Install with "
                "project-evidence-review-agent[llm], or rerun with --no-llm for "
                "deterministic evidence-pack mode."
            ) from exc
        self._client = OpenAI()

    def review_claims(self, prompt: str, *, model: str) -> str:
        """Call the Responses API with no tools and return output text."""

        response = self._client.responses.create(model=model, input=prompt)
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text
        return str(response)
