"""Record a review question as its own bounded artifact.

The review question is captured separately from retrieval because recording the
question does not answer it. A later retrieval step can use the normalized terms
to find lexically relevant chunks, but neither artifact decides whether a claim
is supported, complete, contradicted, ready, approved, compliant, or certified.

Keeping this stage small makes the workflow easier to inspect: humans can see
what question was supplied before any retrieval trace, evidence pack, Markdown
report, or future LLM review is created.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REVIEW_QUESTION_FILE_NAME = "review_question.json"
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "whether",
    "with",
}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
BOUNDARY_NOTE = (
    "Recording a review question does not answer it. This artifact does not "
    "review evidence, call an LLM, determine support, detect gaps or "
    "contradictions, or approve readiness, compliance, certification, or go-live."
)


def normalize_text(text: str) -> str:
    """Return normalized text for deterministic lexical retrieval.

    Normalization supports matching and traceability. It does not answer the
    review question or interpret evidence.
    """

    return " ".join(TOKEN_PATTERN.findall(text.lower()))


def tokenize(text: str) -> list[str]:
    """Tokenize text using a small local rule set and built-in stopwords."""

    return [
        term for term in TOKEN_PATTERN.findall(text.lower()) if term not in STOPWORDS
    ]


def unique_terms(text: str) -> list[str]:
    """Return sorted unique terms so repeated runs produce identical JSON."""

    return sorted(set(tokenize(text)))


def build_review_question(question: str) -> dict[str, Any]:
    """Build the JSON payload that records what the run is trying to answer."""

    return {
        "review_question_version": 1,
        "question": question,
        "normalized_question": normalize_text(question),
        "question_terms": unique_terms(question),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "boundary_note": BOUNDARY_NOTE,
    }


def write_review_question(question: str, output_dir: Path) -> Path:
    """Write ``review_question.json`` and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / REVIEW_QUESTION_FILE_NAME
    path.write_text(
        json.dumps(build_review_question(question), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
