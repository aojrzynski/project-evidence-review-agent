# Roadmap

Each step should preserve the project boundary: the workflow helps a human inspect bounded evidence, but it does not approve projects or replace governance.

## Planned PR sequence

1. **PR #1 repo scaffold** — create the package, CLI, trace stub, tests, linting, CI, and documentation.
2. **PR #2 local source inventory and intake** — add `--sources`, inspect one local file or directory, load supported Markdown, text, JSON, YAML, and CSV files for bounded metadata, skip unsupported files with reasons, write `source_inventory.json`, and keep the trace explicit that no evidence review has happened.
3. **PR #3 chunking and evidence index** — split loaded supported local sources into bounded chunks, assign stable `EV-0001`-style evidence IDs, preserve source references plus line or row references where practical, and write `evidence_index.json` without retrieval or review.
4. **PR #4 review question and retrieval** — record the supplied review question, run deterministic keyword retrieval over evidence chunks, explain selected chunks in `retrieval_trace.json`, and write bounded `evidence_pack.json` without reviewing claims.
5. **PR #5 deterministic evidence pack Markdown** — render `evidence_pack.md` from the same `evidence_pack.json` payload, showing selected chunks, source references, matched terms, retrieval scores, limitations, and review-preparation boundaries before any LLM review.
6. **PR #6 bounded LLM claim review** — build an LLM-safe context from the selected evidence pack, call an optional LLM client, write validated `claim_review.json`, reject malformed, uncited, invented, or authority-overreaching output, and keep `--no-llm` deterministic mode available.
7. **PR #7 missing evidence and contradiction detection** — after a successful validated claim review, run one bounded follow-up LLM call, write validated `missing_evidence.json` and `contradiction_log.json`, require contradiction candidates to cite valid evidence IDs on both sides, and treat gaps and possible tensions as human-review support only.
8. **PR #8 human-readable project evidence report** — current capability: after claim review and follow-up validation pass, write `project_evidence_report.md` as the first artifact to open in a successful full run. The report assembles validated artifacts, separates supported points, unclear points, gap signals, possible tensions, human checks, limitations, and authority boundaries, and does not make another LLM call.
9. **PR #9 LangGraph orchestration, if still appropriate** — add graph orchestration only if the workflow benefits from it, while keeping business logic in normal testable modules.
10. **PR #10 docs, examples, comments, and release polish** — improve examples, comments, and release readiness without expanding the authority boundary.

## Current PR #8 boundary

PR #8 records the supplied review question, retrieves lexically relevant chunks from the deterministic evidence index, writes a bounded JSON evidence pack, renders `evidence_pack.md`, builds `llm_safe_review_context.json`, writes validated `claim_review.json`, writes `missing_evidence.json` and `contradiction_log.json` only when claim review succeeds, and then writes `project_evidence_report.md` only when all prior LLM and follow-up validation passes.

Missing evidence is a gap signal within the supplied evidence, not proof that something does not exist. Contradiction candidates are possible tensions that require human review, not final findings. The report is review material, not project approval, readiness certification, compliance certification, or go-live approval. Human review remains the final authority.
