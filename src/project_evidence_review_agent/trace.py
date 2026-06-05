"""Create the project evidence trace artifact.

The trace exists so a human can prove the command ran and see the exact boundary
of the current implementation. Source inventory records what local material was
found, evidence indexing chunks loaded supported sources, and deterministic
retrieval can select a bounded set of lexical matches for the review question.

This trace now records deterministic evidence-pack work plus the bounded LLM
claim-review status when that optional stage is requested. It still records that
missing evidence detection, contradiction detection, the final project evidence
report, and readiness, approval, legal, compliance, privacy, security,
certification, or go-live verdicts are not performed. The project protects
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
    "PR #6 run: source inventory and evidence indexing may prepare bounded "
    "local chunks, deterministic retrieval may select lexical matches for an "
    "evidence pack, and optional bounded LLM claim review may validate cited "
    "claim output. When sources are not supplied, no LLM review was performed. "
    "Missing evidence detection was not performed, contradiction "
    "detection was not performed, no final project evidence report was written, "
    "and no project claim or go-live decision was approved. When --no-llm is "
    "supplied, evidence_pack.md is deterministic review preparation only. When "
    "sources are not supplied, no retrieval is performed."
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
    evidence_pack_markdown_written: bool = False,
    evidence_pack_markdown_path: Path | None = None,
    selected_evidence_chunk_count: int = 0,
    max_chunks: int = 10,
    source_fingerprint_warning_count: int = 0,
    no_llm: bool = False,
    llm_model: str | None = None,
    llm_safe_review_context_written: bool = False,
    llm_safe_review_context_path: Path | None = None,
    claim_review_written: bool = False,
    claim_review_path: Path | None = None,
    llm_review_status: str = "not_performed",
    claim_review_validation_status: str = "not_performed",
    claim_count: int = 0,
    rejected_claim_count: int = 0,
    validator_message_count: int = 0,
) -> dict[str, Any]:
    """Build the JSON-serializable trace payload for a retrieval run."""

    retrieval_status = "completed" if retrieval_trace_written else "not_performed"
    evidence_pack_status = "completed" if evidence_pack_written else "not_performed"
    evidence_pack_markdown_status = (
        "completed" if evidence_pack_markdown_written else "not_performed"
    )
    return {
        "tool_name": TOOL_NAME,
        "package_name": "project_evidence_review_agent",
        "package_version": __version__,
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "review_question": question,
        "output_directory": str(output_dir),
        "supplied_sources_path": str(sources_path) if sources_path else None,
        "workflow_stage": "pr_006_bounded_llm_claim_review",
        "workflow_status": _workflow_status(
            evidence_pack_markdown_written=evidence_pack_markdown_written,
            llm_review_status=llm_review_status,
            claim_review_validation_status=claim_review_validation_status,
        ),
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
        "evidence_pack_markdown_written": evidence_pack_markdown_written,
        "evidence_pack_markdown_path": str(evidence_pack_markdown_path)
        if evidence_pack_markdown_path
        else None,
        "evidence_pack_markdown_status": evidence_pack_markdown_status,
        "selected_evidence_chunk_count": selected_evidence_chunk_count,
        "max_chunks": max_chunks,
        "source_fingerprint_warning_count": source_fingerprint_warning_count,
        "retrieval_status": retrieval_status,
        "evidence_pack_status": evidence_pack_status,
        "no_llm": no_llm,
        "llm_model": llm_model,
        "llm_safe_review_context_written": llm_safe_review_context_written,
        "llm_safe_review_context_path": str(llm_safe_review_context_path)
        if llm_safe_review_context_path
        else None,
        "claim_review_written": claim_review_written,
        "claim_review_path": str(claim_review_path) if claim_review_path else None,
        "llm_review_status": llm_review_status,
        "claim_review_validation_status": claim_review_validation_status,
        "claim_count": claim_count,
        "rejected_claim_count": rejected_claim_count,
        "validator_message_count": validator_message_count,
        "evidence_review_status": "completed"
        if claim_review_validation_status == "passed"
        else "not_performed",
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
    evidence_pack_markdown_written: bool = False,
    evidence_pack_markdown_path: Path | None = None,
    selected_evidence_chunk_count: int = 0,
    max_chunks: int = 10,
    source_fingerprint_warning_count: int = 0,
    no_llm: bool = False,
    llm_model: str | None = None,
    llm_safe_review_context_written: bool = False,
    llm_safe_review_context_path: Path | None = None,
    claim_review_written: bool = False,
    claim_review_path: Path | None = None,
    llm_review_status: str = "not_performed",
    claim_review_validation_status: str = "not_performed",
    claim_count: int = 0,
    rejected_claim_count: int = 0,
    validator_message_count: int = 0,
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
        evidence_pack_markdown_written=evidence_pack_markdown_written,
        evidence_pack_markdown_path=evidence_pack_markdown_path,
        selected_evidence_chunk_count=selected_evidence_chunk_count,
        max_chunks=max_chunks,
        source_fingerprint_warning_count=source_fingerprint_warning_count,
        no_llm=no_llm,
        llm_model=llm_model,
        llm_safe_review_context_written=llm_safe_review_context_written,
        llm_safe_review_context_path=llm_safe_review_context_path,
        claim_review_written=claim_review_written,
        claim_review_path=claim_review_path,
        llm_review_status=llm_review_status,
        claim_review_validation_status=claim_review_validation_status,
        claim_count=claim_count,
        rejected_claim_count=rejected_claim_count,
        validator_message_count=validator_message_count,
    )
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return trace_path


def _workflow_status(
    *,
    evidence_pack_markdown_written: bool,
    llm_review_status: str,
    claim_review_validation_status: str,
) -> str:
    if claim_review_validation_status == "passed":
        return "bounded_llm_claim_review_completed"
    if claim_review_validation_status == "failed":
        return "bounded_llm_claim_review_validation_failed"
    if llm_review_status == "failed":
        return "bounded_llm_claim_review_failed"
    if llm_review_status == "skipped_no_llm":
        return "deterministic_evidence_pack_markdown_completed"
    if evidence_pack_markdown_written:
        return "deterministic_evidence_pack_markdown_completed"
    return "scaffold_trace_only"
