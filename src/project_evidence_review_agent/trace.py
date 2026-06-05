"""Create the project evidence trace artifact.

The trace exists so a human can prove the command ran and see the exact boundary
of the current implementation. Source inventory records what local material was
found, loaded, or skipped. Evidence indexing then chunks only loaded supported
sources into bounded local references that later stages may cite.

This stage still does not retrieve evidence for the question, build evidence
packs, ask an LLM to review claims, detect missing evidence, detect
contradictions, or produce any readiness, approval, legal, compliance, privacy,
security, certification, or go-live verdict. The project protects evidence and
authority boundaries by recording what happened, what did not happen, and that
human review remains the final authority.
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
    "PR #3 preparation run: source inventory may describe supplied local files "
    "and evidence indexing may create bounded chunks, but no retrieval was "
    "performed, no evidence pack was created, no LLM review was performed, and "
    "no project claim was evaluated."
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
) -> dict[str, Any]:
    """Build the JSON-serializable trace payload for a preparation run.

    Args:
        question: The human review question supplied to the CLI.
        output_dir: Directory where the trace artifact will be written.
        sources_path: Optional local file or directory supplied for inventory.
        source_inventory_written: Whether ``source_inventory.json`` was written.
        loaded_source_count: Count of supported files loaded for metadata.
        skipped_source_count: Count of unsupported or invalid files skipped.
        evidence_index_written: Whether ``evidence_index.json`` was written.
        evidence_chunk_count: Count of bounded evidence chunks created.
        chunking_status: Explicit status for the evidence indexing stage.

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
        "workflow_stage": "pr_003_chunking_evidence_index",
        "workflow_status": "source_inventory_and_evidence_index"
        if evidence_index_written
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
        "retrieval_status": "not_performed",
        "evidence_pack_status": "not_performed",
        "llm_review_status": "not_performed",
        "evidence_review_status": "not_performed",
        "missing_evidence_detection_status": "not_performed",
        "contradiction_detection_status": "not_performed",
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
) -> Path:
    """Write the trace artifact and return its path.

    The output directory is created if needed. Source inventory and evidence
    index artifacts may be written for local preparation, but retrieval outputs,
    evidence packs, reports, and LLM outputs remain deliberately outside this
    stage.
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
        evidence_index_written=evidence_index_written,
        evidence_chunk_count=evidence_chunk_count,
        chunking_status=chunking_status,
    )
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return trace_path
