"""Project Evidence Review Agent package.

This package provides a bounded, local-first workflow for organizing supplied
project evidence, preparing deterministic evidence packs, and optionally running
validation-bounded LLM review over selected evidence. It does not make approval,
readiness, compliance, certification, or go-live decisions. Human review remains
the final authority.
"""

from project_evidence_review_agent.version import __version__

__all__ = ["__version__"]
