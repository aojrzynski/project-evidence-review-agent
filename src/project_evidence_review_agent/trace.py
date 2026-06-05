"""Create the PR #1 scaffold trace artifact.

The trace exists so a human can prove the command ran and see the exact boundary
of the current implementation. At this stage the project creates only a local
metadata artifact: it does not inspect project files, build evidence packs,
retrieve evidence, ask an LLM to review claims, or produce any readiness,
approval, legal, compliance, privacy, or security verdict.

Future workflow stages should preserve this explicit boundary style. Evidence
should be bounded, cited, and reviewable by a human before anyone relies on the
workflow output.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from project_evidence_review_agent.version import __version__

TRACE_FILE_NAME = "project_evidence_trace.json"
TOOL_NAME = "project-evidence-review"
AUTHORITY_BOUNDARY = (
    "This scaffold does not approve projects, certify readiness, replace "
    "governance, or make legal, compliance, privacy, security, or go-live "
    "decisions. Human review remains the final authority."
)
SCAFFOLD_NOTE = (
    "PR #1 scaffold run only: no sources were loaded, no evidence pack was "
    "created, no retrieval or LLM review was performed, and no project claim "
    "was evaluated."
)


def build_trace(question: str, output_dir: Path) -> dict[str, Any]:
    """Build the JSON-serializable trace payload for a scaffold-only run.

    Args:
        question: The human review question supplied to the CLI.
        output_dir: Directory where the trace artifact will be written.

    Returns:
        A dictionary that records the run metadata and makes the current
        non-review status explicit.
    """

    return {
        "tool_name": TOOL_NAME,
        "package_name": "project_evidence_review_agent",
        "package_version": __version__,
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "review_question": question,
        "output_directory": str(output_dir),
        "workflow_stage": "pr_001_repo_scaffold",
        "workflow_status": "scaffold_trace_only",
        "artifact": TRACE_FILE_NAME,
        "source_loading_status": "not_implemented",
        "evidence_review_status": "not_performed",
        "scaffold_note": SCAFFOLD_NOTE,
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_trace(question: str, output_dir: Path) -> Path:
    """Write the scaffold trace artifact and return its path.

    The output directory is created if needed. This is the only artifact PR #1
    writes; source inventories, evidence indexes, evidence packs, reports, and
    LLM outputs are deliberately outside this first scaffold.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / TRACE_FILE_NAME
    trace_payload = build_trace(question=question, output_dir=output_dir)
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return trace_path
