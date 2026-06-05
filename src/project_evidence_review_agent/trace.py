"""Create the project evidence trace artifact.

The trace exists so a human can prove the command ran and see the exact boundary
of the current implementation. PR #2 can inventory local source files before any
evidence processing happens. Source inventory exists before chunking so later
work can start from a deterministic list of supplied, bounded local material.

This stage still does not chunk documents, build evidence packs, retrieve
evidence, ask an LLM to review claims, or produce any readiness, approval,
legal, compliance, privacy, security, or go-live verdict. The project protects
evidence and authority boundaries by recording what happened, what did not
happen, and that human review remains the final authority.
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
    "This workflow does not approve projects, certify readiness, replace "
    "governance, or make legal, compliance, privacy, security, or go-live "
    "decisions. Human review remains the final authority."
)
SCAFFOLD_NOTE = (
    "PR #2 intake run: source inventory may describe supplied local files, but "
    "no chunking was performed, no evidence pack was created, no retrieval or "
    "LLM review was performed, and no project claim was evaluated."
)


def build_trace(
    question: str,
    output_dir: Path,
    sources_path: Path | None = None,
    source_inventory_written: bool = False,
    loaded_source_count: int = 0,
    skipped_source_count: int = 0,
) -> dict[str, Any]:
    """Build the JSON-serializable trace payload for an intake run.

    Args:
        question: The human review question supplied to the CLI.
        output_dir: Directory where the trace artifact will be written.
        sources_path: Optional local file or directory supplied for inventory.
        source_inventory_written: Whether ``source_inventory.json`` was written.
        loaded_source_count: Count of supported files loaded for metadata.
        skipped_source_count: Count of unsupported or invalid files skipped.

    Returns:
        A dictionary that records run metadata and makes the current non-review
        status explicit.
    """

    return {
        "tool_name": TOOL_NAME,
        "package_name": "project_evidence_review_agent",
        "package_version": __version__,
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "review_question": question,
        "output_directory": str(output_dir),
        "supplied_sources_path": str(sources_path) if sources_path else None,
        "workflow_stage": "pr_002_source_inventory_intake",
        "workflow_status": "source_inventory_only"
        if source_inventory_written
        else "scaffold_trace_only",
        "artifact": TRACE_FILE_NAME,
        "source_inventory_written": source_inventory_written,
        "loaded_source_count": loaded_source_count,
        "skipped_source_count": skipped_source_count,
        "source_loading_status": "inventory_written"
        if source_inventory_written
        else "not_requested",
        "chunking_status": "not_performed",
        "retrieval_status": "not_performed",
        "llm_review_status": "not_performed",
        "evidence_review_status": "not_performed",
        "approval_decision_status": "not_performed",
        "scaffold_note": SCAFFOLD_NOTE,
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_trace(
    question: str,
    output_dir: Path,
    sources_path: Path | None = None,
    source_inventory_written: bool = False,
    loaded_source_count: int = 0,
    skipped_source_count: int = 0,
) -> Path:
    """Write the trace artifact and return its path.

    The output directory is created if needed. PR #2 may also write a source
    inventory, but evidence indexes, evidence packs, reports, and LLM outputs
    remain deliberately outside this intake foundation.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / TRACE_FILE_NAME
    trace_payload = build_trace(
        question=question,
        output_dir=output_dir,
        sources_path=sources_path,
        source_inventory_written=source_inventory_written,
        loaded_source_count=loaded_source_count,
        skipped_source_count=skipped_source_count,
    )
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return trace_path
