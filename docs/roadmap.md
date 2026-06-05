# Roadmap

This roadmap keeps early work narrow and reviewable. Each step should preserve the project boundary: the workflow helps a human inspect bounded evidence, but it does not approve projects or replace governance.

## Planned PR sequence

1. **PR #1 repo scaffold** — create the package, CLI, trace stub, tests, linting, CI, and documentation.
2. **PR #2 local source inventory and intake** — add `--sources`, inspect one local file or directory, load supported Markdown, text, JSON, YAML, and CSV files for bounded metadata, skip unsupported files with reasons, write `source_inventory.json`, and keep the trace explicit that no evidence review has happened.
3. **PR #3 chunking and evidence index** — split loaded supported local sources into bounded chunks, assign stable `EV-0001`-style evidence IDs, preserve source references plus line or row references where practical, and write `evidence_index.json` without retrieval or review.
4. **PR #4 review question and retrieval** — record the supplied review question, run deterministic keyword retrieval over evidence chunks, explain selected chunks in `retrieval_trace.json`, and write bounded `evidence_pack.json` without reviewing claims.
5. **PR #5 deterministic evidence pack Markdown** — render `evidence_pack.md` from the same `evidence_pack.json` payload, showing selected chunks, source references, matched terms, retrieval scores, limitations, and review-preparation boundaries before any LLM review.
6. **PR #6 bounded LLM claim review** — current capability: build an LLM-safe context from the selected evidence pack, call an optional LLM client, write validated `claim_review.json`, reject malformed, uncited, invented, or authority-overreaching output, and keep `--no-llm` deterministic mode available.
7. **PR #7 missing evidence and contradiction detection** — identify gaps and possible contradictions for human review.
8. **PR #8 human-readable project evidence report** — produce a clear report that separates evidence, gaps, contradictions, and suggested human checks.
9. **PR #9 LangGraph orchestration, if still appropriate** — add graph orchestration only if the workflow benefits from it.
10. **PR #10 docs, examples, comments, and release polish** — improve examples, comments, and release readiness without expanding the authority boundary.

## Current PR #6 boundary

PR #6 records the supplied review question, retrieves lexically relevant chunks from the deterministic evidence index, writes a bounded JSON evidence pack, renders `evidence_pack.md`, builds `llm_safe_review_context.json`, and writes `claim_review.json` when LLM output passes deterministic validation. The LLM receives only selected evidence-pack content and allowed evidence IDs.

Claim review is still review material only. It does not detect missing evidence as a separate workflow stage, detect contradictions as a separate workflow stage, write the final project evidence report, or produce readiness, compliance, certification, approval, or go-live decisions. Human review remains the final authority.
