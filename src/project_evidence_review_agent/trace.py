"""Create the project evidence trace artifact.

The trace exists so a human can prove the command ran and see the exact boundary
of the current implementation. Source inventory records what local material was
found, evidence indexing chunks loaded supported sources, and deterministic
retrieval can select a bounded set of lexical matches for the review question.

This trace now records the selected orchestrator, deterministic evidence-pack
work, bounded LLM claim-review status, bounded follow-up analysis for missing
evidence and contradiction candidates, and the final human-readable report
when those optional stages are requested and validated. It still records that
readiness, approval, legal, compliance, privacy, security, certification, and
go-live verdicts are not performed. The project protects evidence and authority
boundaries by recording what happened, what did not happen, and that human
review remains the final authority.
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
    "PR #9 run with optional orchestration metadata: source inventory and "
    "evidence indexing may prepare bounded "
    "local chunks, deterministic retrieval may select lexical matches for an "
    "evidence pack, optional bounded LLM claim review may validate cited "
    "claim output, follow-up analysis may write validated missing evidence "
    "and contradiction-candidate artifacts, and a final human-readable report "
    "may be assembled after validation. When sources are not supplied, no "
    "LLM review was performed. No project claim or go-live decision was "
    "approved. When --no-llm is supplied, evidence_pack.md is deterministic "
    "review preparation only and no project evidence report is written. When "
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
    missing_evidence_written: bool = False,
    missing_evidence_path: Path | None = None,
    missing_evidence_status: str = "not_performed",
    missing_evidence_validation_status: str = "not_performed",
    missing_evidence_count: int = 0,
    rejected_missing_evidence_count: int = 0,
    contradiction_log_written: bool = False,
    contradiction_log_path: Path | None = None,
    contradiction_detection_status: str = "not_performed",
    contradiction_validation_status: str = "not_performed",
    contradiction_candidate_count: int = 0,
    rejected_contradiction_count: int = 0,
    project_evidence_report_written: bool = False,
    project_evidence_report_path: Path | None = None,
    project_evidence_report_status: str = "not_requested_or_not_applicable",
    report_input_artifacts: list[str] | None = None,
    report_claim_count: int = 0,
    report_missing_evidence_count: int = 0,
    report_contradiction_candidate_count: int = 0,
    report_human_check_count: int = 0,
    final_report_is_not_approval: bool = True,
    orchestrator: str = "standard",
    langgraph_requested: bool = False,
    langgraph_available: bool | None = None,
    graph_orchestration_status: str = "not_used",
    graph_node_statuses: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build concise operational status for a workflow run.

    The trace records which artifacts were written, which stages were skipped or
    failed, and which orchestrator ran. Counts and statuses support run
    inspection; they are not project conclusions.
    """

    # Derived statuses keep the trace readable without changing artifact schemas
    # or introducing review conclusions.
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
        "workflow_stage": "pr_009_optional_orchestration",
        "workflow_status": _workflow_status(
            evidence_pack_markdown_written=evidence_pack_markdown_written,
            llm_review_status=llm_review_status,
            claim_review_validation_status=claim_review_validation_status,
            missing_evidence_validation_status=missing_evidence_validation_status,
            contradiction_validation_status=contradiction_validation_status,
            project_evidence_report_status=project_evidence_report_status,
        ),
        "artifact": TRACE_FILE_NAME,
        "orchestrator": orchestrator,
        "langgraph_requested": langgraph_requested,
        "langgraph_available": langgraph_available,
        "graph_orchestration_status": graph_orchestration_status,
        "graph_node_statuses": graph_node_statuses or {},
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
        "missing_evidence_written": missing_evidence_written,
        "missing_evidence_path": str(missing_evidence_path)
        if missing_evidence_path
        else None,
        "missing_evidence_status": missing_evidence_status,
        "missing_evidence_detection_status": missing_evidence_status,
        "missing_evidence_validation_status": missing_evidence_validation_status,
        "missing_evidence_count": missing_evidence_count,
        "rejected_missing_evidence_count": rejected_missing_evidence_count,
        "contradiction_log_written": contradiction_log_written,
        "contradiction_log_path": str(contradiction_log_path)
        if contradiction_log_path
        else None,
        "contradiction_detection_status": contradiction_detection_status,
        "contradiction_validation_status": contradiction_validation_status,
        "contradiction_candidate_count": contradiction_candidate_count,
        "rejected_contradiction_count": rejected_contradiction_count,
        "project_evidence_report_written": project_evidence_report_written,
        "project_evidence_report_path": str(project_evidence_report_path)
        if project_evidence_report_path
        else None,
        "project_evidence_report_status": project_evidence_report_status,
        "report_input_artifacts": report_input_artifacts or [],
        "report_claim_count": report_claim_count,
        "report_missing_evidence_count": report_missing_evidence_count,
        "report_contradiction_candidate_count": report_contradiction_candidate_count,
        "report_human_check_count": report_human_check_count,
        # These explicit false/not_performed fields preserve the no-approval and
        # no-go-live boundary even when a final report was assembled.
        "final_report_is_not_approval": final_report_is_not_approval,
        "final_project_evidence_report_written": project_evidence_report_written,
        "approval_or_go_live_decision_written": False,
        "project_evidence_markdown_report_status": project_evidence_report_status,
        "markdown_report_status": project_evidence_report_status,
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
    missing_evidence_written: bool = False,
    missing_evidence_path: Path | None = None,
    missing_evidence_status: str = "not_performed",
    missing_evidence_validation_status: str = "not_performed",
    missing_evidence_count: int = 0,
    rejected_missing_evidence_count: int = 0,
    contradiction_log_written: bool = False,
    contradiction_log_path: Path | None = None,
    contradiction_detection_status: str = "not_performed",
    contradiction_validation_status: str = "not_performed",
    contradiction_candidate_count: int = 0,
    rejected_contradiction_count: int = 0,
    project_evidence_report_written: bool = False,
    project_evidence_report_path: Path | None = None,
    project_evidence_report_status: str = "not_requested_or_not_applicable",
    report_input_artifacts: list[str] | None = None,
    report_claim_count: int = 0,
    report_missing_evidence_count: int = 0,
    report_contradiction_candidate_count: int = 0,
    report_human_check_count: int = 0,
    final_report_is_not_approval: bool = True,
    orchestrator: str = "standard",
    langgraph_requested: bool = False,
    langgraph_available: bool | None = None,
    graph_orchestration_status: str = "not_used",
    graph_node_statuses: dict[str, str] | None = None,
) -> Path:
    """Write the trace artifact and return its path.

    The trace is operational metadata, not another evidence-review artifact.
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
        missing_evidence_written=missing_evidence_written,
        missing_evidence_path=missing_evidence_path,
        missing_evidence_status=missing_evidence_status,
        missing_evidence_validation_status=missing_evidence_validation_status,
        missing_evidence_count=missing_evidence_count,
        rejected_missing_evidence_count=rejected_missing_evidence_count,
        contradiction_log_written=contradiction_log_written,
        contradiction_log_path=contradiction_log_path,
        contradiction_detection_status=contradiction_detection_status,
        contradiction_validation_status=contradiction_validation_status,
        contradiction_candidate_count=contradiction_candidate_count,
        rejected_contradiction_count=rejected_contradiction_count,
        project_evidence_report_written=project_evidence_report_written,
        project_evidence_report_path=project_evidence_report_path,
        project_evidence_report_status=project_evidence_report_status,
        report_input_artifacts=report_input_artifacts,
        report_claim_count=report_claim_count,
        report_missing_evidence_count=report_missing_evidence_count,
        report_contradiction_candidate_count=report_contradiction_candidate_count,
        report_human_check_count=report_human_check_count,
        final_report_is_not_approval=final_report_is_not_approval,
        orchestrator=orchestrator,
        langgraph_requested=langgraph_requested,
        langgraph_available=langgraph_available,
        graph_orchestration_status=graph_orchestration_status,
        graph_node_statuses=graph_node_statuses,
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
    missing_evidence_validation_status: str = "not_performed",
    contradiction_validation_status: str = "not_performed",
    project_evidence_report_status: str = "not_requested_or_not_applicable",
) -> str:
    """Summarize run progress without deciding project readiness."""

    if project_evidence_report_status == "written":
        return "project_evidence_report_written"
    if (
        claim_review_validation_status == "passed"
        and missing_evidence_validation_status == "passed"
        and contradiction_validation_status == "passed"
    ):
        return "bounded_llm_follow_up_analysis_completed"
    if (
        missing_evidence_validation_status == "failed"
        or contradiction_validation_status == "failed"
    ):
        return "bounded_llm_follow_up_analysis_validation_failed"
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
