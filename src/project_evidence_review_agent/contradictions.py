"""Validation and artifact writing for contradiction candidates.

Contradiction detection runs only after a successful bounded claim review so the
model sees validated claims and the same selected evidence boundary. A candidate
is not a final contradiction finding; it is a pointer for human review.

The validator requires evidence IDs on both sides because tension between two
pieces of supplied evidence must remain auditable. Source IDs alone, invented
IDs, malformed structures, or verdict language fail validation. This stage still
does not approve, reject, certify, or make a go-live decision for the project.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from project_evidence_review_agent.claim_review import FORBIDDEN_REVIEW_PHRASES
from project_evidence_review_agent.llm_context import AUTHORITY_BOUNDARY
from project_evidence_review_agent.missing_evidence import ALLOWED_CONFIDENCE

CONTRADICTION_LOG_FILE_NAME = "contradiction_log.json"
CONTRADICTION_LOG_VERSION = 1
REQUIRED_CONTRADICTION_FIELDS = [
    "summary",
    "evidence_side_a",
    "evidence_side_b",
    "explanation",
    "related_claim_ids",
    "suggested_human_check",
    "confidence",
]
LIMITATIONS = [
    (
        "Contradiction candidates are possible tensions in the supplied evidence, "
        "not final findings."
    ),
    (
        "Every candidate must cite valid evidence IDs on both sides and requires "
        "human review."
    ),
    "This artifact is review material only and does not approve or reject the project.",
]


def validate_contradictions(
    items: Any, *, allowed_evidence_ids: list[str], allowed_claim_ids: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Validate contradiction candidates against bounded evidence and claim IDs."""

    messages: list[str] = []
    rejected: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return [], [], ["Top-level field 'contradiction_candidates' must be a list."]

    evidence_allowed = set(allowed_evidence_ids)
    claim_allowed = set(allowed_claim_ids)
    for index, item in enumerate(items, start=1):
        item_ref = _item_ref(item, index)
        if not isinstance(item, dict):
            message = f"{item_ref}: contradiction candidate must be an object."
            messages.append(message)
            rejected.append({"item_index": index, "reason": "candidate_not_object"})
            continue
        item_messages = _validate_candidate(
            item,
            item_ref=item_ref,
            allowed_evidence_ids=evidence_allowed,
            allowed_claim_ids=claim_allowed,
        )
        if item_messages:
            messages.extend(item_messages)
            rejected.append(
                {
                    "contradiction_id": item.get("contradiction_id"),
                    "summary_preview": _preview(str(item.get("summary", ""))),
                    "reason": "validation_failed",
                    "messages": item_messages,
                }
            )
            continue
        normalized = {field: item[field] for field in REQUIRED_CONTRADICTION_FIELDS}
        # Deterministic generated IDs make candidates easy to reference without
        # trusting model-provided identifiers.
        normalized["contradiction_id"] = f"CON-{len(accepted) + 1:04d}"
        accepted.append(normalized)
    return accepted, rejected, messages


def build_contradiction_artifact(
    *,
    question: str,
    model: str,
    analysis_status: str,
    validation_status: str,
    contradiction_candidates: list[dict[str, Any]],
    rejected_items: list[dict[str, Any]],
    validator_messages: list[str],
    allowed_evidence_ids: list[str],
    allowed_claim_ids: list[str],
) -> dict[str, Any]:
    """Build the contradiction log payload without treating candidates as findings."""

    return {
        "contradiction_log_version": CONTRADICTION_LOG_VERSION,
        "question": question,
        "analysis_status": analysis_status,
        "validation_status": validation_status,
        "llm_model": model,
        "contradiction_candidates": contradiction_candidates,
        "rejected_items": rejected_items,
        "validator_messages": validator_messages,
        "allowed_evidence_ids": allowed_evidence_ids,
        "allowed_claim_ids": allowed_claim_ids,
        "limitations": LIMITATIONS,
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_contradiction_artifact(output_dir: Path, payload: dict[str, Any]) -> Path:
    """Write ``contradiction_log.json`` and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / CONTRADICTION_LOG_FILE_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")
    return path


def _validate_candidate(
    item: dict[str, Any],
    *,
    item_ref: str,
    allowed_evidence_ids: set[str],
    allowed_claim_ids: set[str],
) -> list[str]:
    """Validate one contradiction candidate without treating it as a finding."""

    messages: list[str] = []
    for field in REQUIRED_CONTRADICTION_FIELDS:
        if field not in item:
            messages.append(f"{item_ref}: missing field '{field}'.")

    confidence = item.get("confidence")
    if confidence not in ALLOWED_CONFIDENCE:
        messages.append(f"{item_ref}: invalid confidence '{confidence}'.")

    _validate_side(
        item.get("evidence_side_a"),
        field=f"{item_ref}.evidence_side_a",
        allowed_evidence_ids=allowed_evidence_ids,
        messages=messages,
    )
    _validate_side(
        item.get("evidence_side_b"),
        field=f"{item_ref}.evidence_side_b",
        allowed_evidence_ids=allowed_evidence_ids,
        messages=messages,
    )
    _validate_claim_ids(
        item.get("related_claim_ids"),
        field=f"{item_ref}.related_claim_ids",
        allowed_claim_ids=allowed_claim_ids,
        messages=messages,
    )
    for key in ("summary", "explanation", "suggested_human_check"):
        _validate_text_value(item.get(key), f"{item_ref}.{key}", messages)
    return messages


def _validate_side(
    value: Any,
    *,
    field: str,
    allowed_evidence_ids: set[str],
    messages: list[str],
) -> None:
    """Validate one cited side of a possible tension.

    Both sides need concrete EV IDs because vague contradiction claims are hard
    for a human to verify.
    """

    if not isinstance(value, dict):
        messages.append(f"{field} must be an object.")
        return
    evidence_ids = value.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        messages.append(f"{field}.evidence_ids must be a list.")
        evidence_ids = []
    if not evidence_ids:
        messages.append(f"{field}.evidence_ids must contain at least one evidence ID.")
    for evidence_id in evidence_ids:
        if not isinstance(evidence_id, str):
            messages.append(f"{field}.evidence_ids values must be strings.")
            continue
        if evidence_id.startswith("SRC-"):
            # A whole source is too broad for a contradiction side; the candidate
            # must point to bounded evidence chunks.
            messages.append(
                f"{field}.evidence_ids cited source ID instead of evidence ID: "
                f"{evidence_id}."
            )
        if evidence_id not in allowed_evidence_ids:
            # Invented or unselected EV IDs break the same bounded-citation rule
            # used by claim review.
            messages.append(
                f"{field}.evidence_ids cited unknown evidence ID: {evidence_id}."
            )
    _validate_text_value(value.get("description"), f"{field}.description", messages)


def _validate_claim_ids(
    value: Any, *, field: str, allowed_claim_ids: set[str], messages: list[str]
) -> None:
    if not isinstance(value, list):
        messages.append(f"{field} must be a list.")
        return
    for claim_id in value:
        if not isinstance(claim_id, str):
            messages.append(f"{field} values must be strings.")
            continue
        if claim_id not in allowed_claim_ids:
            messages.append(f"{field} cited unknown claim ID: {claim_id}.")


def _validate_text_value(value: Any, field: str, messages: list[str]) -> None:
    """Reject generated text that crosses into authority/verdict language."""

    if not isinstance(value, str):
        messages.append(f"{field} must be text.")
        return
    normalized = value.lower()
    for phrase in FORBIDDEN_REVIEW_PHRASES:
        if phrase in normalized:
            messages.append(f"{field} contains forbidden authority language: {phrase}.")


def _item_ref(item: Any, index: int) -> str:
    if isinstance(item, dict) and item.get("contradiction_id"):
        return str(item["contradiction_id"])
    return f"contradiction_candidates[{index}]"


def _preview(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[:limit]}…"
