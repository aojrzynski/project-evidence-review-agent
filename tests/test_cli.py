from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_evidence_review_agent import __version__
from project_evidence_review_agent.cli import main
from project_evidence_review_agent.evidence_index import EVIDENCE_INDEX_FILE_NAME
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
    assert trace["retrieval_status"] == "not_performed"
    assert trace["evidence_pack_status"] == "not_performed"
    assert trace["llm_review_status"] == "not_performed"
    assert trace["approval_decision_status"] == "not_performed"
    assert trace["go_live_decision_status"] == "not_performed"


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
        ["--sources", str(missing), "--question", "Q", "--output-dir", str(output_dir)]
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
        "Testing notes\nSmoke passed.\nRegression pending human review.\n",
        encoding="utf-8",
    )
    (path / "release_summary.json").write_text(
        json.dumps(
            {
                "release": "demo",
                "readiness_notes": ["synthetic note", "human review required"],
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
        "risk_id,description\nR-001,Synthetic risk\nR-002,Second synthetic risk\n",
        encoding="utf-8",
    )
    (path / "unsupported_document.pdf").write_text("unsupported", encoding="utf-8")
    return path


def _records_by_file_name(inventory_path: Path) -> dict[str, dict[str, object]]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    return {record["file_name"]: record for record in inventory["records"]}


def _read_evidence_index(output_dir: Path) -> dict[str, object]:
    return json.loads((output_dir / EVIDENCE_INDEX_FILE_NAME).read_text("utf-8"))
