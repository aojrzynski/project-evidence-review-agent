"""Shared workflow state for standard and optional graph orchestration.

The product's evidence and review semantics live in focused modules such as
source inventory, retrieval, claim review, follow-up analysis, and reporting.
These dataclasses only carry configuration and stage outcomes between
orchestrators. Keeping that state in one place lets the default Python workflow
and optional LangGraph adapter call the same tested stage functions without
copying business logic into graph nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from project_evidence_review_agent.llm_client import DEFAULT_LLM_MODEL


@dataclass(slots=True)
class WorkflowConfig:
    """User-selected workflow settings shared by all orchestrators.

    Standard orchestration remains the default because LangGraph is an optional
    adapter for teams that want graph-shaped execution. These flags do not alter
    evidence semantics; they only decide which existing stages are run and where
    their artifacts are written.
    """

    # User/run configuration. These values come from the CLI and are shared by
    # standard and graph orchestration without changing stage semantics.
    question: str
    output_dir: Path
    sources_path: Path | None = None
    max_chunks: int = 10
    no_llm: bool = False
    llm_model: str = DEFAULT_LLM_MODEL
    orchestrator: str = "standard"


@dataclass(slots=True)
class WorkflowResult:
    """Mutable stage results used by standard and LangGraph orchestration.

    The fields intentionally mirror trace status/count fields so both
    orchestrators end with the same trace construction. Payload fields are kept
    only to hand validated outputs from one existing business module to the next;
    graph nodes must not reinterpret or rewrite them.
    """

    # Operational status and counts. These fields explain what happened during
    # the run; they are not evidence conclusions or approval decisions.
    source_inventory_written: bool = False
    evidence_index_written: bool = False
    review_question_written: bool = False
    retrieval_trace_written: bool = False
    evidence_pack_written: bool = False
    evidence_pack_markdown_written: bool = False
    evidence_pack_markdown_path: Path | None = None
    loaded_source_count: int = 0
    skipped_source_count: int = 0
    evidence_chunk_count: int = 0
    selected_evidence_chunk_count: int = 0
    source_fingerprint_warning_count: int = 0
    chunking_status: str = "not_requested"
    llm_safe_review_context_written: bool = False
    llm_safe_review_context_path: Path | None = None
    claim_review_written: bool = False
    claim_review_path: Path | None = None
    llm_review_status: str = "not_performed"
    claim_review_validation_status: str = "not_performed"
    claim_count: int = 0
    rejected_claim_count: int = 0
    validator_message_count: int = 0
    missing_evidence_written: bool = False
    missing_evidence_path: Path | None = None
    missing_evidence_status: str = "not_performed"
    missing_evidence_validation_status: str = "not_performed"
    missing_evidence_count: int = 0
    rejected_missing_evidence_count: int = 0
    contradiction_log_written: bool = False
    contradiction_log_path: Path | None = None
    contradiction_detection_status: str = "not_performed"
    contradiction_validation_status: str = "not_performed"
    contradiction_candidate_count: int = 0
    rejected_contradiction_count: int = 0
    project_evidence_report_written: bool = False
    project_evidence_report_path: Path | None = None
    project_evidence_report_status: str = "not_requested_or_not_applicable"
    report_claim_count: int = 0
    report_missing_evidence_count: int = 0
    report_contradiction_candidate_count: int = 0
    report_human_check_count: int = 0
    trace_path: Path | None = None
    graph_orchestration_status: str = "not_used"
    langgraph_available: bool | None = None
    graph_node_statuses: dict[str, str] = field(default_factory=dict)

    # In-memory payload hand-offs between stages. They let both orchestrators
    # share the same business modules without re-reading or reinterpreting
    # artifacts inside graph nodes.
    inventory: Any = None
    evidence_index: dict[str, Any] | None = None
    evidence_pack_payload: dict[str, Any] | None = None
    llm_safe_context: dict[str, Any] | None = None
    claim_review_payload: dict[str, Any] | None = None
    missing_evidence_payload: dict[str, Any] | None = None
    contradiction_payload: dict[str, Any] | None = None
    review_client: Any = None
