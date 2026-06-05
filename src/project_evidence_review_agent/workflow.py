"""Shared workflow stages for project evidence review orchestration.

This module is the orchestration seam for PR #9. It deliberately keeps product
logic in the existing modules: source inventory owns local source loading,
evidence indexing owns chunk semantics, retrieval owns deterministic selection,
claim/follow-up modules own LLM validation, and project reporting owns final
Markdown assembly. The standard runner calls the stages directly; the optional
LangGraph adapter wraps the same stage functions as graph nodes.
"""

from __future__ import annotations

from project_evidence_review_agent.claim_review import run_claim_review
from project_evidence_review_agent.evidence_index import (
    build_evidence_index,
    write_evidence_index,
)
from project_evidence_review_agent.evidence_pack_markdown import (
    write_evidence_pack_markdown,
)
from project_evidence_review_agent.follow_up_analysis import run_follow_up_analysis
from project_evidence_review_agent.llm_client import (
    LLMConfigurationError,
    OpenAIReviewClient,
    ReviewLLMClient,
)
from project_evidence_review_agent.llm_context import (
    build_llm_safe_review_context,
    write_llm_safe_review_context,
)
from project_evidence_review_agent.project_report import (
    INPUT_ARTIFACTS,
    write_project_evidence_report,
)
from project_evidence_review_agent.retrieval import write_retrieval_outputs
from project_evidence_review_agent.review_question import write_review_question
from project_evidence_review_agent.source_inventory import (
    build_source_inventory,
    write_source_inventory_payload,
)
from project_evidence_review_agent.trace import write_trace
from project_evidence_review_agent.workflow_state import WorkflowConfig, WorkflowResult


class WorkflowLLMConfigurationError(Exception):
    """Raised after trace-safe status fields are set for missing LLM config."""

    def __init__(self, original: LLMConfigurationError) -> None:
        self.original = original
        super().__init__(str(original))


def run_standard_workflow(
    config: WorkflowConfig,
    review_client: ReviewLLMClient | None = None,
) -> WorkflowResult:
    """Run the default Python orchestration path.

    Standard orchestration remains the default so normal installs do not require
    LangGraph. The sequence below only decides stage order and skip/failure
    branches; each stage calls the same focused business module that existed
    before this orchestration refactor.
    """

    result = WorkflowResult(langgraph_available=None)
    prepare_output(config, result)
    try:
        if config.sources_path is not None:
            inventory_sources(config, result)
            build_evidence_index_stage(config, result)
            record_review_question(config, result)
            retrieve_evidence(config, result)
            write_evidence_pack_markdown_stage(config, result)
            if config.no_llm:
                mark_no_llm_skips(result)
            else:
                build_llm_context(config, result)
                run_claim_review_stage(config, result, review_client)
                if result.claim_review_validation_status == "passed":
                    run_followup_analysis_stage(config, result, review_client)
                    if followup_passed(result):
                        write_project_report_stage(config, result)
                    else:
                        result.project_evidence_report_status = (
                            "skipped_followup_failed"
                        )
                else:
                    mark_claim_review_failure_skips(result)
        return result
    finally:
        write_trace_stage(config, result)


def prepare_output(config: WorkflowConfig, _result: WorkflowResult) -> None:
    """Create the output directory without changing review semantics."""

    config.output_dir.mkdir(parents=True, exist_ok=True)


def inventory_sources(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Inventory local sources using the existing source inventory module."""

    if config.sources_path is None:
        return
    inventory = build_source_inventory(config.sources_path)
    summary = write_source_inventory_payload(
        inventory=inventory,
        output_dir=config.output_dir,
    )
    result.inventory = inventory
    result.source_inventory_written = True
    result.loaded_source_count = summary.loaded_count
    result.skipped_source_count = summary.skipped_count


def build_evidence_index_stage(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Build bounded deterministic chunks using existing evidence-index logic."""

    if config.sources_path is None or result.inventory is None:
        return
    evidence_index = build_evidence_index(
        inventory=result.inventory,
        sources_path=config.sources_path,
    )
    summary = write_evidence_index(
        inventory=result.inventory,
        sources_path=config.sources_path,
        output_dir=config.output_dir,
        evidence_index=evidence_index,
    )
    result.evidence_index = evidence_index
    result.evidence_index_written = True
    result.evidence_chunk_count = summary.chunk_count
    result.chunking_status = summary.status


def record_review_question(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Record the human review question for deterministic retrieval."""

    if config.sources_path is None:
        return
    write_review_question(question=config.question, output_dir=config.output_dir)
    result.review_question_written = True


def retrieve_evidence(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Run deterministic lexical retrieval without adding interpretation."""

    if result.evidence_index is None:
        return
    summary = write_retrieval_outputs(
        question=config.question,
        evidence_index=result.evidence_index,
        max_chunks=config.max_chunks,
        output_dir=config.output_dir,
    )
    result.retrieval_trace_written = True
    result.evidence_pack_written = True
    result.evidence_pack_payload = summary.evidence_pack_payload
    result.selected_evidence_chunk_count = summary.selected_chunk_count
    result.source_fingerprint_warning_count = max(
        result.evidence_index.get("summary", {}).get(
            "source_fingerprint_warning_count", 0
        ),
        summary.source_fingerprint_warning_count,
    )


def write_evidence_pack_markdown_stage(
    config: WorkflowConfig, result: WorkflowResult
) -> None:
    """Render deterministic evidence-pack Markdown from the selected chunks."""

    if result.evidence_pack_payload is None:
        return
    result.evidence_pack_markdown_path = write_evidence_pack_markdown(
        evidence_pack=result.evidence_pack_payload,
        output_dir=config.output_dir,
    )
    result.evidence_pack_markdown_written = True


def mark_no_llm_skips(result: WorkflowResult) -> None:
    """Record that optional LLM-backed stages were intentionally skipped."""

    result.llm_review_status = "skipped_no_llm"
    result.missing_evidence_status = "skipped_no_llm"
    result.contradiction_detection_status = "skipped_no_llm"
    result.project_evidence_report_status = "skipped_no_llm"


def build_llm_context(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Write bounded LLM context over selected evidence only.

    This stage prepares the same safe context as the standard product flow. It
    does not call an LLM and does not expand the evidence boundary.
    """

    if result.evidence_pack_payload is None:
        return
    result.llm_safe_context = build_llm_safe_review_context(
        result.evidence_pack_payload
    )
    result.llm_safe_review_context_path = write_llm_safe_review_context(
        evidence_pack=result.evidence_pack_payload,
        output_dir=config.output_dir,
    )
    result.llm_safe_review_context_written = True


def get_review_client(review_client: ReviewLLMClient | None) -> ReviewLLMClient:
    """Return the injected fake/test client or construct the optional OpenAI client."""

    if review_client is not None:
        return review_client
    try:
        return OpenAIReviewClient()
    except LLMConfigurationError as exc:
        raise WorkflowLLMConfigurationError(exc) from exc


def run_claim_review_stage(
    config: WorkflowConfig,
    result: WorkflowResult,
    review_client: ReviewLLMClient | None = None,
) -> None:
    """Run bounded claim review and preserve validation-driven skip behavior."""

    if result.llm_safe_context is None:
        return
    try:
        client = get_review_client(review_client)
    except WorkflowLLMConfigurationError:
        result.llm_review_status = "failed"
        result.claim_review_validation_status = "not_validated"
        mark_claim_review_failure_skips(result)
        raise
    result.review_client = client
    claim_result = run_claim_review(
        context=result.llm_safe_context,
        client=client,
        model=config.llm_model,
        output_dir=config.output_dir,
    )
    result.claim_review_written = True
    result.claim_review_path = claim_result.path
    result.llm_review_status = claim_result.llm_review_status
    result.claim_review_validation_status = claim_result.validation_status
    result.claim_count = claim_result.claim_count
    result.rejected_claim_count = claim_result.rejected_claim_count
    result.validator_message_count = claim_result.validator_message_count
    result.claim_review_payload = claim_result.payload


def mark_claim_review_failure_skips(result: WorkflowResult) -> None:
    """Skip downstream stages after claim review failure or failed validation."""

    result.missing_evidence_status = "skipped_claim_review_failed"
    result.contradiction_detection_status = "skipped_claim_review_failed"
    result.project_evidence_report_status = "skipped_claim_review_failed"


def run_followup_analysis_stage(
    config: WorkflowConfig,
    result: WorkflowResult,
    review_client: ReviewLLMClient | None = None,
) -> None:
    """Run existing missing-evidence and contradiction analysis once.

    This reuses the same client and bounded context as claim review; it does not
    introduce any additional graph-specific LLM call.
    """

    if result.llm_safe_context is None or result.claim_review_payload is None:
        return
    client = review_client or result.review_client or get_review_client(review_client)
    follow_up = run_follow_up_analysis(
        llm_context=result.llm_safe_context,
        claim_review=result.claim_review_payload,
        client=client,
        model=config.llm_model,
        output_dir=config.output_dir,
    )
    result.missing_evidence_written = True
    result.missing_evidence_path = follow_up.missing_evidence_path
    result.missing_evidence_status = follow_up.missing_evidence_status
    result.missing_evidence_validation_status = follow_up.missing_validation_status
    result.missing_evidence_count = follow_up.missing_count
    result.rejected_missing_evidence_count = follow_up.rejected_missing_count
    result.contradiction_log_written = True
    result.contradiction_log_path = follow_up.contradiction_log_path
    result.contradiction_detection_status = follow_up.contradiction_status
    result.contradiction_validation_status = follow_up.contradiction_validation_status
    result.contradiction_candidate_count = follow_up.contradiction_count
    result.rejected_contradiction_count = follow_up.rejected_contradiction_count
    result.missing_evidence_payload = follow_up.missing_evidence_payload
    result.contradiction_payload = follow_up.contradiction_payload


def followup_passed(result: WorkflowResult) -> bool:
    """Return whether validated follow-up artifacts permit report assembly."""

    return (
        result.missing_evidence_status == "completed"
        and result.missing_evidence_validation_status == "passed"
        and result.contradiction_detection_status == "completed"
        and result.contradiction_validation_status == "passed"
    )


def write_project_report_stage(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Assemble the final deterministic report from validated artifacts only."""

    if (
        result.evidence_pack_payload is None
        or result.claim_review_payload is None
        or result.missing_evidence_payload is None
        or result.contradiction_payload is None
    ):
        return
    trace_summary = {
        "loaded_source_count": result.loaded_source_count,
        "skipped_source_count": result.skipped_source_count,
        "evidence_chunk_count": result.evidence_chunk_count,
        "project_evidence_report_status": "written",
    }
    report_summary = write_project_evidence_report(
        output_dir=config.output_dir,
        evidence_pack=result.evidence_pack_payload,
        claim_review=result.claim_review_payload,
        missing_evidence=result.missing_evidence_payload,
        contradiction_log=result.contradiction_payload,
        trace_summary=trace_summary,
    )
    result.project_evidence_report_written = True
    result.project_evidence_report_path = report_summary.path
    result.project_evidence_report_status = "written"
    result.report_claim_count = report_summary.claim_count
    result.report_missing_evidence_count = report_summary.missing_evidence_count
    result.report_contradiction_candidate_count = (
        report_summary.contradiction_candidate_count
    )
    result.report_human_check_count = report_summary.human_check_count


def write_trace_stage(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Write the single trace payload for every orchestration path."""

    result.trace_path = write_trace(
        question=config.question,
        output_dir=config.output_dir,
        sources_path=config.sources_path,
        source_inventory_written=result.source_inventory_written,
        loaded_source_count=result.loaded_source_count,
        skipped_source_count=result.skipped_source_count,
        evidence_index_written=result.evidence_index_written,
        evidence_chunk_count=result.evidence_chunk_count,
        chunking_status=result.chunking_status,
        review_question_written=result.review_question_written,
        retrieval_trace_written=result.retrieval_trace_written,
        evidence_pack_written=result.evidence_pack_written,
        evidence_pack_markdown_written=result.evidence_pack_markdown_written,
        evidence_pack_markdown_path=result.evidence_pack_markdown_path,
        selected_evidence_chunk_count=result.selected_evidence_chunk_count,
        max_chunks=config.max_chunks,
        source_fingerprint_warning_count=result.source_fingerprint_warning_count,
        no_llm=config.no_llm,
        llm_model=config.llm_model,
        llm_safe_review_context_written=result.llm_safe_review_context_written,
        llm_safe_review_context_path=result.llm_safe_review_context_path,
        claim_review_written=result.claim_review_written,
        claim_review_path=result.claim_review_path,
        llm_review_status=result.llm_review_status,
        claim_review_validation_status=result.claim_review_validation_status,
        claim_count=result.claim_count,
        rejected_claim_count=result.rejected_claim_count,
        validator_message_count=result.validator_message_count,
        missing_evidence_written=result.missing_evidence_written,
        missing_evidence_path=result.missing_evidence_path,
        missing_evidence_status=result.missing_evidence_status,
        missing_evidence_validation_status=result.missing_evidence_validation_status,
        missing_evidence_count=result.missing_evidence_count,
        rejected_missing_evidence_count=result.rejected_missing_evidence_count,
        contradiction_log_written=result.contradiction_log_written,
        contradiction_log_path=result.contradiction_log_path,
        contradiction_detection_status=result.contradiction_detection_status,
        contradiction_validation_status=result.contradiction_validation_status,
        contradiction_candidate_count=result.contradiction_candidate_count,
        rejected_contradiction_count=result.rejected_contradiction_count,
        project_evidence_report_written=result.project_evidence_report_written,
        project_evidence_report_path=result.project_evidence_report_path,
        project_evidence_report_status=result.project_evidence_report_status,
        report_input_artifacts=INPUT_ARTIFACTS
        if result.project_evidence_report_written
        else [],
        report_claim_count=result.report_claim_count,
        report_missing_evidence_count=result.report_missing_evidence_count,
        report_contradiction_candidate_count=(
            result.report_contradiction_candidate_count
        ),
        report_human_check_count=result.report_human_check_count,
        final_report_is_not_approval=True,
        orchestrator=config.orchestrator,
        langgraph_requested=config.orchestrator == "langgraph",
        langgraph_available=result.langgraph_available,
        graph_orchestration_status=result.graph_orchestration_status,
        graph_node_statuses=result.graph_node_statuses,
    )


def workflow_exit_code(config: WorkflowConfig, result: WorkflowResult) -> int:
    """Map validation and LLM failure statuses to the legacy CLI exit code."""

    if (
        config.sources_path is not None
        and not config.no_llm
        and (
            result.llm_review_status == "failed"
            or result.claim_review_validation_status == "failed"
            or result.missing_evidence_status == "failed"
            or result.missing_evidence_validation_status == "failed"
            or result.contradiction_detection_status == "failed"
            or result.contradiction_validation_status == "failed"
        )
    ):
        return 1
    return 0
