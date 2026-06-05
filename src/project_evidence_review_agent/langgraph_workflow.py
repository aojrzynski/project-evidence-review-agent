"""Optional LangGraph orchestration adapter.

LangGraph is intentionally optional: normal CLI use stays on the standard Python
runner and normal installation does not include graph dependencies. When a user
requests ``--orchestrator langgraph``, this adapter builds a graph whose nodes
are thin wrappers around the shared workflow stages in :mod:`workflow`. The graph
owns ordering and branch decisions only; evidence, review, validation, and report
semantics remain in the existing tested modules.
"""

from __future__ import annotations

from typing import Any

from project_evidence_review_agent.llm_client import ReviewLLMClient
from project_evidence_review_agent.workflow import (
    WorkflowLLMConfigurationError,
    build_evidence_index_stage,
    build_llm_context,
    followup_passed,
    inventory_sources,
    mark_claim_review_failure_skips,
    mark_no_llm_skips,
    prepare_output,
    record_review_question,
    retrieve_evidence,
    run_claim_review_stage,
    run_followup_analysis_stage,
    write_evidence_pack_markdown_stage,
    write_project_report_stage,
    write_trace_stage,
)
from project_evidence_review_agent.workflow_state import WorkflowConfig, WorkflowResult

LANGGRAPH_INSTALL_MESSAGE = (
    "LangGraph orchestration requires the optional graph dependencies. "
    "Install with: pip install -e '.[graph]'"
)


class LangGraphUnavailableError(Exception):
    """Raised when the optional graph extra is requested but not installed."""


def run_langgraph_workflow(
    config: WorkflowConfig,
    review_client: ReviewLLMClient | None = None,
) -> WorkflowResult:
    """Run the same artifact-producing workflow through LangGraph nodes.

    The graph mirrors the product stages and conditional branches: no-source runs
    write only the trace, ``--no-llm`` skips all LLM-backed stages, failed claim
    review skips follow-up/report stages, failed follow-up validation skips the
    report, and every completed path ends by writing the same trace payload. The
    nodes do not duplicate business logic; each node calls a shared stage
    function from :mod:`project_evidence_review_agent.workflow`.
    """

    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise LangGraphUnavailableError(LANGGRAPH_INSTALL_MESSAGE) from exc

    graph_config = WorkflowConfig(
        question=config.question,
        output_dir=config.output_dir,
        sources_path=config.sources_path,
        max_chunks=config.max_chunks,
        no_llm=config.no_llm,
        llm_model=config.llm_model,
        orchestrator="langgraph",
    )
    result = WorkflowResult(
        graph_orchestration_status="running",
        langgraph_available=True,
    )

    def node(name: str, func: Any) -> Any:
        def wrapped(state: dict[str, Any]) -> dict[str, Any]:
            state["result"].graph_node_statuses[name] = "running"
            func(state["config"], state["result"])
            state["result"].graph_node_statuses[name] = "completed"
            return state

        return wrapped

    def run_claim_node(state: dict[str, Any]) -> dict[str, Any]:
        name = "run_claim_review"
        state["result"].graph_node_statuses[name] = "running"
        try:
            run_claim_review_stage(
                state["config"], state["result"], state["review_client"]
            )
        except WorkflowLLMConfigurationError:
            state["result"].graph_node_statuses[name] = "failed"
            raise
        state["result"].graph_node_statuses[name] = "completed"
        return state

    def run_followup_node(state: dict[str, Any]) -> dict[str, Any]:
        name = "run_followup_analysis"
        state["result"].graph_node_statuses[name] = "running"
        run_followup_analysis_stage(
            state["config"], state["result"], state["review_client"]
        )
        state["result"].graph_node_statuses[name] = "completed"
        return state

    def no_llm_node(state: dict[str, Any]) -> dict[str, Any]:
        name = "mark_no_llm_skips"
        state["result"].graph_node_statuses[name] = "running"
        mark_no_llm_skips(state["result"])
        state["result"].graph_node_statuses[name] = "completed"
        return state

    def claim_failed_node(state: dict[str, Any]) -> dict[str, Any]:
        name = "mark_claim_review_failure_skips"
        state["result"].graph_node_statuses[name] = "running"
        mark_claim_review_failure_skips(state["result"])
        state["result"].graph_node_statuses[name] = "completed"
        return state

    def report_skipped_node(state: dict[str, Any]) -> dict[str, Any]:
        name = "mark_followup_report_skipped"
        state["result"].graph_node_statuses[name] = "running"
        state["result"].project_evidence_report_status = "skipped_followup_failed"
        state["result"].graph_node_statuses[name] = "completed"
        return state

    def write_trace_node(state: dict[str, Any]) -> dict[str, Any]:
        name = "write_trace"
        state["result"].graph_node_statuses[name] = "running"
        state["result"].graph_orchestration_status = "completed"
        write_trace_stage(state["config"], state["result"])
        state["result"].graph_node_statuses[name] = "completed"
        return state

    def route_after_prepare(state: dict[str, Any]) -> str:
        if state["config"].sources_path is None:
            return "write_trace"
        return "inventory_sources"

    def route_after_markdown(state: dict[str, Any]) -> str:
        if state["config"].no_llm:
            return "mark_no_llm_skips"
        return "build_llm_context"

    def route_after_claim_review(state: dict[str, Any]) -> str:
        if state["result"].claim_review_validation_status == "passed":
            return "run_followup_analysis"
        return "mark_claim_review_failure_skips"

    def route_after_followup(state: dict[str, Any]) -> str:
        if followup_passed(state["result"]):
            return "write_project_report"
        return "mark_followup_report_skipped"

    workflow = StateGraph(dict)
    workflow.add_node("prepare_output", node("prepare_output", prepare_output))
    workflow.add_node("inventory_sources", node("inventory_sources", inventory_sources))
    workflow.add_node(
        "build_evidence_index",
        node("build_evidence_index", build_evidence_index_stage),
    )
    workflow.add_node(
        "record_review_question",
        node("record_review_question", record_review_question),
    )
    workflow.add_node("retrieve_evidence", node("retrieve_evidence", retrieve_evidence))
    workflow.add_node(
        "write_evidence_pack_markdown",
        node("write_evidence_pack_markdown", write_evidence_pack_markdown_stage),
    )
    workflow.add_node("mark_no_llm_skips", no_llm_node)
    workflow.add_node("build_llm_context", node("build_llm_context", build_llm_context))
    workflow.add_node("run_claim_review", run_claim_node)
    workflow.add_node("mark_claim_review_failure_skips", claim_failed_node)
    workflow.add_node("run_followup_analysis", run_followup_node)
    workflow.add_node("mark_followup_report_skipped", report_skipped_node)
    workflow.add_node(
        "write_project_report",
        node("write_project_report", write_project_report_stage),
    )
    workflow.add_node("write_trace", write_trace_node)

    workflow.set_entry_point("prepare_output")
    workflow.add_conditional_edges(
        "prepare_output",
        route_after_prepare,
        {"inventory_sources": "inventory_sources", "write_trace": "write_trace"},
    )
    workflow.add_edge("inventory_sources", "build_evidence_index")
    workflow.add_edge("build_evidence_index", "record_review_question")
    workflow.add_edge("record_review_question", "retrieve_evidence")
    workflow.add_edge("retrieve_evidence", "write_evidence_pack_markdown")
    workflow.add_conditional_edges(
        "write_evidence_pack_markdown",
        route_after_markdown,
        {
            "mark_no_llm_skips": "mark_no_llm_skips",
            "build_llm_context": "build_llm_context",
        },
    )
    workflow.add_edge("mark_no_llm_skips", "write_trace")
    workflow.add_edge("build_llm_context", "run_claim_review")
    workflow.add_conditional_edges(
        "run_claim_review",
        route_after_claim_review,
        {
            "run_followup_analysis": "run_followup_analysis",
            "mark_claim_review_failure_skips": "mark_claim_review_failure_skips",
        },
    )
    workflow.add_edge("mark_claim_review_failure_skips", "write_trace")
    workflow.add_conditional_edges(
        "run_followup_analysis",
        route_after_followup,
        {
            "write_project_report": "write_project_report",
            "mark_followup_report_skipped": "mark_followup_report_skipped",
        },
    )
    workflow.add_edge("mark_followup_report_skipped", "write_trace")
    workflow.add_edge("write_project_report", "write_trace")
    workflow.add_edge("write_trace", END)

    app = workflow.compile()
    try:
        final_state = app.invoke(
            {"config": graph_config, "result": result, "review_client": review_client}
        )
    except Exception:
        result.graph_orchestration_status = "failed"
        if result.trace_path is None:
            write_trace_stage(graph_config, result)
        raise
    return final_state["result"]
