"""Module entry point for ``python -m project_evidence_review_agent``.

The installed console script and ``python -m`` path both delegate to the same CLI
function so argument parsing and exit-code behavior stay in one place.
"""

from project_evidence_review_agent.cli import main

raise SystemExit(main())
