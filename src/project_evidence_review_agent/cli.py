"""Command-line interface for the PR #1 scaffold.

The CLI accepts a review question and an output directory, then writes a local
trace artifact proving that the scaffold ran. It exists now to establish the
operator-facing command and the project safety boundary before source loading,
evidence-pack building, bounded LLM review, or reporting are implemented.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from project_evidence_review_agent.trace import write_trace
from project_evidence_review_agent.version import __version__


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the scaffold command."""

    parser = argparse.ArgumentParser(
        prog="project-evidence-review",
        description=(
            "Write a scaffold trace for a future bounded project evidence "
            "review workflow. PR #1 does not load sources or perform review."
        ),
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Human review question to record in the scaffold trace.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where project_evidence_trace.json will be written.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the scaffold CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    trace_path = write_trace(question=args.question, output_dir=args.output_dir)
    print(f"Wrote scaffold trace: {trace_path}")
    return 0
