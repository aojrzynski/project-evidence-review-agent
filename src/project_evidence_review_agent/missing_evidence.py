"""Validation and artifact writing for missing evidence review support.

Missing evidence analysis deliberately runs after bounded claim review. The claim
review has already constrained the model to selected evidence and validated claim
IDs, so this stage can talk about gaps relative to that bounded material instead
of raw project folders or model memory.

A missing evidence entry is only a gap signal. It is not proof that an artifact
does not exist somewhere else, and it is not a project decision. Validation is
required before a successful artifact is written because the LLM may otherwise
invent evidence IDs, use unsupported categories, or drift into approval language.
Human review remains the final authority, and the final human-readable project
evidence report is still a later workflow stage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from project_evidence_review_agent.claim_review import FORBIDDEN_REVIEW_PHRASES
from project_evidence_review_agent.llm_context import AUTHORITY_BOUNDARY

MISSING_EVIDENCE_FILE_NAME = "missing_evidence.json"
MISSING_EVIDENCE_VERSION = 1
ALLOWED_GAP_TYPES = {
    "evidence_not_found",
    "evidence_unclear",
    "evidence_not_searched",
    "requires_human_follow_up",
}
GAP_TYPES_ALLOWING_EMPTY_EVIDENCE_IDS = {"evidence_not_found", "evidence_not_searched"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
REQUIRED_MISSING_EVIDENCE_FIELDS = [
    "gap_type",
    "summary",
    "details",
    "related_claim_ids",
    "related_evidence_ids",
    "suggested_human_check",
    "why_it_matters",
    "confidence",
]
LIMITATIONS = [
    (
        "Missing evidence is a gap or uncertainty signal within the supplied "
        "evidence, not proof that an artifact does not exist."
    ),
    "This artifact is review material only and does not approve or reject the project.",
]


def validate_missing_evidence(
    items: Any, *, allowed_evidence_ids: list[str], allowed_claim_ids: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Validate missing evidence entries against bounded IDs and safe wording."""

    messages: list[str] = []
    rejected: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return [], [], ["Top-level field 'missing_evidence' must be a list."]

    evidence_allowed = set(allowed_evidence_ids)
    claim_allowed = set(allowed_claim_ids)
    for index, item in enumerate(items, start=1):
        item_ref = _item_ref(item, index)
        if not isinstance(item, dict):
            message = f"{item_ref}: missing evidence entry must be an object."
            messages.append(message)
            rejected.append({"item_index": index, "reason": "entry_not_object"})
            continue
        item_messages = _validate_item(
            item,
            item_ref=item_ref,
            allowed_evidence_ids=evidence_allowed,
            allowed_claim_ids=claim_allowed,
        )
        if item_messages:
            messages.extend(item_messages)
            rejected.append(
                {
                    "missing_evidence_id": item.get("missing_evidence_id"),
                    "summary_preview": _preview(str(item.get("summary", ""))),
                    "reason": "validation_failed",
                    "messages": item_messages,
                }
            )
            continue
        normalized = {field: item[field] for field in REQUIRED_MISSING_EVIDENCE_FIELDS}
        normalized["missing_evidence_id"] = f"ME-{len(accepted) + 1:04d}"
        accepted.append(normalized)
    return accepted, rejected, messages


def build_missing_evidence_artifact(
    *,
    question: str,
    model: str,
    analysis_status: str,
    validation_status: str,
    missing_evidence: list[dict[str, Any]],
    rejected_items: list[dict[str, Any]],
    validator_messages: list[str],
    allowed_evidence_ids: list[str],
    allowed_claim_ids: list[str],
) -> dict[str, Any]:
    """Build the JSON artifact payload without making a project decision."""

    return {
        "missing_evidence_version": MISSING_EVIDENCE_VERSION,
        "question": question,
        "analysis_status": analysis_status,
        "validation_status": validation_status,
        "llm_model": model,
        "missing_evidence": missing_evidence,
        "rejected_items": rejected_items,
        "validator_messages": validator_messages,
        "allowed_evidence_ids": allowed_evidence_ids,
        "allowed_claim_ids": allowed_claim_ids,
        "limitations": LIMITATIONS,
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_missing_evidence_artifact(output_dir: Path, payload: dict[str, Any]) -> Path:
    """Write ``missing_evidence.json`` and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MISSING_EVIDENCE_FILE_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")
    return path


def _validate_item(
    item: dict[str, Any],
    *,
    item_ref: str,
    allowed_evidence_ids: set[str],
    allowed_claim_ids: set[str],
) -> list[str]:
    messages: list[str] = []
    for field in REQUIRED_MISSING_EVIDENCE_FIELDS:
        if field not in item:
            messages.append(f"{item_ref}: missing field '{field}'.")

    gap_type = item.get("gap_type")
    if gap_type not in ALLOWED_GAP_TYPES:
        messages.append(f"{item_ref}: invalid gap_type '{gap_type}'.")
    confidence = item.get("confidence")
    if confidence not in ALLOWED_CONFIDENCE:
        messages.append(f"{item_ref}: invalid confidence '{confidence}'.")

    evidence_ids = _validate_id_list(
        item.get("related_evidence_ids"),
        field=f"{item_ref}.related_evidence_ids",
        allowed=allowed_evidence_ids,
        reject_source_ids=True,
        messages=messages,
    )
    if not evidence_ids and gap_type not in GAP_TYPES_ALLOWING_EMPTY_EVIDENCE_IDS:
        messages.append(
            f"{item_ref}: empty related_evidence_ids is allowed only for "
            "evidence_not_found or evidence_not_searched gaps."
        )
    _validate_id_list(
        item.get("related_claim_ids"),
        field=f"{item_ref}.related_claim_ids",
        allowed=allowed_claim_ids,
        reject_source_ids=False,
        messages=messages,
    )

    for key in ("summary", "details", "suggested_human_check", "why_it_matters"):
        _validate_text_value(item.get(key), f"{item_ref}.{key}", messages)
    return messages


def _validate_id_list(
    value: Any,
    *,
    field: str,
    allowed: set[str],
    reject_source_ids: bool,
    messages: list[str],
) -> list[str]:
    if not isinstance(value, list):
        messages.append(f"{field} must be a list.")
        return []
    valid_values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            messages.append(f"{field} values must be strings.")
            continue
        if reject_source_ids and item.startswith("SRC-"):
            messages.append(f"{field} cited source ID instead of evidence ID: {item}.")
        if item not in allowed:
            messages.append(f"{field} cited unknown ID: {item}.")
        else:
            valid_values.append(item)
    return valid_values


def _validate_text_value(value: Any, field: str, messages: list[str]) -> None:
    if not isinstance(value, str):
        messages.append(f"{field} must be text.")
        return
    normalized = value.lower()
    for phrase in FORBIDDEN_REVIEW_PHRASES:
        if phrase in normalized:
            messages.append(f"{field} contains forbidden authority language: {phrase}.")


def _item_ref(item: Any, index: int) -> str:
    if isinstance(item, dict) and item.get("missing_evidence_id"):
        return str(item["missing_evidence_id"])
    return f"missing_evidence[{index}]"


def _preview(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[:limit]}…"
