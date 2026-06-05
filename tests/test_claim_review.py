from __future__ import annotations

import json
from pathlib import Path

from project_evidence_review_agent.claim_review import (
    CLAIM_REVIEW_FILE_NAME,
    run_claim_review,
)
from project_evidence_review_agent.cli import main
from project_evidence_review_agent.llm_context import (
    LLM_SAFE_REVIEW_CONTEXT_FILE_NAME,
    build_llm_safe_review_context,
)
from project_evidence_review_agent.trace import TRACE_FILE_NAME


class FakeReviewClient:
    def __init__(
        self, response: str | None = None, *, error: Exception | None = None
    ) -> None:
        self.response = response or "{}"
        self.error = error
        self.calls = 0
        self.last_prompt = ""
        self.last_model = ""

    def review_claims(self, prompt: str, *, model: str) -> str:
        self.calls += 1
        self.last_prompt = prompt
        self.last_model = model
        if self.error is not None:
            raise self.error
        return self.response


def test_valid_fake_llm_response_writes_valid_claim_review(tmp_path: Path) -> None:
    context = build_llm_safe_review_context(_evidence_pack())
    client = FakeReviewClient(json.dumps(_valid_response()))

    result = run_claim_review(
        context=context, client=client, model="fake-model", output_dir=tmp_path
    )

    payload = json.loads((tmp_path / CLAIM_REVIEW_FILE_NAME).read_text("utf-8"))
    assert result.validation_status == "passed"
    assert payload["validation_status"] == "passed"
    assert payload["llm_review_status"] == "completed"
    assert payload["claims"][0]["evidence_ids"] == ["EV-0001"]
    assert payload["allowed_evidence_ids"] == ["EV-0001"]
    assert client.calls == 1
    assert "EV-0001" in client.last_prompt


def test_invented_evidence_id_is_rejected(tmp_path: Path) -> None:
    response = _valid_response()
    response["claims"][0]["evidence_ids"] = ["EV-9999"]
    result = run_claim_review(
        context=build_llm_safe_review_context(_evidence_pack()),
        client=FakeReviewClient(json.dumps(response)),
        model="fake-model",
        output_dir=tmp_path,
    )

    assert result.validation_status == "failed"
    assert any(
        "unknown evidence ID" in message
        for message in result.payload["validator_messages"]
    )
    assert result.payload["claims"] == []
    assert result.payload["rejected_items"]


def test_missing_citation_for_supported_claim_is_rejected(tmp_path: Path) -> None:
    response = _valid_response()
    response["claims"][0]["evidence_ids"] = []
    result = run_claim_review(
        context=build_llm_safe_review_context(_evidence_pack()),
        client=FakeReviewClient(json.dumps(response)),
        model="fake-model",
        output_dir=tmp_path,
    )

    assert result.validation_status == "failed"
    assert any(
        "must cite at least one evidence ID" in message
        for message in result.payload["validator_messages"]
    )


def test_forbidden_approval_language_is_rejected(tmp_path: Path) -> None:
    response = _valid_response()
    response["claims"][0]["claim_text"] = "The project is ready for go-live."
    result = run_claim_review(
        context=build_llm_safe_review_context(_evidence_pack()),
        client=FakeReviewClient(json.dumps(response)),
        model="fake-model",
        output_dir=tmp_path,
    )

    assert result.validation_status == "failed"
    assert any(
        "forbidden authority language" in message
        for message in result.payload["validator_messages"]
    )


def test_malformed_json_is_rejected_cleanly(tmp_path: Path) -> None:
    result = run_claim_review(
        context=build_llm_safe_review_context(_evidence_pack()),
        client=FakeReviewClient("not json"),
        model="fake-model",
        output_dir=tmp_path,
    )

    assert result.validation_status == "failed"
    assert result.payload["claims"] == []
    assert result.payload["rejected_items"][0]["reason"] == "malformed_json"


def test_fake_llm_exception_is_handled_cleanly(tmp_path: Path) -> None:
    result = run_claim_review(
        context=build_llm_safe_review_context(_evidence_pack()),
        client=FakeReviewClient(error=RuntimeError("synthetic outage")),
        model="fake-model",
        output_dir=tmp_path,
    )

    assert result.llm_review_status == "failed"
    assert result.validation_status == "not_validated"
    assert "synthetic outage" in result.payload["validator_messages"][0]


def test_cli_no_llm_does_not_call_fake_client_or_write_claim_review(
    tmp_path: Path,
) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"
    client = FakeReviewClient(json.dumps(_valid_response()))

    exit_code = main(
        [
            "--sources",
            str(sources),
            "--question",
            "What evidence shows testing is complete?",
            "--no-llm",
            "--output-dir",
            str(output_dir),
        ],
        review_client=client,
    )

    trace = json.loads((output_dir / TRACE_FILE_NAME).read_text("utf-8"))
    assert exit_code == 0
    assert client.calls == 0
    assert not (output_dir / CLAIM_REVIEW_FILE_NAME).exists()
    assert not (output_dir / LLM_SAFE_REVIEW_CONTEXT_FILE_NAME).exists()
    assert trace["llm_review_status"] == "skipped_no_llm"
    assert trace["claim_review_validation_status"] == "not_performed"


def test_cli_fake_llm_writes_context_claim_review_and_trace(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"
    client = FakeReviewClient(json.dumps(_valid_response()))

    exit_code = main(
        [
            "--sources",
            str(sources),
            "--question",
            "What evidence shows testing is complete?",
            "--llm-model",
            "fake-model",
            "--output-dir",
            str(output_dir),
        ],
        review_client=client,
    )

    trace = json.loads((output_dir / TRACE_FILE_NAME).read_text("utf-8"))
    context = json.loads(
        (output_dir / LLM_SAFE_REVIEW_CONTEXT_FILE_NAME).read_text("utf-8")
    )
    review = json.loads((output_dir / CLAIM_REVIEW_FILE_NAME).read_text("utf-8"))
    assert exit_code == 0
    assert client.calls == 1
    assert context["allowed_evidence_ids"] == ["EV-0001"]
    assert review["validation_status"] == "passed"
    assert review["claims"][0]["evidence_ids"] == ["EV-0001"]
    assert trace["llm_review_status"] == "completed"
    assert trace["claim_review_validation_status"] == "passed"
    assert trace["claim_count"] == 1
    assert trace["rejected_claim_count"] == 0
    assert trace["validator_message_count"] == 0
    assert trace["missing_evidence_detection_status"] == "not_performed"
    assert trace["contradiction_detection_status"] == "not_performed"
    assert trace["project_evidence_markdown_report_status"] == "not_performed"
    assert trace["approval_decision_status"] == "not_performed"
    assert trace["go_live_decision_status"] == "not_performed"


def test_cli_validation_failure_writes_failed_artifact_and_trace(
    tmp_path: Path,
) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"
    response = _valid_response()
    response["claims"][0]["evidence_ids"] = ["EV-9999"]

    exit_code = main(
        [
            "--sources",
            str(sources),
            "--question",
            "What evidence shows testing is complete?",
            "--output-dir",
            str(output_dir),
        ],
        review_client=FakeReviewClient(json.dumps(response)),
    )

    trace = json.loads((output_dir / TRACE_FILE_NAME).read_text("utf-8"))
    review = json.loads((output_dir / CLAIM_REVIEW_FILE_NAME).read_text("utf-8"))
    assert exit_code == 1
    assert review["validation_status"] == "failed"
    assert trace["llm_review_status"] == "completed"
    assert trace["claim_review_validation_status"] == "failed"
    assert trace["rejected_claim_count"] == 1


def _valid_response() -> dict[str, object]:
    return {
        "claims": [
            {
                "claim_id": "CL-0001",
                "claim_text": (
                    "The supplied notes say smoke testing passed for release."
                ),
                "status": "evidence_supported",
                "evidence_ids": ["EV-0001"],
                "explanation": (
                    "The selected evidence states that smoke testing passed."
                ),
                "caveats": ["The supplied evidence is bounded to the selected chunk."],
            }
        ],
        "unsupported_or_unclear_points": [
            "The supplied evidence does not establish broader readiness."
        ],
        "review_caveats": ["This is bounded review material for human review."],
        "recommended_human_checks": ["Check the full test record and sign-off path."],
    }


def _evidence_pack() -> dict[str, object]:
    return {
        "question": "What evidence shows testing is complete?",
        "selected_chunks": [
            {
                "evidence_id": "EV-0001",
                "source_id": "SRC-0001",
                "source_path": "testing_notes.txt",
                "source_file_name": "testing_notes.txt",
                "source_type": "text",
                "start_line": 1,
                "end_line": 2,
                "text": "Smoke testing passed for release.",
                "text_preview": "Smoke testing passed for release.",
                "sha256": "abc123",
                "fingerprint_status": "recorded",
            }
        ],
        "source_map": {
            "SRC-0001": {
                "source_id": "SRC-0001",
                "source_path": "testing_notes.txt",
                "source_file_name": "testing_notes.txt",
                "source_type": "text",
                "sha256": "abc123",
                "fingerprint_status": "recorded",
            }
        },
    }


def _write_source_pack(path: Path) -> Path:
    path.mkdir()
    (path / "testing_notes.txt").write_text(
        "Smoke testing passed for release.\nHuman review is required.\n",
        encoding="utf-8",
    )
    return path
