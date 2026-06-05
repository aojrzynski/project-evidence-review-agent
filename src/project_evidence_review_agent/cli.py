"""Command-line interface for bounded project evidence review.

The CLI records a human review question, inventories supported local sources,
creates deterministic evidence packs, and, unless ``--no-llm`` is used, runs
bounded LLM review and follow-up analysis over selected evidence. After those
LLM-backed artifacts pass validation, it assembles a human-readable project
evidence report without making another LLM call or approving a project.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    DEFAULT_LLM_MODEL,
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
    PROJECT_EVIDENCE_REPORT_FILE_NAME,
    write_project_evidence_report,
)
from project_evidence_review_agent.retrieval import (
    validate_max_chunks,
    write_retrieval_outputs,
)
from project_evidence_review_agent.review_question import write_review_question
from project_evidence_review_agent.source_inventory import (
    build_source_inventory,
    write_source_inventory_payload,
)
from project_evidence_review_agent.trace import write_trace
from project_evidence_review_agent.version import __version__


def _positive_int(value: str) -> int:
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
    """Create the CLI parser for the evidence preparation command."""

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
    parser.add_argument(
        "--max-chunks",
        type=_positive_int,
        default=10,
        help=(
            "Maximum selected chunks for evidence_pack.json. "
            "Must be positive. Default: 10."
        ),
    )
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
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(
            f"error: output directory cannot be written: {args.output_dir}: {exc}",
            file=sys.stderr,
        )
        return 1

    source_inventory_written = False
    evidence_index_written = False
    review_question_written = False
    retrieval_trace_written = False
    evidence_pack_written = False
    evidence_pack_markdown_written = False
    evidence_pack_markdown_path = None
    loaded_source_count = 0
    skipped_source_count = 0
    evidence_chunk_count = 0
    selected_evidence_chunk_count = 0
    source_fingerprint_warning_count = 0
    chunking_status = "not_requested"
    llm_safe_review_context_written = False
    llm_safe_review_context_path = None
    claim_review_written = False
    claim_review_path = None
    llm_review_status = "not_performed"
    claim_review_validation_status = "not_performed"
    claim_count = 0
    rejected_claim_count = 0
    validator_message_count = 0
    missing_evidence_written = False
    missing_evidence_path = None
    missing_evidence_status = "not_performed"
    missing_evidence_validation_status = "not_performed"
    missing_evidence_count = 0
    rejected_missing_evidence_count = 0
    contradiction_log_written = False
    contradiction_log_path = None
    contradiction_detection_status = "not_performed"
    contradiction_validation_status = "not_performed"
    contradiction_candidate_count = 0
    rejected_contradiction_count = 0
    project_evidence_report_written = False
    project_evidence_report_path = None
    project_evidence_report_status = "not_requested_or_not_applicable"
    report_claim_count = 0
    report_missing_evidence_count = 0
    report_contradiction_candidate_count = 0
    report_human_check_count = 0

    if args.sources is not None:
        try:
            inventory = build_source_inventory(args.sources)
            inventory_summary = write_source_inventory_payload(
                inventory=inventory,
                output_dir=args.output_dir,
            )
            evidence_index = build_evidence_index(
                inventory=inventory,
                sources_path=args.sources,
            )
            evidence_index_summary = write_evidence_index(
                inventory=inventory,
                sources_path=args.sources,
                output_dir=args.output_dir,
                evidence_index=evidence_index,
            )
            review_question_path = write_review_question(
                question=args.question,
                output_dir=args.output_dir,
            )
            retrieval_summary = write_retrieval_outputs(
                question=args.question,
                evidence_index=evidence_index,
                max_chunks=args.max_chunks,
                output_dir=args.output_dir,
            )
            evidence_pack_markdown_path = write_evidence_pack_markdown(
                evidence_pack=retrieval_summary.evidence_pack_payload,
                output_dir=args.output_dir,
            )
            if args.no_llm:
                llm_review_status = "skipped_no_llm"
                missing_evidence_status = "skipped_no_llm"
                contradiction_detection_status = "skipped_no_llm"
                project_evidence_report_status = "skipped_no_llm"
            else:
                llm_safe_context = build_llm_safe_review_context(
                    retrieval_summary.evidence_pack_payload
                )
                llm_safe_review_context_path = write_llm_safe_review_context(
                    evidence_pack=retrieval_summary.evidence_pack_payload,
                    output_dir=args.output_dir,
                )
                llm_safe_review_context_written = True
                try:
                    client = (
                        review_client
                        if review_client is not None
                        else OpenAIReviewClient()
                    )
                except LLMConfigurationError as exc:
                    llm_review_status = "failed"
                    claim_review_validation_status = "not_validated"
                    missing_evidence_status = "skipped_claim_review_failed"
                    contradiction_detection_status = "skipped_claim_review_failed"
                    project_evidence_report_status = "skipped_claim_review_failed"
                    print(
                        f"error: LLM claim review requested but not configured: {exc} "
                        "Rerun with --no-llm for deterministic evidence-pack mode.",
                        file=sys.stderr,
                    )
                else:
                    claim_review_result = run_claim_review(
                        context=llm_safe_context,
                        client=client,
                        model=args.llm_model,
                        output_dir=args.output_dir,
                    )
                    claim_review_written = True
                    claim_review_path = claim_review_result.path
                    llm_review_status = claim_review_result.llm_review_status
                    claim_review_validation_status = (
                        claim_review_result.validation_status
                    )
                    claim_count = claim_review_result.claim_count
                    rejected_claim_count = claim_review_result.rejected_claim_count
                    validator_message_count = (
                        claim_review_result.validator_message_count
                    )
                    if claim_review_validation_status == "passed":
                        follow_up_result = run_follow_up_analysis(
                            llm_context=llm_safe_context,
                            claim_review=claim_review_result.payload,
                            client=client,
                            model=args.llm_model,
                            output_dir=args.output_dir,
                        )
                        missing_evidence_written = True
                        missing_evidence_path = follow_up_result.missing_evidence_path
                        missing_evidence_status = (
                            follow_up_result.missing_evidence_status
                        )
                        missing_evidence_validation_status = (
                            follow_up_result.missing_validation_status
                        )
                        missing_evidence_count = follow_up_result.missing_count
                        rejected_missing_evidence_count = (
                            follow_up_result.rejected_missing_count
                        )
                        contradiction_log_written = True
                        contradiction_log_path = follow_up_result.contradiction_log_path
                        contradiction_detection_status = (
                            follow_up_result.contradiction_status
                        )
                        contradiction_validation_status = (
                            follow_up_result.contradiction_validation_status
                        )
                        contradiction_candidate_count = (
                            follow_up_result.contradiction_count
                        )
                        rejected_contradiction_count = (
                            follow_up_result.rejected_contradiction_count
                        )
                        if (
                            missing_evidence_status == "completed"
                            and missing_evidence_validation_status == "passed"
                            and contradiction_detection_status == "completed"
                            and contradiction_validation_status == "passed"
                        ):
                            trace_summary = {
                                "loaded_source_count": (inventory_summary.loaded_count),
                                "skipped_source_count": (
                                    inventory_summary.skipped_count
                                ),
                                "evidence_chunk_count": (
                                    evidence_index_summary.chunk_count
                                ),
                                "project_evidence_report_status": "written",
                            }
                            report_summary = write_project_evidence_report(
                                output_dir=args.output_dir,
                                evidence_pack=retrieval_summary.evidence_pack_payload,
                                claim_review=claim_review_result.payload,
                                missing_evidence=(
                                    follow_up_result.missing_evidence_payload
                                ),
                                contradiction_log=(
                                    follow_up_result.contradiction_payload
                                ),
                                trace_summary=trace_summary,
                            )
                            project_evidence_report_written = True
                            project_evidence_report_path = report_summary.path
                            project_evidence_report_status = "written"
                            report_claim_count = report_summary.claim_count
                            report_missing_evidence_count = (
                                report_summary.missing_evidence_count
                            )
                            report_contradiction_candidate_count = (
                                report_summary.contradiction_candidate_count
                            )
                            report_human_check_count = report_summary.human_check_count
                        else:
                            project_evidence_report_status = "skipped_followup_failed"
                    else:
                        missing_evidence_status = "skipped_claim_review_failed"
                        contradiction_detection_status = "skipped_claim_review_failed"
                        project_evidence_report_status = "skipped_claim_review_failed"
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
            print(
                f"error: source path cannot be read: {args.sources}: {exc}",
                file=sys.stderr,
            )
            return 1

        source_inventory_written = True
        evidence_index_written = True
        review_question_written = True
        retrieval_trace_written = True
        evidence_pack_written = True
        evidence_pack_markdown_written = True
        loaded_source_count = inventory_summary.loaded_count
        skipped_source_count = inventory_summary.skipped_count
        evidence_chunk_count = evidence_index_summary.chunk_count
        selected_evidence_chunk_count = retrieval_summary.selected_chunk_count
        source_fingerprint_warning_count = max(
            evidence_index.get("summary", {}).get(
                "source_fingerprint_warning_count", 0
            ),
            retrieval_summary.source_fingerprint_warning_count,
        )
        chunking_status = evidence_index_summary.status
        print(f"Wrote source inventory: {inventory_summary.path}")
        print(f"Wrote evidence index: {evidence_index_summary.path}")
        print(f"Wrote review question: {review_question_path}")
        print(f"Wrote retrieval trace: {retrieval_summary.retrieval_trace_path}")
        print(f"Wrote evidence pack JSON: {retrieval_summary.evidence_pack_path}")
        print(f"Wrote evidence pack Markdown: {evidence_pack_markdown_path}")

    try:
        trace_path = write_trace(
            question=args.question,
            output_dir=args.output_dir,
            sources_path=args.sources,
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
            max_chunks=args.max_chunks,
            source_fingerprint_warning_count=source_fingerprint_warning_count,
            no_llm=args.no_llm,
            llm_model=args.llm_model,
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
            report_input_artifacts=INPUT_ARTIFACTS
            if project_evidence_report_written
            else [],
            report_claim_count=report_claim_count,
            report_missing_evidence_count=report_missing_evidence_count,
            report_contradiction_candidate_count=report_contradiction_candidate_count,
            report_human_check_count=report_human_check_count,
            final_report_is_not_approval=True,
        )
    except OSError as exc:
        print(
            f"error: output directory cannot be written: {args.output_dir}: {exc}",
            file=sys.stderr,
        )
        return 1

    if args.sources is not None and not args.no_llm:
        if project_evidence_report_written:
            print(
                f"Wrote {PROJECT_EVIDENCE_REPORT_FILE_NAME}: "
                f"{project_evidence_report_path}"
            )
            print(f"First artifact to open: {project_evidence_report_path}")
            print(f"Wrote evidence pack Markdown: {evidence_pack_markdown_path}")
        if claim_review_written:
            print(f"Wrote claim review: {claim_review_path}")
        if missing_evidence_written:
            print(f"Wrote missing evidence: {missing_evidence_path}")
        if contradiction_log_written:
            print(f"Wrote contradiction log: {contradiction_log_path}")
    print(f"Wrote project evidence trace: {trace_path}")
    if (
        args.sources is not None
        and not args.no_llm
        and (
            llm_review_status == "failed"
            or claim_review_validation_status == "failed"
            or missing_evidence_status == "failed"
            or missing_evidence_validation_status == "failed"
            or contradiction_detection_status == "failed"
            or contradiction_validation_status == "failed"
        )
    ):
        return 1
    return 0
