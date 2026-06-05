# Project Evidence Review Agent

Project Evidence Review Agent is a bounded, local-first workflow for helping a human inspect project evidence. It organizes supplied project material, records what was found and skipped, creates bounded evidence chunks, retrieves lexically relevant chunks for a review question, and keeps authority with the reviewer.

It does not approve projects, certify readiness, replace governance, or make legal, compliance, privacy, security, or go-live decisions. Human review remains the final authority.

## Plain-English purpose

Project work often leaves evidence spread across plans, notes, decisions, risks, test notes, and release materials. When someone asks whether a claim is supported, the first problem is not to generate a confident answer. The first problem is to identify the local material that was supplied, show what the tool could load, show what it skipped, prepare small source references, and select a bounded set of chunks that match the review question.

PR #5 records the supplied review question, performs deterministic retrieval over the evidence index, writes `evidence_pack.json`, and renders the same payload as `evidence_pack.md`. Retrieval means keyword-based selection of chunks that appear lexically relevant to the question. Retrieval is not review. A selected chunk does not automatically support or contradict a claim, and a high retrieval score does not mean the evidence is complete or that a project is ready.

## Deterministic evidence packs and LLM review

The planned workflow has two different layers:

1. **Deterministic evidence-pack building** inspects supplied local sources, inventories them, chunks them, retrieves relevant passages, and writes bounded JSON evidence packs and readable Markdown views. This layer is reproducible and inspectable.
2. **LLM review** will later reason over the bounded evidence pack. The full future review workflow is LLM-default, but the model must reason only over supplied evidence and cite evidence IDs when assessing claims.

A later `--no-llm` mode should mean evidence-pack-only. It should not mean a full review without the model. In that mode, the tool should stop after producing deterministic evidence artifacts for a human or separate review step.

## What PR #5 currently does

PR #5 provides local source inventory, deterministic evidence indexing, review question recording, deterministic retrieval, a bounded JSON evidence pack, and a deterministic Markdown rendering of that same pack:

- Defines the `project_evidence_review_agent` Python package.
- Adds the `project-evidence-review` CLI command.
- Accepts `--question`, `--output-dir`, `--sources`, `--max-chunks`, and `--version`.
- Accepts one local source path as either a file or directory.
- Walks directories recursively while ignoring hidden directories and common Python/tooling cache directories.
- Loads supported local Markdown, text, JSON, YAML, and CSV files for bounded metadata.
- Skips unsupported file extensions with clear reasons.
- Adds lightweight source fingerprints, including SHA-256 and modified-time metadata where practical.
- Writes `source_inventory.json` when `--sources` is supplied.
- Writes `evidence_index.json` when `--sources` is supplied.
- Creates stable `EV-0001`-style evidence IDs in deterministic source and chunk order.
- Links each evidence chunk back to `SRC-0001`-style source inventory records.
- Preserves line references for Markdown and text where practical.
- Preserves row references for CSV data rows where practical.
- Writes `review_question.json` to record the supplied question and normalized terms.
- Writes `retrieval_trace.json` to explain selected chunks, matched terms, and scoring reasons.
- Writes `evidence_pack.json` with the bounded selected chunks for later reporting and LLM review.
- Writes `evidence_pack.md` as a human-readable view rendered from the same `evidence_pack.json` payload.
- Continues writing `project_evidence_trace.json`.
- Records that no LLM review, missing evidence detection, contradiction detection, final project evidence report, or approval decision happened.
- Adds synthetic example project material, tests, Ruff configuration, and CI-ready checks.

## Supported source file types

PR #5 supports these extensions:

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
- `sha256`, `modified_time_utc`, `modified_time_ns`, and `fingerprint_status`, where practical.
- `line_count`, where practical.
- Bounded `content_preview` for supported text-like files.
- Parser metadata.
- Basic JSON/YAML top-level type and keys when practical.
- CSV row count and column names when practical.

Source fingerprints help later artifacts show which local file version was used. They are not a full audit system and do not certify authenticity. If a timestamp or hash cannot be read, normal use should not be blocked.

## What `evidence_index.json` contains

When `--sources` is supplied, the tool also writes `evidence_index.json`. The evidence index answers a different question from source inventory:

- Source inventory says, “What local files were found, loaded, or skipped?”
- Evidence index says, “What bounded pieces of loaded local evidence are available for retrieval and later review?”

Each evidence chunk includes fields such as:

- `evidence_id`, such as `EV-0001`.
- `source_id`, such as `SRC-0001`.
- `source_path`, `source_file_name`, and `source_type`.
- Source fingerprint fields where practical.
- Same-run source consistency status and warnings if the file appears to change between inventory and indexing.
- `chunk_index` within the source.
- `heading`, where practical.
- `start_line` and `end_line` for Markdown and text where practical.
- `start_row` and `end_row` for CSV data rows where practical.
- `text`, `text_preview`, `char_count`, and `word_count`.
- `chunk_strategy`, which explains how the chunk was created.

Chunks are bounded so later review steps can work with small, inspectable source references instead of entire files. Stable evidence IDs matter because later retrieval, citation, validation, and human checks need a consistent way to point back to the same chunk.

## What `review_question.json` contains

`review_question.json` records the supplied review question before retrieval:

- The original question.
- A normalized lowercase form.
- Deterministic question terms after punctuation handling and stopword removal.
- A timestamp for when the question artifact was created.
- A boundary note explaining that recording a question does not answer it.

Review question recording is separate from retrieval so the input question is explicit and inspectable.

## What retrieval means

Retrieval uses a simple deterministic keyword approach:

- Lowercase terms.
- Strip punctuation with a local tokenizer.
- Remove a small built-in stopword list.
- Compare question terms with chunk text, headings, source file names, and source paths.
- Boost heading matches, source path matches, exact phrase matches, and common project-review terms such as testing, risks, requirements, decisions, release, and go-live.
- Use deterministic tie-breaking by evidence ID.
- Limit selected chunks with `--max-chunks`, which defaults to `10`.

This is explainable because `retrieval_trace.json` shows matched terms and scoring reasons. It is limited because keyword retrieval can miss relevant evidence that uses different words, and it cannot determine truth or completeness.

## What `retrieval_trace.json` contains

`retrieval_trace.json` explains the retrieval decision without duplicating full chunk text. It includes:

- The question, normalized question, and question terms.
- Retrieval strategy and scoring parameters.
- `max_chunks`, total chunks considered, and selected chunk count.
- Selected chunks with evidence IDs, source IDs, source paths, headings, scores, matched terms, scoring reasons, and line or row references where available.
- A bounded list of top unselected candidates, when useful.
- Source fingerprint notes and warnings, where relevant.
- Limitations and an authority boundary note.

The trace may say which chunks matched terms and why they were selected. It must not say that the project is ready, that evidence is complete, or that a claim is supported or contradicted.

## What `evidence_pack.json` contains

`evidence_pack.json` is the bounded machine-readable evidence pack used to render `evidence_pack.md` and support later LLM review. It includes:

- The review question.
- Retrieval strategy.
- Selected chunk count.
- Selected chunks with evidence IDs, source IDs, source paths, source file names, source types, headings, line or row references, text, text previews, matched terms, retrieval scores, and fingerprint metadata where practical.
- A compact `source_map` for selected sources.
- Limitations.
- An authority boundary.

The evidence pack does not include unsupported skipped files as evidence, does not dump the full source inventory, and does not include entire documents beyond the bounded selected chunks.

## What is not implemented yet

PR #5 deliberately does not:

- Create `project_evidence_report.md`.
- Call an LLM.
- Add OpenAI, LangGraph, embeddings, vector databases, or external connectors.
- Parse PDF, DOCX, OCR, web pages, Google Drive, GitHub APIs, or other remote systems.
- Decide whether claims are supported.
- Detect missing evidence.
- Detect contradictions.
- Produce a final project evidence report.
- Produce readiness, approval, compliance, privacy, security, certification, or go-live verdicts.

Full review mode will come later, after deterministic source intake, chunking, retrieval, and evidence-pack Markdown artifacts are in place.

## What to open first

When `--sources` is supplied, open `evidence_pack.md` first if you want a readable review-preparation artifact. It shows the review question, how the pack was built, selected evidence chunks, source references, matched terms, retrieval scores, a source map, limitations, and deterministic next steps.

Open `evidence_pack.json` when you need the machine-readable payload for tests, automation, or future bounded LLM review. The Markdown is rendered from the same payload that is written to `evidence_pack.json`; it does not re-run retrieval or introduce a second source of truth.

`evidence_pack.md` is different from the future `project_evidence_report.md`. The evidence pack is preparation: it shows selected lexical matches and source references. The future report will be a later artifact that separates evidence, missing evidence, possible contradictions, and human checks. PR #5 does not write that final report.

Important boundaries for `evidence_pack.md`:

- It is deterministic and does not use an LLM.
- It is not project approval or a go-live decision.
- Selected evidence is not automatically supporting evidence.
- Retrieval scores mean lexical relevance, not truth or completeness.
- Missing evidence detection and contradiction detection do not exist yet.
- Human review remains the final authority.

## Safety and authority boundaries

The workflow is intended to help a human review evidence. It must not become an approval engine.

Current and future outputs should preserve these boundaries:

- The tool should separate inventory, evidence indexing, retrieval, evidence-pack creation, and evidence review.
- Loading a file should not imply that the file supports any project claim.
- Creating a chunk should not imply that the chunk is relevant to the review question.
- Selecting a chunk should not imply that the chunk supports or contradicts the question.
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

Run the intake, indexing, and retrieval command with synthetic local sources:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "Is the project ready for go-live?" \
  --max-chunks 8 \
  --output-dir outputs/retrieval_run
```

Expected result:

```text
outputs/retrieval_run/source_inventory.json
outputs/retrieval_run/evidence_index.json
outputs/retrieval_run/review_question.json
outputs/retrieval_run/retrieval_trace.json
outputs/retrieval_run/evidence_pack.json
outputs/retrieval_run/evidence_pack.md
outputs/retrieval_run/project_evidence_trace.json
```

The trace records the question, output directory, supplied source path, source inventory counts, evidence chunk counts, selected chunk count, `--max-chunks`, `evidence_pack.md` path, package version, timestamp, and authority boundary. It also confirms that no LLM review, missing evidence detection, contradiction detection, final project evidence report, or approval decision happened.

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
