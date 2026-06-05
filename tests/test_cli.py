from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_evidence_review_agent import __version__
from project_evidence_review_agent.claim_review import CLAIM_REVIEW_FILE_NAME
from project_evidence_review_agent.cli import main
from project_evidence_review_agent.contradictions import CONTRADICTION_LOG_FILE_NAME
from project_evidence_review_agent.evidence_index import EVIDENCE_INDEX_FILE_NAME
from project_evidence_review_agent.evidence_pack_markdown import (
    EVIDENCE_PACK_MARKDOWN_FILE_NAME,
    render_evidence_pack_markdown,
)
from project_evidence_review_agent.missing_evidence import MISSING_EVIDENCE_FILE_NAME
from project_evidence_review_agent.project_report import (
    PROJECT_EVIDENCE_REPORT_FILE_NAME,
)
from project_evidence_review_agent.retrieval import (
    EVIDENCE_PACK_FILE_NAME,
    RETRIEVAL_TRACE_FILE_NAME,
)
from project_evidence_review_agent.review_question import REVIEW_QUESTION_FILE_NAME
from project_evidence_review_agent.source_inventory import SOURCE_INVENTORY_FILE_NAME
from project_evidence_review_agent.trace import TRACE_FILE_NAME


def test_cli_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "project-evidence-review" in output
    assert "--question" in output
    assert "--output-dir" in output
    assert "--sources" in output
    assert "--max-chunks" in output
    assert "--no-llm" in output
    assert "--llm-model" in output
    assert "--orchestrator" in output


def test_cli_version_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert f"project-evidence-review {__version__}" in capsys.readouterr().out


def test_cli_works_without_sources_preserving_scaffold_boundary(tmp_path: Path) -> None:
    question = "Is the project ready for go-live?"
    output_dir = tmp_path / "scaffold_run"

    exit_code = main(["--question", question, "--output-dir", str(output_dir)])

    trace_path = output_dir / TRACE_FILE_NAME
    assert exit_code == 0
    assert trace_path.exists()
    assert not (output_dir / SOURCE_INVENTORY_FILE_NAME).exists()
    assert not (output_dir / EVIDENCE_INDEX_FILE_NAME).exists()
    assert not (output_dir / EVIDENCE_PACK_MARKDOWN_FILE_NAME).exists()

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["review_question"] == question
    assert trace["source_inventory_written"] is False
    assert trace["evidence_index_written"] is False
    assert trace["loaded_source_count"] == 0
    assert trace["skipped_source_count"] == 0
    assert trace["evidence_chunk_count"] == 0
    assert trace["source_loading_status"] == "not_requested"
    assert trace["chunking_status"] == "not_requested"
    assert trace["evidence_review_status"] == "not_performed"
    assert trace["retrieval_status"] == "not_performed"
    assert trace["evidence_pack_status"] == "not_performed"
    assert trace["llm_review_status"] == "not_performed"
    assert trace["approval_decision_status"] == "not_performed"
    assert trace["go_live_decision_status"] == "not_performed"
    assert trace["review_question_written"] is False
    assert trace["retrieval_trace_written"] is False
    assert trace["evidence_pack_written"] is False
    assert trace["evidence_pack_markdown_written"] is False
    assert trace["evidence_pack_markdown_status"] == "not_performed"
    assert trace["evidence_pack_markdown_path"] is None
    assert "no retrieval" in trace["scaffold_note"]
    assert "no LLM review was performed" in trace["scaffold_note"]
    assert "Human review remains the final authority" in trace["authority_boundary"]


def test_cli_with_sources_writes_inventory_evidence_index_and_trace_counts(
    tmp_path: Path,
) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "source_inventory_run"

    exit_code = main(
        [
            "--sources",
            str(sources),
            "--question",
            "Is the project ready for go-live?",
            "--no-llm",
            "--output-dir",
            str(output_dir),
        ]
    )

    inventory_path = output_dir / SOURCE_INVENTORY_FILE_NAME
    evidence_index_path = output_dir / EVIDENCE_INDEX_FILE_NAME
    trace_path = output_dir / TRACE_FILE_NAME
    assert exit_code == 0
    assert inventory_path.exists()
    assert evidence_index_path.exists()
    assert trace_path.exists()
    assert (output_dir / REVIEW_QUESTION_FILE_NAME).exists()
    assert (output_dir / RETRIEVAL_TRACE_FILE_NAME).exists()
    assert (output_dir / EVIDENCE_PACK_FILE_NAME).exists()
    assert (output_dir / EVIDENCE_PACK_MARKDOWN_FILE_NAME).exists()
    assert not (output_dir / MISSING_EVIDENCE_FILE_NAME).exists()
    assert not (output_dir / CONTRADICTION_LOG_FILE_NAME).exists()
    assert not (output_dir / PROJECT_EVIDENCE_REPORT_FILE_NAME).exists()

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    evidence_index = json.loads(evidence_index_path.read_text(encoding="utf-8"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert inventory["summary"]["loaded_sources"] == 5
    assert inventory["summary"]["skipped_sources"] == 1
    assert evidence_index["summary"]["loaded_sources_considered"] == 5
    assert evidence_index["summary"]["evidence_chunks"] > 0
    assert trace["source_inventory_written"] is True
    assert trace["evidence_index_written"] is True
    assert trace["loaded_source_count"] == 5
    assert trace["skipped_source_count"] == 1
    assert trace["evidence_chunk_count"] == evidence_index["summary"]["evidence_chunks"]
    assert trace["chunking_status"] == "completed"
    assert trace["review_question_written"] is True
    assert trace["retrieval_trace_written"] is True
    assert trace["evidence_pack_written"] is True
    assert trace["evidence_pack_markdown_written"] is True
    assert trace["evidence_pack_markdown_status"] == "completed"
    assert trace["evidence_pack_markdown_path"].endswith(
        EVIDENCE_PACK_MARKDOWN_FILE_NAME
    )
    assert trace["retrieval_status"] == "completed"
    assert trace["evidence_pack_status"] == "completed"
    assert trace["llm_review_status"] == "skipped_no_llm"
    assert trace["approval_decision_status"] == "not_performed"
    assert trace["go_live_decision_status"] == "not_performed"
    assert trace["missing_evidence_detection_status"] == "skipped_no_llm"
    assert trace["contradiction_detection_status"] == "skipped_no_llm"
    assert trace["project_evidence_report_written"] is False
    assert trace["project_evidence_report_status"] == "skipped_no_llm"
    assert trace["markdown_report_status"] == "skipped_no_llm"
    assert trace["project_evidence_report_written"] is False
    assert trace["project_evidence_report_status"] == "skipped_no_llm"
    assert trace["project_evidence_markdown_report_status"] == "skipped_no_llm"
    assert trace["max_chunks"] == 10


def test_cli_with_sources_writes_readable_evidence_pack_markdown(
    tmp_path: Path,
) -> None:
    question = "Which synthetic testing release risks need human review?"
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "markdown_run"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                question,
                "--max-chunks",
                "4",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    evidence_pack = _read_json(output_dir / EVIDENCE_PACK_FILE_NAME)
    markdown = (output_dir / EVIDENCE_PACK_MARKDOWN_FILE_NAME).read_text("utf-8")
    trace = _read_json(output_dir / TRACE_FILE_NAME)

    assert question in markdown
    assert "# Evidence Pack" in markdown
    assert "## Important boundary" in markdown
    assert "review preparation, not project approval" in markdown
    assert "A selected chunk is not automatically supporting evidence" in markdown
    assert "No LLM was used" in markdown
    assert "Human review remains the final authority" in markdown
    assert "Matched terms" in markdown
    assert "Retrieval score" in markdown
    assert "Reference: lines" in markdown or "Reference: rows" in markdown
    assert "```text" in markdown
    assert "| Source ID | File name | Path | Type | Fingerprint |" in markdown
    assert "go-live is approved" not in markdown.lower()
    assert "project is approved" not in markdown.lower()
    assert "claim is supported" not in markdown.lower()
    assert "claim is contradicted" not in markdown.lower()

    selected_chunks = evidence_pack["selected_chunks"]
    assert selected_chunks
    for chunk in selected_chunks:
        assert chunk["evidence_id"] in markdown
        assert chunk["source_id"] in markdown
        assert chunk["source_file_name"] in markdown
        assert chunk["source_path"] in markdown
        assert str(chunk["retrieval_score"]) in markdown
        for term in chunk["matched_terms"]:
            assert f"`{term}`" in markdown
        if "start_line" in chunk:
            assert f"lines {chunk['start_line']}-{chunk['end_line']}" in markdown
        if "start_row" in chunk:
            assert f"rows {chunk['start_row']}-{chunk['end_row']}" in markdown

    assert trace["evidence_pack_markdown_written"] is True
    assert trace["selected_evidence_chunk_count"] == len(selected_chunks)
    assert trace["llm_review_status"] == "skipped_no_llm"
    assert trace["missing_evidence_detection_status"] == "skipped_no_llm"
    assert trace["contradiction_detection_status"] == "skipped_no_llm"
    assert trace["project_evidence_report_written"] is False
    assert trace["project_evidence_report_status"] == "skipped_no_llm"
    assert trace["project_evidence_markdown_report_status"] == "skipped_no_llm"
    assert trace["approval_decision_status"] == "not_performed"


def test_markdown_renderer_is_deterministic_and_non_interpretive() -> None:
    payload = {
        "question": "Do synthetic tests mention release risk?",
        "retrieval_strategy": "deterministic_term_overlap_v1",
        "max_chunks": 2,
        "selected_chunk_count": 1,
        "selected_chunks": [
            {
                "evidence_id": "EV-0001",
                "source_id": "SRC-0001",
                "source_path": "synthetic/testing_notes.txt",
                "source_file_name": "testing_notes.txt",
                "source_type": "text",
                "start_line": 1,
                "end_line": 2,
                "text": "Synthetic release risk note for human review.",
                "matched_terms": ["release", "risk"],
                "retrieval_score": 6,
                "sha256": "abcdef1234567890",
                "fingerprint_status": "recorded",
            }
        ],
        "source_map": {
            "SRC-0001": {
                "source_id": "SRC-0001",
                "source_path": "synthetic/testing_notes.txt",
                "source_file_name": "testing_notes.txt",
                "source_type": "text",
                "sha256": "abcdef1234567890",
                "fingerprint_status": "recorded",
            }
        },
        "limitations": ["Synthetic limitation."],
    }

    first = render_evidence_pack_markdown(payload)
    second = render_evidence_pack_markdown(payload)

    assert first == second
    assert "EV-0001" in first
    assert "SRC-0001" in first
    assert "testing_notes.txt" in first
    assert "lines 1-2" in first
    assert "review preparation, not project approval" in first
    assert "not automatically supporting evidence" in first
    assert "No LLM was used" in first
    assert "claim is supported" not in first.lower()


def test_review_question_retrieval_and_evidence_pack_artifacts(tmp_path: Path) -> None:
    question = "Is the project ready for go-live testing release risks?"
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "retrieval_run"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                question,
                "--max-chunks",
                "3",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    review_question = _read_json(output_dir / REVIEW_QUESTION_FILE_NAME)
    retrieval_trace = _read_json(output_dir / RETRIEVAL_TRACE_FILE_NAME)
    evidence_pack = _read_json(output_dir / EVIDENCE_PACK_FILE_NAME)
    trace = _read_json(output_dir / TRACE_FILE_NAME)

    assert review_question["question"] == question
    assert "go-live" in review_question["question_terms"]
    assert retrieval_trace["question"] == question
    assert retrieval_trace["max_chunks"] == 3
    assert 0 < retrieval_trace["selected_chunk_count"] <= 3
    assert (
        evidence_pack["selected_chunk_count"] == retrieval_trace["selected_chunk_count"]
    )
    assert (
        trace["selected_evidence_chunk_count"] == evidence_pack["selected_chunk_count"]
    )

    selected = retrieval_trace["selected_chunks"]
    assert any("go-live" in chunk["matched_terms"] for chunk in selected)
    assert all(chunk["scoring_reasons"] for chunk in selected)
    assert all(chunk["evidence_id"].startswith("EV-") for chunk in selected)
    assert all(chunk["source_id"].startswith("SRC-") for chunk in selected)

    pack_chunks = evidence_pack["selected_chunks"]
    assert all(chunk["text"] for chunk in pack_chunks)
    assert all(chunk["evidence_id"] and chunk["source_id"] for chunk in pack_chunks)
    assert any("start_line" in chunk or "start_row" in chunk for chunk in pack_chunks)
    assert "unsupported_document.pdf" not in {
        chunk["source_file_name"] for chunk in pack_chunks
    }
    assert evidence_pack["source_map"]


def test_max_chunks_rejects_non_positive_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exc_info:
        main(["--question", "Q", "--max-chunks", "0", "--output-dir", str(output_dir)])

    assert exc_info.value.code == 2
    assert "--max-chunks must be a positive integer" in capsys.readouterr().err


def test_retrieval_is_deterministic_across_repeated_runs(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    first_output = tmp_path / "out1"
    second_output = tmp_path / "out2"
    question = "go-live testing risks release"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                question,
                "--no-llm",
                "--output-dir",
                str(first_output),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                question,
                "--no-llm",
                "--output-dir",
                str(second_output),
            ]
        )
        == 0
    )

    first_trace = _read_json(first_output / RETRIEVAL_TRACE_FILE_NAME)
    second_trace = _read_json(second_output / RETRIEVAL_TRACE_FILE_NAME)
    first_pack = _read_json(first_output / EVIDENCE_PACK_FILE_NAME)
    second_pack = _read_json(second_output / EVIDENCE_PACK_FILE_NAME)
    first_markdown = (first_output / EVIDENCE_PACK_MARKDOWN_FILE_NAME).read_text(
        "utf-8"
    )
    second_markdown = (second_output / EVIDENCE_PACK_MARKDOWN_FILE_NAME).read_text(
        "utf-8"
    )
    assert first_trace == second_trace
    assert first_pack == second_pack
    assert first_markdown == second_markdown


def test_source_fingerprints_present_for_loaded_files(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "testing",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    inventory = _read_json(output_dir / SOURCE_INVENTORY_FILE_NAME)
    loaded = [record for record in inventory["records"] if record["status"] == "loaded"]
    assert loaded
    assert all(record["fingerprint_status"] == "recorded" for record in loaded)
    assert all(record["sha256"] for record in loaded)
    chunks = _read_evidence_index(output_dir)["chunks"]
    assert all(chunk["source_consistency_status"] == "consistent" for chunk in chunks)


def test_supported_source_types_are_loaded(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    records = _records_by_file_name(output_dir / SOURCE_INVENTORY_FILE_NAME)
    assert records["requirements.md"]["status"] == "loaded"
    assert records["requirements.md"]["source_type"] == "markdown"
    assert records["requirements.md"]["parser"] == "utf-8-text"
    assert records["testing_notes.txt"]["status"] == "loaded"
    assert records["testing_notes.txt"]["source_type"] == "text"
    assert records["release_summary.json"]["status"] == "loaded"
    assert records["release_summary.json"]["json_top_level_type"] == "dict"
    assert records["project_config.yaml"]["status"] == "loaded"
    assert records["project_config.yaml"]["yaml_top_level_type"] == "dict"
    assert records["risk_log.csv"]["status"] == "loaded"
    assert records["risk_log.csv"]["column_names"] == ["risk_id", "description"]


def test_evidence_index_chunks_supported_source_types(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    evidence_index = _read_evidence_index(output_dir)
    chunks = evidence_index["chunks"]
    source_types = {chunk["source_type"] for chunk in chunks}
    assert {"markdown", "text", "json", "yaml", "csv"}.issubset(source_types)
    assert all(chunk["source_id"].startswith("SRC-") for chunk in chunks)
    assert all(chunk["char_count"] <= 2000 for chunk in chunks)
    assert all(chunk["text_preview"] for chunk in chunks)
    assert "unsupported_document.pdf" not in {
        chunk["source_file_name"] for chunk in chunks
    }


def test_evidence_ids_are_stable_and_deterministic(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    first_output = tmp_path / "out1"
    second_output = tmp_path / "out2"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(first_output),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(second_output),
            ]
        )
        == 0
    )

    first_chunks = _read_evidence_index(first_output)["chunks"]
    second_chunks = _read_evidence_index(second_output)["chunks"]
    assert [chunk["evidence_id"] for chunk in first_chunks] == [
        f"EV-{index:04d}" for index in range(1, len(first_chunks) + 1)
    ]
    assert first_chunks == second_chunks


def test_markdown_and_text_chunks_include_line_numbers(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    chunks = _read_evidence_index(output_dir)["chunks"]
    markdown_chunks = [chunk for chunk in chunks if chunk["source_type"] == "markdown"]
    text_chunks = [chunk for chunk in chunks if chunk["source_type"] == "text"]
    assert markdown_chunks
    assert text_chunks
    assert all(
        "start_line" in chunk and "end_line" in chunk for chunk in markdown_chunks
    )
    assert all("start_line" in chunk and "end_line" in chunk for chunk in text_chunks)
    assert {chunk["heading"] for chunk in markdown_chunks} >= {
        "Requirements",
        "Operational checks",
    }


def test_csv_chunks_include_row_references(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack")
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    csv_chunks = [
        chunk
        for chunk in _read_evidence_index(output_dir)["chunks"]
        if chunk["source_type"] == "csv"
    ]
    assert csv_chunks
    assert csv_chunks[0]["start_row"] == 2
    assert csv_chunks[0]["end_row"] == 3
    assert "Columns: risk_id, description" in csv_chunks[0]["text"]


def test_unsupported_file_extension_is_skipped_with_reason(tmp_path: Path) -> None:
    sources = tmp_path / "project_pack"
    sources.mkdir()
    (sources / "unsupported_document.pdf").write_text("not parsed", encoding="utf-8")
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    records = _records_by_file_name(output_dir / SOURCE_INVENTORY_FILE_NAME)
    evidence_index = _read_evidence_index(output_dir)
    skipped = records["unsupported_document.pdf"]
    assert skipped["status"] == "skipped"
    assert "unsupported file extension" in skipped["skip_reason"]
    assert evidence_index["chunks"] == []
    assert evidence_index["summary"]["skipped_sources_excluded"] == 1


def test_missing_sources_path_gives_clean_nonzero_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "out"
    missing = tmp_path / "missing"

    exit_code = main(
        [
            "--sources",
            str(missing),
            "--question",
            "Q",
            "--no-llm",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 1
    assert "--sources path does not exist" in capsys.readouterr().err
    assert not (output_dir / SOURCE_INVENTORY_FILE_NAME).exists()
    assert not (output_dir / EVIDENCE_INDEX_FILE_NAME).exists()


def test_single_markdown_file_can_be_inventoried_and_indexed(tmp_path: Path) -> None:
    source_file = tmp_path / "requirements.md"
    source_file.write_text("# Requirements\n\nSynthetic note.\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--sources",
                str(source_file),
                "--question",
                "Q",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    inventory = json.loads(
        (output_dir / SOURCE_INVENTORY_FILE_NAME).read_text(encoding="utf-8")
    )
    evidence_index = _read_evidence_index(output_dir)
    assert inventory["source_path_type"] == "file"
    assert inventory["records"][0]["source_id"] == "SRC-0001"
    assert inventory["records"][0]["file_name"] == "requirements.md"
    assert evidence_index["chunks"][0]["evidence_id"] == "EV-0001"
    assert evidence_index["chunks"][0]["source_id"] == "SRC-0001"


def _write_source_pack(path: Path) -> Path:
    path.mkdir()
    (path / "requirements.md").write_text(
        "# Requirements\n\n"
        "Synthetic requirement.\n\n"
        "## Operational checks\n\n"
        "Synthetic operations checklist item.\n",
        encoding="utf-8",
    )
    (path / "testing_notes.txt").write_text(
        "Testing notes\n"
        "Smoke testing passed for release.\n"
        "Regression pending human review before go-live.\n",
        encoding="utf-8",
    )
    (path / "release_summary.json").write_text(
        json.dumps(
            {
                "release": "demo go-live",
                "readiness_notes": ["synthetic release note", "human review required"],
                "ready_for_review": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "project_config.yaml").write_text(
        "project_name: demo\nreview_required: true\nowners:\n  - synthetic-team\n",
        encoding="utf-8",
    )
    (path / "risk_log.csv").write_text(
        "risk_id,description\n"
        "R-001,Synthetic go-live risk\n"
        "R-002,Second synthetic release risk\n",
        encoding="utf-8",
    )
    (path / "unsupported_document.pdf").write_text("unsupported", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _records_by_file_name(inventory_path: Path) -> dict[str, dict[str, object]]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    return {record["file_name"]: record for record in inventory["records"]}


def _read_evidence_index(output_dir: Path) -> dict[str, object]:
    return json.loads((output_dir / EVIDENCE_INDEX_FILE_NAME).read_text("utf-8"))


def test_default_cli_trace_records_standard_orchestrator(tmp_path: Path) -> None:
    sources = _write_source_pack(tmp_path / "project_pack_orchestrator_default")
    output_dir = tmp_path / "orchestrator_default"

    assert (
        main(
            [
                "--sources",
                str(sources),
                "--question",
                "What evidence shows testing is complete?",
                "--no-llm",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    trace = _read_json(output_dir / TRACE_FILE_NAME)
    assert trace["orchestrator"] == "standard"
    assert trace["langgraph_requested"] is False
    assert trace["langgraph_available"] is None
    assert trace["graph_orchestration_status"] == "not_used"
    assert trace["graph_node_statuses"] == {}
    assert trace["workflow_stage"] == "pr_009_optional_orchestration"
    assert "PR #9 run with optional orchestration metadata" in trace["scaffold_note"]
    assert "PR #8 run" not in trace["scaffold_note"]


def test_explicit_standard_orchestrator_matches_default_artifact_names(
    tmp_path: Path,
) -> None:
    sources = _write_source_pack(tmp_path / "project_pack_standard")
    default_output = tmp_path / "default"
    standard_output = tmp_path / "standard"
    argv = [
        "--sources",
        str(sources),
        "--question",
        "go-live testing risks release",
        "--max-chunks",
        "3",
        "--no-llm",
    ]

    assert main([*argv, "--output-dir", str(default_output)]) == 0
    assert (
        main(
            [
                *argv,
                "--orchestrator",
                "standard",
                "--output-dir",
                str(standard_output),
            ]
        )
        == 0
    )

    assert _artifact_names(default_output) == _artifact_names(standard_output)
    default_pack = _read_json(default_output / EVIDENCE_PACK_FILE_NAME)
    standard_pack = _read_json(standard_output / EVIDENCE_PACK_FILE_NAME)
    assert [c["evidence_id"] for c in default_pack["selected_chunks"]] == [
        c["evidence_id"] for c in standard_pack["selected_chunks"]
    ]


def test_langgraph_orchestrator_missing_dependency_fails_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from project_evidence_review_agent.langgraph_workflow import (
        LANGGRAPH_INSTALL_MESSAGE,
        LangGraphUnavailableError,
    )

    def raise_unavailable(*_args: object, **_kwargs: object) -> None:
        raise LangGraphUnavailableError(LANGGRAPH_INSTALL_MESSAGE)

    monkeypatch.setattr(
        "project_evidence_review_agent.cli.run_langgraph_workflow",
        raise_unavailable,
    )
    output_dir = tmp_path / "langgraph_missing"

    exit_code = main(
        [
            "--question",
            "Q",
            "--orchestrator",
            "langgraph",
            "--output-dir",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "pip install -e '.[graph]'" in captured.err
    assert "Traceback" not in captured.err


def test_langgraph_orchestrator_no_llm_matches_standard_when_available(
    tmp_path: Path,
) -> None:
    pytest.importorskip("langgraph", reason="optional graph dependencies not installed")
    sources = _write_source_pack(tmp_path / "project_pack_langgraph")
    standard_output = tmp_path / "standard"
    graph_output = tmp_path / "langgraph"
    argv = [
        "--sources",
        str(sources),
        "--question",
        "go-live testing risks release",
        "--max-chunks",
        "3",
        "--no-llm",
    ]

    assert (
        main(
            [
                *argv,
                "--orchestrator",
                "standard",
                "--output-dir",
                str(standard_output),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                *argv,
                "--orchestrator",
                "langgraph",
                "--output-dir",
                str(graph_output),
            ]
        )
        == 0
    )

    assert _artifact_names(standard_output) == _artifact_names(graph_output)
    assert not (graph_output / CLAIM_REVIEW_FILE_NAME).exists()
    assert not (graph_output / MISSING_EVIDENCE_FILE_NAME).exists()
    assert not (graph_output / CONTRADICTION_LOG_FILE_NAME).exists()
    assert (graph_output / EVIDENCE_PACK_MARKDOWN_FILE_NAME).exists()

    standard_trace = _read_json(standard_output / TRACE_FILE_NAME)
    graph_trace = _read_json(graph_output / TRACE_FILE_NAME)
    for key in [
        "loaded_source_count",
        "skipped_source_count",
        "evidence_chunk_count",
        "selected_evidence_chunk_count",
        "llm_review_status",
        "missing_evidence_detection_status",
        "contradiction_detection_status",
        "project_evidence_report_status",
    ]:
        assert standard_trace[key] == graph_trace[key]
    assert graph_trace["orchestrator"] == "langgraph"
    assert graph_trace["graph_orchestration_status"] == "completed"


def test_langgraph_full_fake_llm_happy_path_writes_validated_artifacts(
    tmp_path: Path,
) -> None:
    pytest.importorskip("langgraph", reason="optional graph dependencies not installed")
    sources = _write_source_pack(tmp_path / "project_pack_langgraph_full")
    output_dir = tmp_path / "langgraph_full"
    client = _FakeReviewClient(
        json.dumps(_valid_fake_claim_response("__FIRST_ALLOWED__")),
        follow_up_response=json.dumps(
            {"missing_evidence": [], "contradiction_candidates": []}
        ),
    )

    exit_code = main(
        [
            "--sources",
            str(sources),
            "--question",
            "What evidence shows testing is complete?",
            "--llm-model",
            "fake-model",
            "--orchestrator",
            "langgraph",
            "--output-dir",
            str(output_dir),
        ],
        review_client=client,
    )

    trace = _read_json(output_dir / TRACE_FILE_NAME)
    assert exit_code == 0
    assert client.calls == 1
    assert client.follow_up_calls == 1
    assert (output_dir / CLAIM_REVIEW_FILE_NAME).exists()
    assert (output_dir / MISSING_EVIDENCE_FILE_NAME).exists()
    assert (output_dir / CONTRADICTION_LOG_FILE_NAME).exists()
    assert (output_dir / PROJECT_EVIDENCE_REPORT_FILE_NAME).exists()
    assert (output_dir / TRACE_FILE_NAME).exists()
    assert trace["orchestrator"] == "langgraph"
    assert trace["graph_orchestration_status"] == "completed"
    assert trace["approval_decision_status"] == "not_performed"
    assert trace["go_live_decision_status"] == "not_performed"


class _FakeReviewClient:
    def __init__(
        self,
        response: str,
        *,
        follow_up_response: str,
    ) -> None:
        self.response = response
        self.follow_up_response = follow_up_response
        self.calls = 0
        self.follow_up_calls = 0

    def review_claims(self, prompt: str, *, model: str) -> str:
        assert model == "fake-model"
        self.calls += 1
        response = json.loads(self.response)
        allowed_ids = json.loads(prompt)["allowed_evidence_ids"]
        for claim in response["claims"]:
            if claim["evidence_ids"] == ["__FIRST_ALLOWED__"]:
                claim["evidence_ids"] = [allowed_ids[0]]
        return json.dumps(response)

    def review_follow_up_analysis(self, _prompt: str, *, model: str) -> str:
        assert model == "fake-model"
        self.follow_up_calls += 1
        return self.follow_up_response


def _valid_fake_claim_response(evidence_id: str) -> dict[str, object]:
    return {
        "claims": [
            {
                "claim_id": "CL-0001",
                "claim_text": "The supplied evidence contains testing material.",
                "status": "evidence_supported",
                "evidence_ids": [evidence_id],
                "explanation": "The selected evidence includes a cited evidence ID.",
                "caveats": ["This is bounded to selected local evidence."],
            }
        ],
        "unsupported_or_unclear_points": [],
        "review_caveats": ["Human review remains required."],
        "recommended_human_checks": ["Check the cited testing evidence."],
    }


def _artifact_names(output_dir: Path) -> set[str]:
    return {path.name for path in output_dir.iterdir() if path.is_file()}
