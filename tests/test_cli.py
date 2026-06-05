from __future__ import annotations

import json

import pytest

from project_evidence_review_agent import __version__
from project_evidence_review_agent.cli import main
from project_evidence_review_agent.trace import TRACE_FILE_NAME


def test_cli_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "project-evidence-review" in output
    assert "--question" in output
    assert "--output-dir" in output


def test_cli_version_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert f"project-evidence-review {__version__}" in capsys.readouterr().out


def test_cli_writes_trace_with_question_and_scaffold_boundary(tmp_path) -> None:
    question = "Is the project ready for go-live?"
    output_dir = tmp_path / "scaffold_run"

    exit_code = main(["--question", question, "--output-dir", str(output_dir)])

    trace_path = output_dir / TRACE_FILE_NAME
    assert exit_code == 0
    assert trace_path.exists()

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["review_question"] == question
    assert trace["source_loading_status"] == "not_implemented"
    assert trace["evidence_review_status"] == "not_performed"
    assert "no sources were loaded" in trace["scaffold_note"]
    assert "no retrieval or LLM review was performed" in trace["scaffold_note"]
    assert "Human review remains the final authority" in trace["authority_boundary"]
