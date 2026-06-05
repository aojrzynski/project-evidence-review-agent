# Roadmap

This roadmap keeps early work narrow and reviewable. Each step should preserve the project boundary: the workflow helps a human inspect bounded evidence, but it does not approve projects or replace governance.

## Planned PR sequence

1. **PR #1 repo scaffold** — create the package, CLI, trace stub, tests, linting, CI, and documentation.
2. **PR #2 local source inventory and intake** — add `--sources`, inspect one local file or directory, load supported Markdown, text, JSON, YAML, and CSV files for bounded metadata, skip unsupported files with reasons, write `source_inventory.json`, and keep the trace explicit that no evidence review has happened.
3. **PR #3 chunking and evidence index** — split loaded supported local sources into bounded chunks, assign stable `EV-0001`-style evidence IDs, preserve source references plus line or row references where practical, and write `evidence_index.json` without retrieval or review.
4. **PR #4 review question and retrieval** — record the supplied review question, run deterministic keyword retrieval over evidence chunks, explain selected chunks in `retrieval_trace.json`, and write bounded `evidence_pack.json` without reviewing claims.
5. **PR #5 deterministic evidence pack Markdown** — render `evidence_pack.md` from the same `evidence_pack.json` payload, showing selected chunks, source references, matched terms, retrieval scores, limitations, and review-preparation boundaries before any LLM review.
6. **PR #6 bounded LLM claim review** — add an LLM-default review step that reasons only over supplied evidence and cites evidence IDs.
7. **PR #7 missing evidence and contradiction detection** — identify gaps and possible contradictions for human review.
8. **PR #8 human-readable project evidence report** — produce a clear report that separates evidence, gaps, contradictions, and suggested human checks.
9. **PR #9 LangGraph orchestration, if still appropriate** — add graph orchestration only if the workflow benefits from it.
10. **PR #10 docs, examples, comments, and release polish** — improve examples, comments, and release readiness without expanding the authority boundary.

## Current PR #5 boundary

PR #5 records the supplied review question, retrieves lexically relevant chunks from the deterministic evidence index, explains retrieval choices, writes a bounded JSON evidence pack, and renders `evidence_pack.md` from that same payload. It also carries lightweight source fingerprints where practical so humans can see which local file version supplied selected evidence.

The Markdown evidence pack is still preparation only. It does not decide whether a claim is supported, detect missing evidence, detect contradictions, call an LLM, write the final project evidence report, or produce readiness, compliance, certification, approval, or go-live decisions. A selected chunk means keyword relevance, not proof or completeness.
