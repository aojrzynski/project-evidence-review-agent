# Roadmap

This roadmap keeps early work narrow and reviewable. Each step should preserve the project boundary: the workflow helps a human inspect bounded evidence, but it does not approve projects or replace governance.

## Planned PR sequence

1. **PR #1 repo scaffold** — create the package, CLI, trace stub, tests, linting, CI, and documentation.
2. **PR #2 local source inventory and intake** — add `--sources`, inspect one local file or directory, load supported Markdown, text, JSON, YAML, and CSV files for bounded metadata, skip unsupported files with reasons, write `source_inventory.json`, and keep the trace explicit that no evidence review has happened.
3. **PR #3 chunking and evidence index** — split supported local text sources into reviewable chunks and create a deterministic index.
4. **PR #4 review question and retrieval** — connect review questions to bounded local evidence candidates.
5. **PR #5 deterministic evidence pack Markdown** — write a human-readable evidence pack before any LLM review.
6. **PR #6 bounded LLM claim review** — add an LLM-default review step that reasons only over supplied evidence and cites evidence IDs.
7. **PR #7 missing evidence and contradiction detection** — identify gaps and possible contradictions for human review.
8. **PR #8 human-readable project evidence report** — produce a clear report that separates evidence, gaps, contradictions, and suggested human checks.
9. **PR #9 LangGraph orchestration, if still appropriate** — add graph orchestration only if the workflow benefits from it.
10. **PR #10 docs, examples, comments, and release polish** — improve examples, comments, and release readiness without expanding the authority boundary.

## Current PR #2 boundary

PR #2 is source inventory only. It records supplied local material and skip reasons, but it does not chunk sources, retrieve evidence, build evidence packs, call an LLM, interpret claims, detect missing evidence, detect contradictions, write a final report, or produce readiness, compliance, certification, approval, or go-live decisions.
