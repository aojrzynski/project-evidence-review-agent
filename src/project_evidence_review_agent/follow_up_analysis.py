"""Combined LLM follow-up analysis for evidence gaps and contradictions.

The follow-up call is intentionally placed after claim review. At that point the
workflow has a bounded context and a validated claim-review artifact, so the model
can suggest missing evidence and contradiction candidates without seeing raw
project folders, full inventories, unsupported files, external knowledge, tools,
or web search.

The LLM may suggest review material, but validators decide what can be written as
a successful artifact. Missing evidence remains a gap signal rather than proof of
absence. Contradiction candidates require cited evidence on both sides and remain
candidates for human review, not final findings. This stage still does not write
the final report or make any approval, readiness, compliance, certification, or
go-live decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_evidence_review_agent.claim_review import parse_llm_response
from project_evidence_review_agent.contradictions import (
    build_contradiction_artifact,
    validate_contradictions,
    write_contradiction_artifact,
)
from project_evidence_review_agent.llm_client import ReviewLLMClient
from project_evidence_review_agent.missing_evidence import (
    build_missing_evidence_artifact,
    validate_missing_evidence,
    write_missing_evidence_artifact,
)


@dataclass(frozen=True)
class FollowUpAnalysisResult:
    """Summary returned to CLI wiring and trace construction."""

    missing_evidence_path: Path
    contradiction_log_path: Path
    missing_evidence_payload: dict[str, Any]
    contradiction_payload: dict[str, Any]

    @property
    def missing_evidence_status(self) -> str:
        return str(self.missing_evidence_payload.get("analysis_status", "unknown"))

    @property
    def missing_validation_status(self) -> str:
        return str(self.missing_evidence_payload.get("validation_status", "unknown"))

    @property
    def contradiction_status(self) -> str:
        return str(self.contradiction_payload.get("analysis_status", "unknown"))

    @property
    def contradiction_validation_status(self) -> str:
        return str(self.contradiction_payload.get("validation_status", "unknown"))

    @property
    def missing_count(self) -> int:
        items = self.missing_evidence_payload.get("missing_evidence", [])
        return len(items) if isinstance(items, list) else 0

    @property
    def rejected_missing_count(self) -> int:
        items = self.missing_evidence_payload.get("rejected_items", [])
        return len(items) if isinstance(items, list) else 0

    @property
    def contradiction_count(self) -> int:
        items = self.contradiction_payload.get("contradiction_candidates", [])
        return len(items) if isinstance(items, list) else 0

    @property
    def rejected_contradiction_count(self) -> int:
        items = self.contradiction_payload.get("rejected_items", [])
        return len(items) if isinstance(items, list) else 0


def build_follow_up_analysis_prompt(
    *, llm_context: dict[str, Any], claim_review: dict[str, Any]
) -> str:
    """Build one strict bounded prompt for gap and contradiction signals.

    The prompt reuses selected evidence and validated claim review only. It does
    not authorize external searching, raw-source access, or final findings.
    """

    allowed_claim_ids = _allowed_claim_ids(claim_review)
    schema = {
        "missing_evidence": [
            {
                "gap_type": (
                    "evidence_not_found | evidence_unclear | "
                    "evidence_not_searched | requires_human_follow_up"
                ),
                "summary": "Short bounded gap summary.",
                "details": (
                    "Explain the gap using only supplied evidence and claim review."
                ),
                "related_claim_ids": ["CL-0001"],
                "related_evidence_ids": ["EV-0001"],
                "suggested_human_check": "Practical non-authoritative next check.",
                "why_it_matters": "Why a human may want to check this gap.",
                "confidence": "low | medium | high",
            }
        ],
        "contradiction_candidates": [
            {
                "summary": "Short possible-tension summary.",
                "evidence_side_a": {
                    "evidence_ids": ["EV-0001"],
                    "description": "What this side appears to say.",
                },
                "evidence_side_b": {
                    "evidence_ids": ["EV-0002"],
                    "description": "What the other side appears to say.",
                },
                "explanation": "Why the cited sides may be in tension.",
                "related_claim_ids": ["CL-0001"],
                "suggested_human_check": "Practical non-authoritative next check.",
                "confidence": "low | medium | high",
            }
        ],
    }
    prompt_payload = {
        "task": "Return bounded review follow-up analysis as JSON only.",
        "rules": [
            "Use only the supplied evidence context and validated claim review.",
            "Do not answer from memory or external knowledge.",
            "Do not invent evidence IDs.",
            "Do not invent claim IDs.",
            (
                "Missing evidence means a gap or uncertainty in supplied evidence, "
                "not proof that something does not exist."
            ),
            "Contradictions are only candidates and require human review.",
            "Every contradiction candidate must cite evidence IDs on both sides.",
            (
                "If no contradiction is visible in the supplied evidence, return "
                "an empty contradiction_candidates list."
            ),
            "Do not approve or reject the project.",
            "Do not certify readiness, compliance, security, privacy, or go-live.",
            "Return only JSON matching the schema; do not include Markdown.",
        ],
        "allowed_evidence_ids": llm_context.get("allowed_evidence_ids", []),
        "allowed_claim_ids": allowed_claim_ids,
        "expected_schema": schema,
        "bounded_context": llm_context,
        "validated_claim_review": claim_review,
    }
    return json.dumps(prompt_payload, indent=2, sort_keys=True)


def run_follow_up_analysis(
    *,
    llm_context: dict[str, Any],
    claim_review: dict[str, Any],
    client: ReviewLLMClient,
    model: str,
    output_dir: Path,
) -> FollowUpAnalysisResult:
    """Call the injected client once, validate both outputs, and write artifacts."""

    prompt = build_follow_up_analysis_prompt(
        llm_context=llm_context, claim_review=claim_review
    )
    question = str(llm_context.get("question", ""))
    allowed_evidence_ids = [
        str(eid) for eid in llm_context.get("allowed_evidence_ids", [])
    ]
    allowed_claim_ids = _allowed_claim_ids(claim_review)
    try:
        # One bounded follow-up call asks for both kinds of review support so the
        # same evidence and validated claim IDs govern both outputs.
        raw_response = client.review_follow_up_analysis(prompt, model=model)
    except Exception as exc:  # noqa: BLE001 - convert client failures to clean artifacts
        # Client failures become failed artifacts for both follow-up outputs; a
        # missing file would make trace inspection harder.
        message = f"LLM follow-up analysis failed: {exc}"
        missing_payload = build_missing_evidence_artifact(
            question=question,
            model=model,
            analysis_status="failed",
            validation_status="not_validated",
            missing_evidence=[],
            rejected_items=[],
            validator_messages=[message],
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_claim_ids=allowed_claim_ids,
        )
        contradiction_payload = build_contradiction_artifact(
            question=question,
            model=model,
            analysis_status="failed",
            validation_status="not_validated",
            contradiction_candidates=[],
            rejected_items=[],
            validator_messages=[message],
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_claim_ids=allowed_claim_ids,
        )
        return _write_result(output_dir, missing_payload, contradiction_payload)

    parsed, parse_messages = parse_llm_response(raw_response)
    if parsed is None:
        # Malformed output cannot safely produce either artifact because both
        # depend on the same top-level JSON response.
        rejected = [
            {"reason": "malformed_json", "raw_response_preview": _preview(raw_response)}
        ]
        missing_payload = build_missing_evidence_artifact(
            question=question,
            model=model,
            analysis_status="completed",
            validation_status="failed",
            missing_evidence=[],
            rejected_items=rejected,
            validator_messages=parse_messages,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_claim_ids=allowed_claim_ids,
        )
        contradiction_payload = build_contradiction_artifact(
            question=question,
            model=model,
            analysis_status="completed",
            validation_status="failed",
            contradiction_candidates=[],
            rejected_items=rejected,
            validator_messages=parse_messages,
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_claim_ids=allowed_claim_ids,
        )
        return _write_result(output_dir, missing_payload, contradiction_payload)

    top_messages = _validate_top_level(parsed)
    # Validation remains deterministic and separate from the model call. Unsafe
    # or malformed items are rejected rather than repaired into findings.
    missing_items, rejected_missing, missing_messages = validate_missing_evidence(
        parsed.get("missing_evidence"),
        allowed_evidence_ids=allowed_evidence_ids,
        allowed_claim_ids=allowed_claim_ids,
    )
    contradiction_items, rejected_contradictions, contradiction_messages = (
        validate_contradictions(
            parsed.get("contradiction_candidates"),
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_claim_ids=allowed_claim_ids,
        )
    )
    missing_all_messages = top_messages + missing_messages
    contradiction_all_messages = top_messages + contradiction_messages
    missing_status = "passed" if not missing_all_messages else "failed"
    contradiction_status = "passed" if not contradiction_all_messages else "failed"
    missing_payload = build_missing_evidence_artifact(
        question=question,
        model=model,
        analysis_status="completed",
        validation_status=missing_status,
        missing_evidence=missing_items if missing_status == "passed" else [],
        rejected_items=rejected_missing,
        validator_messages=missing_all_messages,
        allowed_evidence_ids=allowed_evidence_ids,
        allowed_claim_ids=allowed_claim_ids,
    )
    contradiction_payload = build_contradiction_artifact(
        question=question,
        model=model,
        analysis_status="completed",
        validation_status=contradiction_status,
        contradiction_candidates=contradiction_items
        if contradiction_status == "passed"
        else [],
        rejected_items=rejected_contradictions,
        validator_messages=contradiction_all_messages,
        allowed_evidence_ids=allowed_evidence_ids,
        allowed_claim_ids=allowed_claim_ids,
    )
    return _write_result(output_dir, missing_payload, contradiction_payload)


def _validate_top_level(parsed: dict[str, Any]) -> list[str]:
    """Check that the combined response contains both expected sections."""

    messages: list[str] = []
    for field in ("missing_evidence", "contradiction_candidates"):
        if field not in parsed:
            messages.append(f"Missing top-level field: {field}")
    return messages


def _allowed_claim_ids(claim_review: dict[str, Any]) -> list[str]:
    """Extract validated claim IDs that follow-up output may reference."""

    claims = claim_review.get("claims", [])
    if not isinstance(claims, list):
        return []
    return [
        str(claim.get("claim_id"))
        for claim in claims
        if isinstance(claim, dict) and claim.get("claim_id")
    ]


def _write_result(
    output_dir: Path,
    missing_payload: dict[str, Any],
    contradiction_payload: dict[str, Any],
) -> FollowUpAnalysisResult:
    """Write both follow-up artifacts and return their trace-facing summary."""

    missing_path = write_missing_evidence_artifact(output_dir, missing_payload)
    contradiction_path = write_contradiction_artifact(output_dir, contradiction_payload)
    return FollowUpAnalysisResult(
        missing_evidence_path=missing_path,
        contradiction_log_path=contradiction_path,
        missing_evidence_payload=missing_payload,
        contradiction_payload=contradiction_payload,
    )


def _preview(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[:limit]}…"
