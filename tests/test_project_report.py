from __future__ import annotations

from project_evidence_review_agent.project_report import render_project_evidence_report


def test_project_report_renderer_preserves_ids_sections_and_is_deterministic() -> None:
    first = render_project_evidence_report(
        evidence_pack=_evidence_pack(),
        claim_review=_claim_review(),
        missing_evidence=_missing_evidence(),
        contradiction_log=_contradiction_log(),
        trace_summary={
            "loaded_source_count": 1,
            "skipped_source_count": 0,
            "evidence_chunk_count": 2,
            "project_evidence_report_status": "written",
        },
    )
    second = render_project_evidence_report(
        evidence_pack=_evidence_pack(),
        claim_review=_claim_review(),
        missing_evidence=_missing_evidence(),
        contradiction_log=_contradiction_log(),
        trace_summary={
            "loaded_source_count": 1,
            "skipped_source_count": 0,
            "evidence_chunk_count": 2,
            "project_evidence_report_status": "written",
        },
    )

    assert first == second
    for section in [
        "# Project Evidence Report",
        "## Review question",
        "## Evidence-supported points",
        "## Missing evidence signals",
        "## Possible contradiction candidates",
        "## Selected evidence map",
        "## Source map",
        "## Recommended human checks",
        "## Limitations",
        "## Authority boundary",
    ]:
        assert section in first
    for expected_id in [
        "CL-0001",
        "CL-0002",
        "EV-0001",
        "EV-0002",
        "ME-0001",
        "CON-0001",
        "SRC-0001",
    ]:
        assert expected_id in first
    assert "What evidence shows testing is complete?" in first
    assert "Check the full test record." in first
    assert "Check whether a final sign-off record exists." in first
    assert "Compare the test note and review note." in first
    assert "Missing evidence is a gap signal" in first
    assert "not proof that the evidence does not exist elsewhere" in first
    assert "possible tensions in the supplied evidence" in first
    assert "not final findings" in first
    assert "This report is review material, not project approval." in first
    assert "The agent cannot approve go-live." in first
    assert "go-live is approved" not in first.lower()
    assert "project is approved" not in first.lower()


def test_project_report_renderer_handles_empty_valid_lists() -> None:
    report = render_project_evidence_report(
        evidence_pack={
            "question": "What evidence exists?",
            "selected_chunks": [],
            "source_map": {},
            "limitations": [],
        },
        claim_review={
            "llm_review_status": "completed",
            "validation_status": "passed",
            "claims": [],
            "recommended_human_checks": [],
            "limitations": [],
        },
        missing_evidence={
            "validation_status": "passed",
            "missing_evidence": [],
            "limitations": [],
        },
        contradiction_log={
            "validation_status": "passed",
            "contradiction_candidates": [],
            "limitations": [],
        },
        trace_summary={"project_evidence_report_status": "written"},
    )

    assert "No evidence-supported claims were included" in report
    assert "No missing evidence signals were returned" in report
    assert "No contradiction candidates were returned" in report
    assert "This does not mean there are no gaps in the real project" in report
    assert (
        "This does not mean there are no contradictions in the real project" in report
    )


def _evidence_pack() -> dict[str, object]:
    return {
        "question": "What evidence shows testing is complete?",
        "selected_chunk_count": 2,
        "selected_chunks": [
            {
                "evidence_id": "EV-0001",
                "source_id": "SRC-0001",
                "source_file_name": "testing_notes.txt",
                "source_path": "testing_notes.txt",
                "source_type": "text",
                "start_line": 1,
                "end_line": 2,
                "matched_terms": ["testing"],
                "retrieval_score": 4,
            },
            {
                "evidence_id": "EV-0002",
                "source_id": "SRC-0001",
                "source_file_name": "testing_notes.txt",
                "source_path": "testing_notes.txt",
                "source_type": "text",
                "start_line": 3,
                "end_line": 4,
                "matched_terms": ["review"],
                "retrieval_score": 2,
            },
        ],
        "source_map": {
            "SRC-0001": {
                "source_id": "SRC-0001",
                "source_file_name": "testing_notes.txt",
                "source_path": "testing_notes.txt",
                "source_type": "text",
                "sha256": "abcdef1234567890",
                "fingerprint_status": "recorded",
            }
        },
        "limitations": ["Synthetic retrieval limitation."],
    }


def _claim_review() -> dict[str, object]:
    return {
        "llm_review_status": "completed",
        "validation_status": "passed",
        "claims": [
            {
                "claim_id": "CL-0001",
                "claim_text": "The supplied notes say smoke testing passed.",
                "status": "evidence_supported",
                "evidence_ids": ["EV-0001"],
                "explanation": "The selected evidence states smoke testing passed.",
                "caveats": ["Bounded to selected evidence."],
            },
            {
                "claim_id": "CL-0002",
                "claim_text": "A final sign-off artifact is visible.",
                "status": "unclear_from_supplied_evidence",
                "evidence_ids": [],
                "explanation": "The selected evidence does not include that artifact.",
                "caveats": ["Other files may contain it."],
            },
        ],
        "recommended_human_checks": ["Check the full test record."],
        "limitations": ["Synthetic claim limitation."],
    }


def _missing_evidence() -> dict[str, object]:
    return {
        "validation_status": "passed",
        "missing_evidence": [
            {
                "missing_evidence_id": "ME-0001",
                "gap_type": "evidence_not_found",
                "summary": "No final sign-off record is in the selected evidence.",
                "details": "The selected chunks mention smoke tests only.",
                "related_claim_ids": ["CL-0002"],
                "related_evidence_ids": [],
                "suggested_human_check": (
                    "Check whether a final sign-off record exists."
                ),
                "why_it_matters": "A human may need to inspect the boundary.",
                "confidence": "medium",
            }
        ],
        "limitations": ["Synthetic missing evidence limitation."],
    }


def _contradiction_log() -> dict[str, object]:
    return {
        "validation_status": "passed",
        "contradiction_candidates": [
            {
                "contradiction_id": "CON-0001",
                "summary": (
                    "Testing passed and review remained open may need comparison."
                ),
                "evidence_side_a": {
                    "evidence_ids": ["EV-0001"],
                    "description": "Smoke testing passed.",
                },
                "evidence_side_b": {
                    "evidence_ids": ["EV-0002"],
                    "description": "Review remained open.",
                },
                "explanation": "The chunks may describe different steps.",
                "related_claim_ids": ["CL-0001"],
                "suggested_human_check": "Compare the test note and review note.",
                "confidence": "low",
            }
        ],
        "limitations": ["Synthetic contradiction limitation."],
    }
