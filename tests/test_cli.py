from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_evidence_review_agent import __version__
from project_evidence_review_agent.cli import main
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

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["review_question"] == question
    assert trace["source_inventory_written"] is False
    assert trace["loaded_source_count"] == 0
    assert trace["skipped_source_count"] == 0
    assert trace["source_loading_status"] == "not_requested"
    assert trace["evidence_review_status"] == "not_performed"
    assert "no chunking was performed" in trace["scaffold_note"]
    assert "no retrieval or LLM review was performed" in trace["scaffold_note"]
    assert "Human review remains the final authority" in trace["authority_boundary"]


def test_cli_with_sources_writes_source_inventory_and_trace_counts(
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
    trace_path = output_dir / TRACE_FILE_NAME
    assert exit_code == 0
    assert inventory_path.exists()
    assert trace_path.exists()

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert inventory["summary"]["loaded_sources"] == 5
    assert inventory["summary"]["skipped_sources"] == 1
    assert trace["source_inventory_written"] is True
    assert trace["loaded_source_count"] == 5
    assert trace["skipped_source_count"] == 1
    assert trace["chunking_status"] == "not_performed"
    assert trace["retrieval_status"] == "not_performed"
    assert trace["llm_review_status"] == "not_performed"
    assert trace["approval_decision_status"] == "not_performed"


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
    skipped = records["unsupported_document.pdf"]
    assert skipped["status"] == "skipped"
    assert "unsupported file extension" in skipped["skip_reason"]


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


def test_single_markdown_file_can_be_inventoried(tmp_path: Path) -> None:
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
    assert inventory["source_path_type"] == "file"
    assert inventory["records"][0]["source_id"] == "SRC-0001"
    assert inventory["records"][0]["file_name"] == "requirements.md"


def _write_source_pack(path: Path) -> Path:
    path.mkdir()
    (path / "requirements.md").write_text(
        "# Requirements\n\nSynthetic requirement.\n", encoding="utf-8"
    )
    (path / "testing_notes.txt").write_text(
        "Testing notes\nSmoke passed.\n", encoding="utf-8"
    )
    (path / "release_summary.json").write_text(
        '{"release": "demo", "ready_for_review": true}\n',
        encoding="utf-8",
    )
    (path / "project_config.yaml").write_text(
        "project_name: demo\nreview_required: true\n",
        encoding="utf-8",
    )
    (path / "risk_log.csv").write_text(
        "risk_id,description\nR-001,Synthetic risk\n",
        encoding="utf-8",
    )
    (path / "unsupported_document.pdf").write_text("unsupported", encoding="utf-8")
    return path


def _records_by_file_name(inventory_path: Path) -> dict[str, dict[str, object]]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    return {record["file_name"]: record for record in inventory["records"]}
