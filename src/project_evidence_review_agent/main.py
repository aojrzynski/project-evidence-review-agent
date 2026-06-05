"""Compatibility entrypoint for the Project Evidence Review Agent CLI.

The canonical console script points to :mod:`project_evidence_review_agent.cli`.
This module stays intentionally small so the module form exercises the same
local source intake path during early development.
"""

from project_evidence_review_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
