# Roadmap

This roadmap keeps early work narrow and reviewable. Each step should preserve the project boundary: the workflow helps a human inspect bounded evidence, but it does not approve projects or replace governance.

## Planned PR sequence

1. **PR #1 repo scaffold** — create the package, CLI, trace stub, tests, linting, CI, and documentation.
2. **PR #2 local source inventory and intake** — define local source inputs and record what files are available for later evidence processing.
3. **PR #3 chunking and evidence index** — split supported local text sources into reviewable chunks and create a deterministic index.
4. **PR #4 review question and retrieval** — connect review questions to bounded local evidence candidates.
5. **PR #5 deterministic evidence pack Markdown** — write a human-readable evidence pack before any LLM review.
6. **PR #6 bounded LLM claim review** — add an LLM-default review step that reasons only over supplied evidence and cites evidence IDs.
7. **PR #7 missing evidence and contradiction detection** — identify gaps and possible contradictions for human review.
8. **PR #8 human-readable project evidence report** — produce a clear report that separates evidence, gaps, contradictions, and suggested human checks.
9. **PR #9 LangGraph orchestration, if still appropriate** — add graph orchestration only if the workflow benefits from it.
10. **PR #10 docs, examples, comments, and release polish** — improve examples, comments, and release readiness without expanding the authority boundary.
