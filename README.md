# Project Evidence Review Agent

Project Evidence Review Agent is a local-first workflow scaffold for reviewing project claims against bounded evidence.

It is designed for questions such as:

- What evidence do we have for this project claim?
- What evidence is missing?
- What may contradict the claim?
- What should a human reviewer check next?

The project does not approve projects, certify readiness, replace governance, or make legal, compliance, privacy, security, or go-live decisions. Human review remains the final authority.

## Plain-English purpose

Project work often leaves evidence spread across plans, notes, tickets, decisions, and review materials. When someone asks whether a claim is supported, the first problem is not to generate a confident answer. The first problem is to gather the relevant local evidence, show what was considered, show what was missing, and keep the final judgment with a human reviewer.

This repository starts that workflow in small steps. PR #1 only creates the Python package, command-line entrypoint, trace artifact, tests, linting, CI, and initial documentation.

## Deterministic evidence packs and LLM review

The planned workflow has two different layers:

1. **Deterministic evidence-pack building** will inspect supplied local sources, inventory them, chunk them, retrieve relevant passages, and write bounded evidence packs. This layer should be reproducible and inspectable.
2. **LLM review** will later reason over the bounded evidence pack. The full future review workflow is LLM-default, but the model must reason only over supplied evidence and cite evidence IDs when assessing claims.

A later `--no-llm` mode should mean evidence-pack-only. It should not mean a full review without the model. In that mode, the tool should stop after producing deterministic evidence artifacts for a human or separate review step.

## What PR #1 currently does

PR #1 provides a narrow scaffold:

- Defines the `project_evidence_review_agent` Python package.
- Adds the `project-evidence-review` CLI command.
- Accepts `--question`, `--output-dir`, and `--version`.
- Creates the output directory when needed.
- Writes one artifact: `project_evidence_trace.json`.
- Records that the run is scaffold-only and that no source loading or evidence review has happened.
- Adds tests, Ruff configuration, and GitHub Actions CI.

## What is not implemented yet

PR #1 deliberately does not:

- Load project sources.
- Support `--sources`.
- Chunk documents.
- Retrieve evidence.
- Create evidence IDs.
- Write `source_inventory.json`.
- Write `evidence_index.json`.
- Write `evidence_pack.json` or `evidence_pack.md`.
- Call an LLM.
- Add OpenAI, LangGraph, embeddings, vector databases, or external connectors.
- Parse PDF, DOCX, OCR, web pages, Google Drive, GitHub APIs, or other remote systems.
- Produce readiness, approval, compliance, privacy, security, or go-live verdicts.

## Safety and authority boundaries

The workflow is intended to help a human review evidence. It must not become an approval engine.

Current and future outputs should preserve these boundaries:

- The tool should separate evidence from interpretation.
- Future claims should cite evidence IDs.
- Missing evidence and possible contradictions should be shown as review prompts, not final verdicts.
- The LLM should eventually reason only over bounded supplied evidence.
- Human review remains the final authority.

## Quick start

Create and activate a virtual environment, then install the package in editable mode with development tools:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the scaffold command:

```bash
project-evidence-review --question "Is the project ready for go-live?" --output-dir outputs/scaffold_run
```

Expected result:

```text
outputs/scaffold_run/project_evidence_trace.json
```

The trace records the question, package version, timestamp, output directory, scaffold status, and authority boundary.

You can also run the package module directly:

```bash
python -m project_evidence_review_agent --question "What evidence supports this claim?" --output-dir outputs/example
```

## Run tests and checks

```bash
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

These are also the commands run by GitHub Actions CI.

## Roadmap

The initial planned sequence is documented in [docs/roadmap.md](docs/roadmap.md):

1. PR #1 repo scaffold
2. PR #2 local source inventory and intake
3. PR #3 chunking and evidence index
4. PR #4 review question and retrieval
5. PR #5 deterministic evidence pack Markdown
6. PR #6 bounded LLM claim review
7. PR #7 missing evidence and contradiction detection
8. PR #8 human-readable project evidence report
9. PR #9 LangGraph orchestration, if still appropriate
10. PR #10 docs, examples, comments, and release polish
