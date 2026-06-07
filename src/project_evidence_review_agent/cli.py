"""Command-line interface for bounded project evidence review.

The CLI parses user intent and delegates stage execution to shared workflow
orchestration. Standard Python orchestration is the default. Optional LangGraph
orchestration can be requested with ``--orchestrator langgraph`` and only changes
how existing stages are ordered; it does not change evidence, review,
validation, report, or authority-boundary semantics.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from project_evidence_review_agent.langgraph_workflow import (
    LANGGRAPH_INSTALL_MESSAGE,
    LangGraphUnavailableError,
    run_langgraph_workflow,
)
from project_evidence_review_agent.llm_client import (
    DEFAULT_LLM_MODEL,
    ReviewLLMClient,
)
from project_evidence_review_agent.project_report import (
    PROJECT_EVIDENCE_REPORT_FILE_NAME,
)
from project_evidence_review_agent.retrieval import validate_max_chunks
from project_evidence_review_agent.version import __version__
from project_evidence_review_agent.workflow import (
    WorkflowLLMConfigurationError,
    run_standard_workflow,
    workflow_exit_code,
)
from project_evidence_review_agent.workflow_state import WorkflowConfig, WorkflowResult


def _positive_int(value: str) -> int:
    """Validate ``--max-chunks`` before workflow execution starts.

    The limit controls the size of the selected evidence pack and, when LLM
    review is enabled, the maximum evidence context passed downstream. Failing
    early keeps invalid bounds out of both orchestrators.
    """

    try:
        parsed = int(value)
    except ValueError as exc:
        message = "--max-chunks must be a positive integer"
        raise argparse.ArgumentTypeError(message) from exc
    try:
        return validate_max_chunks(parsed)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser that captures user intent only.

    The parser does not build artifacts or interpret evidence. It records the
    requested question, bounds, LLM mode, and orchestrator so the workflow layer
    can run the same business stages consistently.
    """

    parser = argparse.ArgumentParser(
        prog="project-evidence-review",
        description=(
            "Build deterministic evidence packs and, unless --no-llm is used, "
            "run bounded LLM review over selected evidence."
        ),
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Human review question to record and use for deterministic retrieval.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where output artifacts will be written.",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        help="Optional local file or directory to inventory, chunk, and retrieve from.",
    )
    # This bound is parsed with a custom validator because it constrains the
    # selected evidence pack and any later LLM context size.
    parser.add_argument(
        "--max-chunks",
        type=_positive_int,
        default=10,
        help=(
            "Maximum selected chunks for evidence_pack.json. "
            "Must be positive. Default: 10."
        ),
    )
    # --no-llm is a first-class deterministic evidence-pack mode, not an error
    # recovery path. It lets users inspect selected local evidence without any
    # optional model dependency.
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help=(
            "Skip LLM claim review and stop after deterministic evidence-pack "
            "JSON/Markdown artifacts."
        ),
    )
    parser.add_argument(
        "--llm-model",
        default=DEFAULT_LLM_MODEL,
        help=(
            f"LLM model for bounded claim review and follow-up analysis. "
            f"Default: {DEFAULT_LLM_MODEL}."
        ),
    )
    # The orchestrator flag selects execution shape only. LangGraph is optional
    # and must not change evidence selection, validation, or report meaning.
    parser.add_argument(
        "--orchestrator",
        choices=("standard", "langgraph"),
        default="standard",
        help=(
            "Workflow orchestrator to use. 'standard' is the default and has no "
            "LangGraph dependency; 'langgraph' requires the optional graph extra."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(
    argv: list[str] | None = None,
    review_client: ReviewLLMClient | None = None,
) -> int:
    """Run the CLI and return the process exit code.

    ``review_client`` is an injection seam for tests and callers that want to
    exercise the same CLI flow without constructing the optional OpenAI client.
    Missing optional LangGraph or LLM configuration is reported cleanly here,
    while the workflow remains responsible for trace-safe stage statuses.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    config = WorkflowConfig(
        question=args.question,
        output_dir=args.output_dir,
        sources_path=args.sources,
        max_chunks=args.max_chunks,
        no_llm=args.no_llm,
        llm_model=args.llm_model,
        orchestrator=args.orchestrator,
    )

    try:
        # Dispatch to the requested orchestration layer. Both branches call the
        # same stage functions, so CLI behavior does not depend on graph usage.
        if args.orchestrator == "langgraph":
            result = run_langgraph_workflow(config, review_client=review_client)
        else:
            result = run_standard_workflow(config, review_client=review_client)
    except LangGraphUnavailableError:
        print(f"error: {LANGGRAPH_INSTALL_MESSAGE}", file=sys.stderr)
        return 1
    except WorkflowLLMConfigurationError as exc:
        print(
            f"error: LLM claim review requested but not configured: {exc} "
            "Rerun with --no-llm for deterministic evidence-pack mode.",
            file=sys.stderr,
        )
        # The workflow has already written a trace with failure statuses.
        return 1
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(
            f"error: source path cannot be read: {args.sources}: {exc}",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        target = args.sources if args.sources is not None else args.output_dir
        prefix = (
            "source path cannot be read"
            if args.sources is not None
            else "output directory cannot be written"
        )
        print(f"error: {prefix}: {target}: {exc}", file=sys.stderr)
        return 1

    _print_written_artifacts(config, result)
    return workflow_exit_code(config, result)



def _print_written_artifacts(config: WorkflowConfig, result: WorkflowResult) -> None:
    """Print user guidance after artifacts have already been written.

    These messages are not part of artifact generation or validation. They only
    help a CLI user find the files that the workflow reported as written.
    """

    if config.sources_path is not None and result.source_inventory_written:
        print(f"Wrote source inventory: {config.output_dir / 'source_inventory.json'}")
        print(f"Wrote evidence index: {config.output_dir / 'evidence_index.json'}")
        print(f"Wrote review question: {config.output_dir / 'review_question.json'}")
        print(f"Wrote retrieval trace: {config.output_dir / 'retrieval_trace.json'}")
        print(f"Wrote evidence pack JSON: {config.output_dir / 'evidence_pack.json'}")
        print(f"Wrote evidence pack Markdown: {result.evidence_pack_markdown_path}")
    if config.sources_path is not None and not config.no_llm:
        if result.project_evidence_report_written:
            print(
                f"Wrote {PROJECT_EVIDENCE_REPORT_FILE_NAME}: "
                f"{result.project_evidence_report_path}"
            )
            print(f"First artifact to open: {result.project_evidence_report_path}")
            print(f"Wrote evidence pack Markdown: {result.evidence_pack_markdown_path}")
        if result.claim_review_written:
            print(f"Wrote claim review: {result.claim_review_path}")
        if result.missing_evidence_written:
            print(f"Wrote missing evidence: {result.missing_evidence_path}")
        if result.contradiction_log_written:
            print(f"Wrote contradiction log: {result.contradiction_log_path}")
    print(f"Wrote project evidence trace: {result.trace_path}")
