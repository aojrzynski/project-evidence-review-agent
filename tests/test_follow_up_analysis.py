from __future__ import annotations

import json
from pathlib import Path

from project_evidence_review_agent.contradictions import validate_contradictions
from project_evidence_review_agent.follow_up_analysis import run_follow_up_analysis
from project_evidence_review_agent.missing_evidence import validate_missing_evidence


class FakeFollowUpClient:
    def __init__(
        self, response: str | None = None, *, error: Exception | None = None
    ) -> None:
        self.response = response or "{}"
        self.error = error
        self.calls = 0
        self.last_prompt = ""

    def review_follow_up_analysis(self, prompt: str, *, model: str) -> str:
        self.calls += 1
        self.last_prompt = prompt
        if self.error is not None:
            raise self.error
        return self.response


def test_valid_follow_up_output_writes_artifacts_with_deterministic_ids(
    tmp_path: Path,
) -> None:
    client = FakeFollowUpClient(json.dumps(_valid_follow_up()))

    result = run_follow_up_analysis(
        llm_context=_context(),
        claim_review=_claim_review(),
        client=client,
        model="fake-model",
        output_dir=tmp_path,
    )

    missing = json.loads(result.missing_evidence_path.read_text("utf-8"))
    contradictions = json.loads(result.contradiction_log_path.read_text("utf-8"))
    assert result.missing_validation_status == "passed"
    assert result.contradiction_validation_status == "passed"
    assert missing["missing_evidence"][0]["missing_evidence_id"] == "ME-0001"
    assert (
        contradictions["contradiction_candidates"][0]["contradiction_id"] == "CON-0001"
    )
    assert contradictions["contradiction_candidates"][0]["evidence_side_a"][
        "evidence_ids"
    ] == ["EV-0001"]
    assert client.calls == 1
    assert "validated_claim_review" in client.last_prompt


def test_missing_evidence_enums_and_ids_are_validated() -> None:
    item = _valid_missing_item()
    item["gap_type"] = "proof_missing"
    item["confidence"] = "certain"
    item["related_evidence_ids"] = ["EV-9999"]
    item["related_claim_ids"] = ["CL-9999"]

    accepted, rejected, messages = validate_missing_evidence(
        [item], allowed_evidence_ids=["EV-0001"], allowed_claim_ids=["CL-0001"]
    )

    assert accepted == []
    assert rejected
    assert any("invalid gap_type" in message for message in messages)
    assert any("invalid confidence" in message for message in messages)
    assert any("unknown ID: EV-9999" in message for message in messages)
    assert any("unknown ID: CL-9999" in message for message in messages)


def test_missing_evidence_empty_evidence_ids_allowed_only_for_not_found() -> None:
    allowed = _valid_missing_item()
    allowed["gap_type"] = "evidence_not_found"
    allowed["related_evidence_ids"] = []
    rejected_item = _valid_missing_item()
    rejected_item["gap_type"] = "evidence_unclear"
    rejected_item["related_evidence_ids"] = []

    accepted, rejected, messages = validate_missing_evidence(
        [allowed, rejected_item],
        allowed_evidence_ids=["EV-0001"],
        allowed_claim_ids=["CL-0001"],
    )

    assert accepted[0]["missing_evidence_id"] == "ME-0001"
    assert rejected
    assert any("empty related_evidence_ids" in message for message in messages)


def test_contradiction_candidates_require_valid_evidence_on_both_sides() -> None:
    item = _valid_contradiction_item()
    item["evidence_side_a"]["evidence_ids"] = []
    item["evidence_side_b"]["evidence_ids"] = ["SRC-0001", "EV-9999"]
    item["related_claim_ids"] = ["CL-9999"]

    accepted, rejected, messages = validate_contradictions(
        [item], allowed_evidence_ids=["EV-0001"], allowed_claim_ids=["CL-0001"]
    )

    assert accepted == []
    assert rejected
    assert any("side_a.evidence_ids must contain" in message for message in messages)
    assert any("source ID instead of evidence ID" in message for message in messages)
    assert any("unknown evidence ID: EV-9999" in message for message in messages)
    assert any("unknown claim ID: CL-9999" in message for message in messages)


def test_forbidden_language_is_rejected_in_follow_up_outputs() -> None:
    missing = _valid_missing_item()
    missing["summary"] = "The project is ready."
    contradiction = _valid_contradiction_item()
    contradiction["explanation"] = "This is the final decision."

    _, _, missing_messages = validate_missing_evidence(
        [missing], allowed_evidence_ids=["EV-0001"], allowed_claim_ids=["CL-0001"]
    )
    _, _, contradiction_messages = validate_contradictions(
        [contradiction], allowed_evidence_ids=["EV-0001"], allowed_claim_ids=["CL-0001"]
    )

    assert any(
        "forbidden authority language" in message for message in missing_messages
    )
    assert any(
        "forbidden authority language" in message for message in contradiction_messages
    )


def test_malformed_follow_up_json_is_rejected_cleanly(tmp_path: Path) -> None:
    result = run_follow_up_analysis(
        llm_context=_context(),
        claim_review=_claim_review(),
        client=FakeFollowUpClient("not json"),
        model="fake-model",
        output_dir=tmp_path,
    )

    assert result.missing_validation_status == "failed"
    assert result.contradiction_validation_status == "failed"
    assert (
        result.missing_evidence_payload["rejected_items"][0]["reason"]
        == "malformed_json"
    )


def test_follow_up_llm_exception_is_handled_cleanly(tmp_path: Path) -> None:
    result = run_follow_up_analysis(
        llm_context=_context(),
        claim_review=_claim_review(),
        client=FakeFollowUpClient(error=RuntimeError("synthetic outage")),
        model="fake-model",
        output_dir=tmp_path,
    )

    assert result.missing_evidence_status == "failed"
    assert result.missing_validation_status == "not_validated"
    assert (
        "synthetic outage" in result.missing_evidence_payload["validator_messages"][0]
    )


def _valid_follow_up() -> dict[str, object]:
    return {
        "missing_evidence": [_valid_missing_item()],
        "contradiction_candidates": [_valid_contradiction_item()],
    }


def _valid_missing_item() -> dict[str, object]:
    return {
        "gap_type": "evidence_not_found",
        "summary": (
            "The supplied evidence does not show a final test sign-off artifact."
        ),
        "details": (
            "The selected evidence mentions smoke testing but not a separate "
            "sign-off record."
        ),
        "related_claim_ids": ["CL-0001"],
        "related_evidence_ids": [],
        "suggested_human_check": (
            "Check whether a final test sign-off record exists in project files."
        ),
        "why_it_matters": (
            "A human may need the sign-off record to understand the evidence "
            "boundary."
        ),
        "confidence": "medium",
    }


def _valid_contradiction_item() -> dict[str, object]:
    return {
        "summary": (
            "One selected chunk says testing passed while another says review "
            "remains open."
        ),
        "evidence_side_a": {
            "evidence_ids": ["EV-0001"],
            "description": "Smoke testing passed.",
        },
        "evidence_side_b": {
            "evidence_ids": ["EV-0002"],
            "description": "Human review remains open.",
        },
        "explanation": (
            "The two chunks may describe different stages of the same process."
        ),
        "related_claim_ids": ["CL-0001"],
        "suggested_human_check": (
            "Ask a human reviewer to compare the test note and review note."
        ),
        "confidence": "low",
    }


def _context() -> dict[str, object]:
    return {
        "question": "What evidence shows testing is complete?",
        "allowed_evidence_ids": ["EV-0001", "EV-0002"],
        "evidence": [],
        "source_map": {"SRC-0001": {"source_id": "SRC-0001"}},
    }


def _claim_review() -> dict[str, object]:
    return {
        "validation_status": "passed",
        "claims": [{"claim_id": "CL-0001", "claim_text": "Smoke testing passed."}],
    }
