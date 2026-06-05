"""Project Evidence Review Agent package.

This package will grow into a bounded, local-first workflow for reviewing
project claims against supplied evidence. The PR #1 scaffold intentionally does
not load sources, retrieve evidence, call an LLM, or make approval decisions.
Human review remains the final authority.
"""

from project_evidence_review_agent.version import __version__

__all__ = ["__version__"]
