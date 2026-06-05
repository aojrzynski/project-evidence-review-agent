# Project Evidence Review Agent

Project Evidence Review Agent is a bounded, local-first workflow for helping a human inspect project evidence. It organizes supplied project material, records what was found and skipped, creates bounded evidence chunks for later citation, and keeps authority with the reviewer.

It does not approve projects, certify readiness, replace governance, or make legal, compliance, privacy, security, or go-live decisions. Human review remains the final authority.

## Plain-English purpose

Project work often leaves evidence spread across plans, notes, decisions, risks, test notes, and release materials. When someone asks whether a claim is supported, the first problem is not to generate a confident answer. The first problem is to identify the local material that was supplied, show what the tool could load, show what it skipped, and prepare small source references that can be checked later.

PR #3 adds deterministic evidence indexing after source inventory. The tool can now inventory local source files and write a deterministic `source_inventory.json` artifact, then split loaded supported files into bounded chunks in `evidence_index.json`. Source inventory is not evidence review. Evidence indexing is not evidence review. A chunk existing does not mean its contents support the review question.

## Deterministic evidence packs and LLM review

The planned workflow has two different layers:

1. **Deterministic evidence-pack building** will inspect supplied local sources, inventory them, chunk them, retrieve relevant passages, and write bounded evidence packs. This layer should be reproducible and inspectable.
2. **LLM review** will later reason over the bounded evidence pack. The full future review workflow is LLM-default, but the model must reason only over supplied evidence and cite evidence IDs when assessing claims.

A later `--no-llm` mode should mean evidence-pack-only. It should not mean a full review without the model. In that mode, the tool should stop after producing deterministic evidence artifacts for a human or separate review step.

## What PR #3 currently does

PR #3 provides local source inventory plus deterministic evidence indexing:

- Defines the `project_evidence_review_agent` Python package.
- Adds the `project-evidence-review` CLI command.
- Accepts `--question`, `--output-dir`, `--sources`, and `--version`.
- Accepts one local source path as either a file or directory.
- Walks directories recursively while ignoring hidden directories and common Python/tooling cache directories.
- Loads supported local Markdown, text, JSON, YAML, and CSV files for bounded metadata.
- Skips unsupported file extensions with clear reasons.
- Creates the output directory when needed.
- Writes `source_inventory.json` when `--sources` is supplied.
- Writes `evidence_index.json` when `--sources` is supplied.
- Creates stable `EV-0001`-style evidence IDs in deterministic source and chunk order.
- Links each evidence chunk back to `SRC-0001`-style source inventory records.
- Preserves line references for Markdown and text where practical.
- Preserves row references for CSV data rows where practical.
- Continues writing `project_evidence_trace.json`.
- Records that no retrieval, evidence pack, LLM review, or approval decision happened.
- Adds synthetic example project material, tests, Ruff configuration, and CI-ready checks.

## Supported source file types

PR #3 supports these extensions:

- `.md`
- `.txt`
- `.json`
- `.yaml`
- `.yml`
- `.csv`

Unsupported files are not treated as review failures. They are skipped with a reason in the source inventory and do not create evidence chunks. PDF, DOCX, OCR, web pages, remote services, external connectors, embeddings, vector databases, OpenAI, and LangGraph are not implemented in this PR.

## What `source_inventory.json` contains

When `--sources` is supplied, the tool writes `source_inventory.json` with deterministic records such as:

- `source_id`, such as `SRC-0001`.
- Relative `path` and `file_name`.
- File `extension` and `source_type`.
- `status`, either `loaded` or `skipped`.
- `skip_reason` for skipped files.
- `size_bytes`, where available.
- `line_count`, where practical.
- Bounded `content_preview` for supported text-like files.
- Parser metadata.
- Basic JSON/YAML top-level type and keys when practical.
- CSV row count and column names when practical.

The inventory deliberately does not dump whole documents into the artifact and does not say whether any source supports a claim.

## What `evidence_index.json` contains

When `--sources` is supplied, the tool also writes `evidence_index.json`. The evidence index answers a different question from source inventory:

- Source inventory says, “What local files were found, loaded, or skipped?”
- Evidence index says, “What bounded pieces of loaded local evidence are available for later retrieval and review?”

Each evidence chunk includes fields such as:

- `evidence_id`, such as `EV-0001`.
- `source_id`, such as `SRC-0001`.
- `source_path`, `source_file_name`, and `source_type`.
- `chunk_index` within the source.
- `heading`, where practical.
- `start_line` and `end_line` for Markdown and text where practical.
- `start_row` and `end_row` for CSV data rows where practical.
- `text`, `text_preview`, `char_count`, and `word_count`.
- `chunk_strategy`, which explains how the chunk was created.

Chunks are bounded so later review steps can work with small, inspectable source references instead of entire files. Stable evidence IDs matter because later retrieval, citation, validation, and human checks need a consistent way to point back to the same chunk. Line and row references help a human find the original local source location.

The evidence index is still preparation only. It does not retrieve chunks for the question, decide whether a chunk supports or contradicts anything, call an LLM, or make a project decision.

## What is not implemented yet

PR #3 deliberately does not:

- Create `review_question.json`.
- Retrieve evidence for the question.
- Create `retrieval_trace.json`.
- Create `evidence_pack.json`.
- Create `evidence_pack.md`.
- Call an LLM.
- Add OpenAI, LangGraph, embeddings, vector databases, or external connectors.
- Parse PDF, DOCX, OCR, web pages, Google Drive, GitHub APIs, or other remote systems.
- Detect missing evidence.
- Detect contradictions.
- Produce a final project evidence report.
- Produce readiness, approval, compliance, privacy, security, certification, or go-live verdicts.

Full review mode will come later, after deterministic source intake, chunking, retrieval, and evidence-pack artifacts are in place.

## Safety and authority boundaries

The workflow is intended to help a human review evidence. It must not become an approval engine.

Current and future outputs should preserve these boundaries:

- The tool should separate inventory from evidence indexing and evidence review.
- Loading a file should not imply that the file supports any project claim.
- Creating a chunk should not imply that the chunk is relevant to the review question.
- Future claims should cite evidence IDs.
- Missing evidence and possible contradictions should be shown as review prompts, not final verdicts.
- The LLM should eventually reason only over bounded supplied evidence.
- Human review remains the final authority.

## Synthetic local demo material

The example material under `examples/project_pack/` is fake and simple. Local demo material should stay synthetic and should not contain secrets, client data, private project data, credentials, tokens, or sensitive material.

## Quick start

Create and activate a virtual environment, then install the package in editable mode with development tools:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the intake and indexing command with synthetic local sources:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "Is the project ready for go-live?" \
  --output-dir outputs/evidence_index_run
```

Expected result:

```text
outputs/evidence_index_run/source_inventory.json
outputs/evidence_index_run/evidence_index.json
outputs/evidence_index_run/project_evidence_trace.json
```

The trace records the question, output directory, supplied source path, source inventory counts, evidence chunk counts, package version, timestamp, and authority boundary. It also confirms that no retrieval, evidence pack, LLM review, or approval decision happened.

You can still run without `--sources` to write only the trace:

```bash
project-evidence-review --question "What evidence supports this claim?" --output-dir outputs/scaffold_run
```

You can also run the package module directly:

```bash
python -m project_evidence_review_agent \
  --sources examples/project_pack \
  --question "What evidence supports this claim?" \
  --output-dir outputs/example
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
