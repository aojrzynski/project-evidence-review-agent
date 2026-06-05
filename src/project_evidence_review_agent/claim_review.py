"""Bounded LLM claim review and deterministic validation.

The LLM is useful for drafting claim-level review material, but it is not an
authority. It may reason only over ``llm_safe_review_context.json``. Every
supported or partially supported claim must cite existing evidence IDs because
citations keep the output tied to bounded local evidence instead of model memory.

Invented citations, uncited support claims, malformed JSON, and authority language
are rejected deterministically. A failed validation must never become a successful
claim review, because a failed artifact is safer than a misleading successful
review. This stage does not approve a project, certify readiness, detect missing
evidence as a standalone workflow stage, detect contradictions as a standalone
workflow stage, or write the final project evidence report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_evidence_review_agent.llm_client import ReviewLLMClient
from project_evidence_review_agent.llm_context import AUTHORITY_BOUNDARY

CLAIM_REVIEW_FILE_NAME = "claim_review.json"
CLAIM_REVIEW_VERSION = 1
ALLOWED_CLAIM_STATUSES = {
    "evidence_supported",
    "partially_supported",
    "not_supported_by_supplied_evidence",
    "unclear_from_supplied_evidence",
}
SUPPORT_STATUSES = {"evidence_supported", "partially_supported"}
FORBIDDEN_REVIEW_PHRASES = [
    "approved",
    "approval granted",
    "certified",
    "compliant",
    "compliance confirmed",
    "go-live approved",
    "ready for go-live",
    "safe to launch",
    "production ready",
    "project is ready",
    "final decision",
    "legal verdict",
    "security verdict",
    "privacy verdict",
]
REQUIRED_TOP_LEVEL_FIELDS = [
    "claims",
    "unsupported_or_unclear_points",
    "review_caveats",
    "recommended_human_checks",
]
REQUIRED_CLAIM_FIELDS = [
    "claim_id",
    "claim_text",
    "status",
    "evidence_ids",
    "explanation",
    "caveats",
]


@dataclass(frozen=True)
class ClaimReviewResult:
    """Summary returned to CLI wiring and trace construction."""

    path: Path
    payload: dict[str, Any]

    @property
    def llm_review_status(self) -> str:
        return str(self.payload.get("llm_review_status", "unknown"))

    @property
    def validation_status(self) -> str:
        return str(self.payload.get("validation_status", "unknown"))

    @property
    def claim_count(self) -> int:
        claims = self.payload.get("claims", [])
        return len(claims) if isinstance(claims, list) else 0

    @property
    def rejected_claim_count(self) -> int:
        rejected = self.payload.get("rejected_items", [])
        return len(rejected) if isinstance(rejected, list) else 0

    @property
    def validator_message_count(self) -> int:
        messages = self.payload.get("validator_messages", [])
        return len(messages) if isinstance(messages, list) else 0


def build_claim_review_prompt(context: dict[str, Any]) -> str:
    """Build the strict bounded prompt for claim review."""

    schema = {
        "claims": [
            {
                "claim_id": "CL-0001",
                "claim_text": "Short claim grounded only in supplied evidence.",
                "status": (
                    "evidence_supported | partially_supported | "
                    "not_supported_by_supplied_evidence | "
                    "unclear_from_supplied_evidence"
                ),
                "evidence_ids": ["EV-0001"],
                "explanation": "Explain using only supplied evidence.",
                "caveats": ["Any limitation from supplied evidence."],
            }
        ],
        "unsupported_or_unclear_points": [
            "Point that remains unclear from supplied evidence."
        ],
        "review_caveats": ["Bounded review caveat."],
        "recommended_human_checks": ["Concrete next check for a human."],
    }
    prompt_payload = {
        "task": "Return a bounded claim review as JSON only.",
        "rules": [
            "Use only the supplied evidence context below.",
            "Do not answer from general knowledge or memory.",
            "Do not invent evidence IDs or cite source IDs alone.",
            (
                "Every evidence_supported or partially_supported claim must cite "
                "at least one allowed evidence ID."
            ),
            "Use unclear_from_supplied_evidence when evidence is insufficient.",
            (
                "Do not approve the project, certify readiness, or make legal/"
                "compliance/privacy/security/go-live verdicts."
            ),
            "Human review remains final.",
            "Return only JSON matching the schema; do not include Markdown.",
        ],
        "allowed_evidence_ids": context.get("allowed_evidence_ids", []),
        "expected_schema": schema,
        "bounded_context": context,
    }
    return json.dumps(prompt_payload, indent=2, sort_keys=True)


def run_claim_review(
    *,
    context: dict[str, Any],
    client: ReviewLLMClient,
    model: str,
    output_dir: Path,
) -> ClaimReviewResult:
    """Call an injected LLM client, validate the response, and write an artifact."""

    prompt = build_claim_review_prompt(context)
    path = output_dir / CLAIM_REVIEW_FILE_NAME
    allowed_evidence_ids = [str(eid) for eid in context.get("allowed_evidence_ids", [])]
    try:
        raw_response = client.review_claims(prompt, model=model)
    except Exception as exc:  # noqa: BLE001 - convert client failures to clean artifact
        payload = build_failed_claim_review(
            context=context,
            model=model,
            llm_review_status="failed",
            validation_status="not_validated",
            validator_messages=[f"LLM claim review failed: {exc}"],
        )
        _write_json(path, payload)
        return ClaimReviewResult(path=path, payload=payload)

    parsed, parse_messages = parse_llm_response(raw_response)
    if parsed is None:
        payload = build_failed_claim_review(
            context=context,
            model=model,
            llm_review_status="completed",
            validation_status="failed",
            validator_messages=parse_messages,
            rejected_items=[
                {
                    "reason": "malformed_json",
                    "raw_response_preview": _preview(raw_response),
                }
            ],
        )
        _write_json(path, payload)
        return ClaimReviewResult(path=path, payload=payload)

    validation_messages, rejected_items = validate_claim_review_response(
        parsed, allowed_evidence_ids=allowed_evidence_ids
    )
    validation_status = "passed" if not validation_messages else "failed"
    payload = _claim_review_payload(
        context=context,
        model=model,
        llm_review_status="completed",
        validation_status=validation_status,
        parsed=parsed if validation_status == "passed" else {},
        validator_messages=validation_messages,
        rejected_items=rejected_items,
    )
    _write_json(path, payload)
    return ClaimReviewResult(path=path, payload=payload)


def parse_llm_response(raw_response: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse model JSON without accepting malformed output as successful."""

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        return None, [f"LLM response was not valid JSON: {exc.msg}"]
    if not isinstance(parsed, dict):
        return None, ["LLM response JSON must be an object."]
    return parsed, []


def validate_claim_review_response(
    response: dict[str, Any], *, allowed_evidence_ids: list[str]
) -> tuple[list[str], list[dict[str, Any]]]:
    """Validate structure, citations, statuses, and authority language."""

    messages: list[str] = []
    rejected_items: list[dict[str, Any]] = []
    allowed = set(allowed_evidence_ids)

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in response:
            messages.append(f"Missing top-level field: {field}")
    claims = response.get("claims")
    if not isinstance(claims, list):
        messages.append("Top-level field 'claims' must be a list.")
        claims = []

    _validate_text_collection(
        response.get("review_caveats", []), "review_caveats", messages
    )
    _validate_text_collection(
        response.get("recommended_human_checks", []),
        "recommended_human_checks",
        messages,
    )
    _validate_text_collection(
        response.get("unsupported_or_unclear_points", []),
        "unsupported_or_unclear_points",
        messages,
    )

    for index, claim in enumerate(claims, start=1):
        claim_ref = _claim_ref(claim, index)
        if not isinstance(claim, dict):
            messages.append(f"{claim_ref}: claim must be an object.")
            rejected_items.append({"claim_index": index, "reason": "claim_not_object"})
            continue
        claim_messages = _validate_claim(claim, allowed=allowed, claim_ref=claim_ref)
        if claim_messages:
            messages.extend(claim_messages)
            rejected_items.append(
                {
                    "claim_id": claim.get("claim_id"),
                    "claim_text_preview": _preview(str(claim.get("claim_text", ""))),
                    "reason": "validation_failed",
                    "messages": claim_messages,
                }
            )
    return messages, rejected_items


def build_failed_claim_review(
    *,
    context: dict[str, Any],
    model: str,
    llm_review_status: str,
    validation_status: str,
    validator_messages: list[str],
    rejected_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a failed artifact without pretending the review succeeded."""

    return _claim_review_payload(
        context=context,
        model=model,
        llm_review_status=llm_review_status,
        validation_status=validation_status,
        parsed={},
        validator_messages=validator_messages,
        rejected_items=rejected_items or [],
    )


def _claim_review_payload(
    *,
    context: dict[str, Any],
    model: str,
    llm_review_status: str,
    validation_status: str,
    parsed: dict[str, Any],
    validator_messages: list[str],
    rejected_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "claim_review_version": CLAIM_REVIEW_VERSION,
        "question": context.get("question", ""),
        "llm_review_status": llm_review_status,
        "llm_model": model,
        "validation_status": validation_status,
        "claims": parsed.get("claims", []),
        "unsupported_or_unclear_points": parsed.get(
            "unsupported_or_unclear_points", []
        ),
        "review_caveats": parsed.get("review_caveats", []),
        "recommended_human_checks": parsed.get("recommended_human_checks", []),
        "rejected_items": rejected_items,
        "validator_messages": validator_messages,
        "allowed_evidence_ids": context.get("allowed_evidence_ids", []),
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def _validate_claim(
    claim: dict[str, Any], *, allowed: set[str], claim_ref: str
) -> list[str]:
    messages: list[str] = []
    for field in REQUIRED_CLAIM_FIELDS:
        if field not in claim:
            messages.append(f"{claim_ref}: missing field '{field}'.")

    status = claim.get("status")
    if status not in ALLOWED_CLAIM_STATUSES:
        messages.append(f"{claim_ref}: invalid status '{status}'.")

    evidence_ids = claim.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        messages.append(f"{claim_ref}: evidence_ids must be a list.")
        evidence_ids = []
    else:
        for evidence_id in evidence_ids:
            if not isinstance(evidence_id, str):
                messages.append(f"{claim_ref}: evidence ID values must be strings.")
                continue
            if evidence_id.startswith("SRC-"):
                messages.append(
                    f"{claim_ref}: cited source ID instead of evidence ID: "
                    f"{evidence_id}."
                )
            if evidence_id not in allowed:
                messages.append(
                    f"{claim_ref}: cited unknown evidence ID: {evidence_id}."
                )
    if status in SUPPORT_STATUSES and not evidence_ids:
        messages.append(
            f"{claim_ref}: {status} claims must cite at least one evidence ID."
        )

    for key in ("claim_text", "explanation"):
        _validate_text_value(claim.get(key, ""), f"{claim_ref}.{key}", messages)
    _validate_text_collection(
        claim.get("caveats", []), f"{claim_ref}.caveats", messages
    )
    return messages


def _validate_text_collection(value: Any, field: str, messages: list[str]) -> None:
    if not isinstance(value, list):
        messages.append(f"{field} must be a list.")
        return
    for index, item in enumerate(value, start=1):
        _validate_text_value(item, f"{field}[{index}]", messages)


def _validate_text_value(value: Any, field: str, messages: list[str]) -> None:
    if not isinstance(value, str):
        messages.append(f"{field} must be text.")
        return
    normalized = value.lower()
    for phrase in FORBIDDEN_REVIEW_PHRASES:
        if phrase in normalized:
            messages.append(f"{field} contains forbidden authority language: {phrase}.")


def _claim_ref(claim: Any, index: int) -> str:
    if isinstance(claim, dict) and claim.get("claim_id"):
        return str(claim["claim_id"])
    return f"claim[{index}]"


def _preview(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}…"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")
