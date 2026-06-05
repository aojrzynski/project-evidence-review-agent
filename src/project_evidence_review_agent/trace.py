"""Create the project evidence trace artifact.

The trace exists so a human can prove the command ran and see the exact boundary
of the current implementation. Source inventory records what local material was
found, evidence indexing chunks loaded supported sources, and deterministic
retrieval can select a bounded set of lexical matches for the review question.

This stage still does not ask an LLM to review claims, detect missing evidence,
detect contradictions, write a Markdown report, or produce any readiness,
approval, legal, compliance, privacy, security, certification, or go-live
verdict. The project protects evidence and authority boundaries by recording
what happened, what did not happen, and that human review remains the final
authority.
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
    "PR #4 run: source inventory and evidence indexing may prepare bounded "
    "local chunks, and deterministic retrieval may select lexical matches for "
    "an evidence pack. Retrieval is not review: no LLM review was performed, no "
    "missing evidence detection was performed, no contradiction detection was "
    "performed, no Markdown report was written, and no project claim or go-live "
    "decision was approved. When sources are not supplied, no retrieval is performed."
)


def build_trace(
    question: str,
    output_dir: Path,
    sources_path: Path | None = None,
    source_inventory_written: bool = False,
    loaded_source_count: int = 0,
    skipped_source_count: int = 0,
    evidence_index_written: bool = False,
    evidence_chunk_count: int = 0,
    chunking_status: str = "not_requested",
    review_question_written: bool = False,
    retrieval_trace_written: bool = False,
    evidence_pack_written: bool = False,
    selected_evidence_chunk_count: int = 0,
    max_chunks: int = 10,
    source_fingerprint_warning_count: int = 0,
) -> dict[str, Any]:
    """Build the JSON-serializable trace payload for a retrieval run."""

    retrieval_status = "completed" if retrieval_trace_written else "not_performed"
    evidence_pack_status = "completed" if evidence_pack_written else "not_performed"
    return {
        "tool_name": TOOL_NAME,
        "package_name": "project_evidence_review_agent",
        "package_version": __version__,
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "review_question": question,
        "output_directory": str(output_dir),
        "supplied_sources_path": str(sources_path) if sources_path else None,
        "workflow_stage": "pr_004_review_question_retrieval",
        "workflow_status": "deterministic_retrieval_completed"
        if retrieval_trace_written
        else "scaffold_trace_only",
        "artifact": TRACE_FILE_NAME,
        "source_inventory_written": source_inventory_written,
        "loaded_source_count": loaded_source_count,
        "skipped_source_count": skipped_source_count,
        "source_loaded_count": loaded_source_count,
        "source_skipped_count": skipped_source_count,
        "source_loading_status": "inventory_written"
        if source_inventory_written
        else "not_requested",
        "evidence_index_written": evidence_index_written,
        "evidence_chunk_count": evidence_chunk_count,
        "chunking_status": chunking_status,
        "review_question_written": review_question_written,
        "retrieval_trace_written": retrieval_trace_written,
        "evidence_pack_written": evidence_pack_written,
        "selected_evidence_chunk_count": selected_evidence_chunk_count,
        "max_chunks": max_chunks,
        "source_fingerprint_warning_count": source_fingerprint_warning_count,
        "retrieval_status": retrieval_status,
        "evidence_pack_status": evidence_pack_status,
        "llm_review_status": "not_performed",
        "evidence_review_status": "not_performed",
        "missing_evidence_detection_status": "not_performed",
        "contradiction_detection_status": "not_performed",
        "project_evidence_markdown_report_status": "not_performed",
        "markdown_report_status": "not_performed",
        "approval_decision_status": "not_performed",
        "go_live_decision_status": "not_performed",
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
    evidence_index_written: bool = False,
    evidence_chunk_count: int = 0,
    chunking_status: str = "not_requested",
    review_question_written: bool = False,
    retrieval_trace_written: bool = False,
    evidence_pack_written: bool = False,
    selected_evidence_chunk_count: int = 0,
    max_chunks: int = 10,
    source_fingerprint_warning_count: int = 0,
) -> Path:
    """Write the trace artifact and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / TRACE_FILE_NAME
    trace_payload = build_trace(
        question=question,
        output_dir=output_dir,
        sources_path=sources_path,
        source_inventory_written=source_inventory_written,
        loaded_source_count=loaded_source_count,
        skipped_source_count=skipped_source_count,
        evidence_index_written=evidence_index_written,
        evidence_chunk_count=evidence_chunk_count,
        chunking_status=chunking_status,
        review_question_written=review_question_written,
        retrieval_trace_written=retrieval_trace_written,
        evidence_pack_written=evidence_pack_written,
        selected_evidence_chunk_count=selected_evidence_chunk_count,
        max_chunks=max_chunks,
        source_fingerprint_warning_count=source_fingerprint_warning_count,
    )
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return trace_path
