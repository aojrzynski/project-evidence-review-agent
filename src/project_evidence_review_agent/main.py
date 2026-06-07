"""Compatibility entrypoint for the Project Evidence Review Agent CLI.

The canonical console script points to :mod:`project_evidence_review_agent.cli`.
This compatibility module stays intentionally small so older imports or scripts
reach the same CLI path without duplicating argument parsing or workflow logic.
"""

from project_evidence_review_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
