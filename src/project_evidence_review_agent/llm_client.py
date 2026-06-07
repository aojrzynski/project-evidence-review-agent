"""LLM client boundary for bounded claim and follow-up review.

The default workflow can use an LLM, but deterministic package import and tests must
not require OpenAI. This module defines a small protocol that fake test clients can
implement and keeps the OpenAI import inside ``OpenAIReviewClient``. The production
client sends plain bounded prompt text through the Responses API without tools,
file uploads, function calling, streaming, web search, code interpreter, or MCP.
"""

from __future__ import annotations

import os
from typing import Protocol

# A small default model keeps the example workflow practical; callers can
# override it with --llm-model without changing validation boundaries.
DEFAULT_LLM_MODEL = "gpt-4.1-mini"


class LLMConfigurationError(RuntimeError):
    """Raised when LLM review is requested but no usable client is configured."""


class ReviewLLMClient(Protocol):
    """Protocol implemented by real and fake review clients.

    The workflow depends on this protocol rather than a concrete OpenAI class so
    tests can inject deterministic fake clients and validation can be exercised
    without network access.
    """

    def review_claims(self, prompt: str, *, model: str) -> str:
        """Return model text for a bounded claim-review prompt."""

    def review_follow_up_analysis(self, prompt: str, *, model: str) -> str:
        """Return model text for bounded missing evidence/contradiction analysis."""


class OpenAIReviewClient:
    """OpenAI Responses API wrapper for bounded claim review.

    The import is local so ``--no-llm`` and tests keep working without the optional
    dependency. The API key is checked before import so the CLI can give a clean
    deterministic-mode hint instead of a confusing stack trace.
    """

    def __init__(self) -> None:
        if not os.environ.get("OPENAI_API_KEY"):
            # Check configuration explicitly so users get a deterministic-mode
            # hint instead of a low-level client error.
            raise LLMConfigurationError(
                "OPENAI_API_KEY is not set. Install/configure the optional LLM "
                "client, or rerun with --no-llm for deterministic evidence-pack mode."
            )
        try:
            # Keep the import local so package import, tests, and --no-llm runs
            # do not require the optional OpenAI dependency.
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

        return self._create_response(prompt, model=model)

    def review_follow_up_analysis(self, prompt: str, *, model: str) -> str:
        """Call the Responses API for bounded follow-up analysis with no tools."""

        return self._create_response(prompt, model=model)

    def _create_response(self, prompt: str, *, model: str) -> str:
        """Send plain prompt text and return raw model text for validation.

        The request intentionally uses no web tools, file uploads, function
        calling, or streaming; downstream validators own structure and safety.
        """

        response = self._client.responses.create(model=model, input=prompt)
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text
        return str(response)
