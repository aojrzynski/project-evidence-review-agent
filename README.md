# Project Evidence Review Agent

Project Evidence Review Agent is a bounded review workflow for helping a human inspect supplied local project evidence. It inventories local material, chunks supported files, retrieves a bounded evidence pack for a question, and can run an LLM claim review only over that selected evidence.

It does not approve projects, certify readiness, replace governance, or make legal, compliance, privacy, security, or go-live decisions. Human review remains the final authority.

## Plain-English purpose

Project work often leaves evidence spread across plans, notes, decisions, risks, test notes, and release materials. When someone asks whether a claim is supported, the first problem is not to generate a confident answer. The first problem is to identify the local material that was supplied, show what the tool could load, show what it skipped, prepare small source references, and select a bounded set of chunks that match the review question.

The current workflow now has two layers:

1. **Deterministic evidence-pack building** inspects supplied local sources, inventories them, chunks them, retrieves relevant passages, and writes bounded JSON evidence packs plus readable Markdown views.
2. **Bounded LLM claim review** asks an LLM to draft structured claim review material from only the selected evidence pack, then validates the returned citations and authority boundary before treating the output as successful.

The LLM is central to the full claim review workflow, but it is not authoritative. The evidence pack controls the input boundary. The validator controls the output boundary.

## Current PR #6 capability

PR #6 provides bounded LLM claim review while keeping deterministic evidence-pack mode available:

- Defines the `project_evidence_review_agent` Python package.
- Adds the `project-evidence-review` CLI command.
- Accepts `--question`, `--output-dir`, `--sources`, `--max-chunks`, `--no-llm`, `--llm-model`, and `--version`.
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
- Writes `evidence_pack.json` with the bounded selected chunks.
- Writes `evidence_pack.md` as a human-readable view rendered from the same `evidence_pack.json` payload.
- By default, when `--sources` is supplied, attempts bounded LLM claim review.
- Writes `llm_safe_review_context.json` before an LLM call in LLM mode.
- Writes `claim_review.json` with validated claims, or a failed validation artifact when model output is unsafe.
- Continues writing `project_evidence_trace.json` with deterministic and LLM status fields.
- Records that missing evidence detection, contradiction detection, final project evidence report, and approval decisions are still not performed.

## Supported source file types

Supported extensions are:

- `.md`
- `.txt`
- `.json`
- `.yaml`
- `.yml`
- `.csv`

Unsupported files are not treated as review failures. They are skipped with a reason in the source inventory and do not create evidence chunks. PDF, DOCX, OCR, web pages, remote services, external connectors, embeddings, vector databases, and LangGraph are not implemented in this PR.

## Optional LLM dependency

OpenAI support is optional so deterministic mode and tests do not require a real LLM client or `OPENAI_API_KEY`.

Install development tools only:

```bash
python -m pip install -e ".[dev]"
```

Install development tools plus optional LLM support:

```bash
python -m pip install -e ".[dev,llm]"
```

LLM mode uses the OpenAI Responses API through a small wrapper. It does not use web search, file uploads, code interpreter, MCP, tools, function calling, or streaming.

If `--sources` is supplied and `--no-llm` is not supplied, the CLI attempts LLM claim review. If OpenAI is not installed or `OPENAI_API_KEY` is not configured, the command fails cleanly and explains how to rerun with `--no-llm`.

## Deterministic mode with `--no-llm`

Use `--no-llm` when you want evidence-pack-only behavior or when no LLM client is configured:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/deterministic_run
```

Expected deterministic artifacts:

```text
outputs/deterministic_run/source_inventory.json
outputs/deterministic_run/evidence_index.json
outputs/deterministic_run/review_question.json
outputs/deterministic_run/retrieval_trace.json
outputs/deterministic_run/evidence_pack.json
outputs/deterministic_run/evidence_pack.md
outputs/deterministic_run/project_evidence_trace.json
```

`claim_review.json` is not written in `--no-llm` mode. The trace records `llm_review_status = skipped_no_llm`.

## LLM claim review mode

Use default LLM-enabled mode when the optional dependency and API key are configured:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --llm-model gpt-4.1-mini \
  --output-dir outputs/claim_review_run
```

Expected LLM-enabled artifacts:

```text
outputs/claim_review_run/source_inventory.json
outputs/claim_review_run/evidence_index.json
outputs/claim_review_run/review_question.json
outputs/claim_review_run/retrieval_trace.json
outputs/claim_review_run/evidence_pack.json
outputs/claim_review_run/evidence_pack.md
outputs/claim_review_run/llm_safe_review_context.json
outputs/claim_review_run/claim_review.json
outputs/claim_review_run/project_evidence_trace.json
```

## What `llm_safe_review_context.json` contains

`llm_safe_review_context.json` is saved so a human can inspect exactly what would be sent to the LLM. It is built only from:

- The review question.
- Selected chunks from `evidence_pack.json`.
- Allowed evidence IDs.
- Source map and citation metadata needed for traceability.
- Explicit review instructions, forbidden outputs, authority boundaries, and context limit notes.

It does not include skipped unsupported files, the full source inventory, the full evidence index, unselected chunks, raw project folders, or anything outside the selected evidence pack.

## What `claim_review.json` contains

`claim_review.json` records structured claim review material and validation status:

- `claim_review_version`
- `question`
- `llm_review_status`
- `llm_model`
- `validation_status`
- `claims`
- `unsupported_or_unclear_points`
- `review_caveats`
- `recommended_human_checks`
- `rejected_items`
- `validator_messages`
- `allowed_evidence_ids`
- `authority_boundary`

Each claim must include `claim_id`, `claim_text`, `status`, `evidence_ids`, `explanation`, and `caveats`.

Allowed claim statuses are:

- `evidence_supported`
- `partially_supported`
- `not_supported_by_supplied_evidence`
- `unclear_from_supplied_evidence`

## Citation validation

The validator checks model output before it can be treated as a successful claim review:

- The response must be valid JSON with required top-level fields.
- `claims` must be a list.
- Every claim must contain required fields.
- Claim statuses must use the allowed status values.
- `evidence_supported` and `partially_supported` claims must cite at least one evidence ID.
- Every cited evidence ID must exist in `allowed_evidence_ids`.
- A claim may not cite a `SRC-0001` source ID alone instead of an `EV-0001` evidence ID.
- A claim may not cite an invented evidence ID.
- LLM-generated review content may not use forbidden approval or verdict language.

Uncited, invented, malformed, or authority-overreaching model output is rejected. A failed validation writes `claim_review.json` with `validation_status = failed`, validator messages, and rejected item summaries. It is safer to preserve a failed validation artifact than to present unsafe output as a successful review.

## What the trace records

`project_evidence_trace.json` records the deterministic artifact statuses plus LLM fields such as:

- `no_llm`
- `llm_model`
- `llm_safe_review_context_written`
- `llm_safe_review_context_path`
- `claim_review_written`
- `claim_review_path`
- `llm_review_status`
- `claim_review_validation_status`
- `claim_count`
- `rejected_claim_count`
- `validator_message_count`

The trace still confirms no missing evidence detection, no contradiction detection, no final project evidence report, and no approval or go-live decision.

## Safety and authority boundaries

The workflow is intended to help a human review evidence. It must not become an approval engine.

Current and future outputs should preserve these boundaries:

- The tool separates inventory, evidence indexing, retrieval, bounded LLM context construction, claim review, and validation.
- Loading a file does not imply that the file supports any project claim.
- Creating a chunk does not imply that the chunk is relevant to the review question.
- Selecting a chunk does not imply that the chunk supports or contradicts the question.
- The LLM must reason only over bounded supplied evidence.
- Claims that indicate support must cite evidence IDs.
- Missing evidence and possible contradictions are future stages and should be shown as review prompts, not final verdicts.
- Claim review is review material, not project approval.
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

Run deterministic mode first if you do not have an LLM configured:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "Is the project ready for go-live?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/retrieval_run
```

You can still run without `--sources` to write only the trace:

```bash
project-evidence-review --question "What evidence supports this claim?" --output-dir outputs/scaffold_run
```

You can also run the package module directly:

```bash
python -m project_evidence_review_agent \
  --sources examples/project_pack \
  --question "What evidence supports this claim?" \
  --no-llm \
  --output-dir outputs/example
```

## Run tests and checks

```bash
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

These checks do not call a real LLM and do not require `OPENAI_API_KEY`.

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
