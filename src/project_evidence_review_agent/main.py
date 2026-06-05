"""Compatibility entrypoint for the Project Evidence Review Agent CLI.

The canonical console script points to :mod:`project_evidence_review_agent.cli`.
This module stays intentionally small so `python -m project_evidence_review_agent.main`
can exercise the same scaffold path during early development.
"""

from project_evidence_review_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
