# Bounded LLM claim review

The LLM receives only a bounded evidence pack because the review question must stay tied to supplied local evidence. The model is not allowed to answer from memory, invent sources, or expand the context beyond selected evidence chunks.

## Why the context is saved

`llm_safe_review_context.json` records exactly what is available to the model:

- The review question.
- Selected evidence chunks.
- Allowed `EV-0001`-style evidence IDs.
- Source metadata needed for citations.
- Review instructions and authority boundaries.

Saving the context lets a human audit the model input before reading the claim review.

## Why every supported claim needs evidence IDs

A claim marked `evidence_supported` or `partially_supported` must cite existing evidence IDs. Citation validation keeps the review connected to the bounded evidence pack. A source ID alone is not enough because claims are evaluated against selected chunks, not entire files.

## What validation rejects

Validation rejects output that is malformed, misses required fields, uses an unsupported claim status, invents evidence IDs, omits citations for supported claims, cites source IDs in place of evidence IDs, or uses approval and verdict language.

A failed validation is safer than a misleading successful review. The failed artifact preserves validator messages and rejected item summaries without treating unsafe model output as accepted review material.

## Not approval

`claim_review.json` is not a project decision. It does not approve readiness, compliance, certification, security, privacy, legal status, or go-live. Human review remains the final authority.
