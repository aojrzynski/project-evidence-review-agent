"""Command-line interface for local project evidence intake.

The CLI records a human review question and writes trace artifacts for a bounded
local workflow. PR #2 adds ``--sources`` so the tool can inventory local files
before later evidence chunking exists. This intake stage describes supplied
material; it does not interpret files as evidence, retrieve passages, call an
LLM, or approve a project.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from project_evidence_review_agent.source_inventory import write_source_inventory
from project_evidence_review_agent.trace import write_trace
from project_evidence_review_agent.version import __version__


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the intake command."""

    parser = argparse.ArgumentParser(
        prog="project-evidence-review",
        description=(
            "Write trace artifacts for a bounded project evidence review "
            "workflow. PR #2 can inventory local sources but does not review."
        ),
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Human review question to record in the trace.",
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
        help=(
            "Optional local file or directory to inventory before review stages exist."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
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
    loaded_source_count = 0
    skipped_source_count = 0
    if args.sources is not None:
        try:
            inventory_summary = write_source_inventory(
                sources_path=args.sources,
                output_dir=args.output_dir,
            )
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
        loaded_source_count = inventory_summary.loaded_count
        skipped_source_count = inventory_summary.skipped_count
        print(f"Wrote source inventory: {inventory_summary.path}")

    try:
        trace_path = write_trace(
            question=args.question,
            output_dir=args.output_dir,
            sources_path=args.sources,
            source_inventory_written=source_inventory_written,
            loaded_source_count=loaded_source_count,
            skipped_source_count=skipped_source_count,
        )
    except OSError as exc:
        print(
            f"error: output directory cannot be written: {args.output_dir}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote project evidence trace: {trace_path}")
    return 0
