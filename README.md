# Project Evidence Review Agent

Project Evidence Review Agent is a bounded review workflow for helping a human inspect supplied local project evidence. It inventories local material, chunks supported files, retrieves a bounded evidence pack for a question, and can run an LLM claim review only over that selected evidence.

It does not approve projects, certify readiness, replace governance, or make legal, compliance, privacy, security, or go-live decisions. Human review remains the final authority.

## Plain-English purpose

Project work often leaves evidence spread across plans, notes, decisions, risks, test notes, and release materials. When someone asks whether a claim is supported, the first problem is not to generate a confident answer. The first problem is to identify the local material that was supplied, show what the tool could load, show what it skipped, prepare small source references, and select a bounded set of chunks that match the review question.

The current workflow now has four product layers, plus an optional orchestration adapter:

1. **Deterministic evidence-pack building** inspects supplied local sources, inventories them, chunks them, retrieves relevant passages, and writes bounded JSON evidence packs plus readable Markdown views.
2. **Bounded LLM claim review** asks an LLM to draft structured claim review material from only the selected evidence pack, then validates the returned citations and authority boundary before treating the output as successful.
3. **Validation-bounded follow-up analysis** uses the same bounded context plus validated claim review to identify missing evidence gaps and contradiction candidates for human review.
4. **Human-readable report assembly** writes `project_evidence_report.md` from validated artifacts after a successful full run, without making another LLM call or adding a new decision stage.
5. **Optional orchestration selection** runs those same stages through either the default standard Python orchestrator or, when installed and requested, a LangGraph graph that only coordinates existing stages.

The LLM is central to the full claim review workflow, but it is not authoritative. The evidence pack controls the input boundary. The validator controls the output boundary. The final report is an assembly of validated artifacts for a human reviewer.

## Current PR #9 capability

PR #9 adds optional LangGraph workflow orchestration while keeping the standard Python orchestrator as the default and preserving the PR #8 artifact-producing workflow:

- Defines the `project_evidence_review_agent` Python package.
- Adds the `project-evidence-review` CLI command.
- Accepts `--question`, `--output-dir`, `--sources`, `--max-chunks`, `--no-llm`, `--llm-model`, `--orchestrator`, and `--version`.
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
- After successful claim review, writes `missing_evidence.json` with validation-bounded evidence gap signals.
- After successful claim review, writes `contradiction_log.json` with validation-bounded contradiction candidates.
- Requires contradiction candidates to cite valid evidence IDs on both sides.
- Allows missing evidence entries to describe gaps where evidence was not found.
- Writes `project_evidence_report.md` after claim review, missing evidence, and contradiction validation all pass.
- Makes `project_evidence_report.md` the first artifact to open after a successful full run.
- Keeps `evidence_pack.md` as the first artifact to open in `--no-llm` mode.
- Assembles validated artifacts without making another LLM call.
- Continues writing `project_evidence_trace.json` with deterministic, LLM, follow-up, report, and orchestrator status fields.
- Records that approval and go-live decisions are still not performed.

## Orchestration

The default orchestrator is standard Python:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator standard \
  --output-dir outputs/standard_run
```

LangGraph orchestration is optional and requires the `graph` extra:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator langgraph \
  --output-dir outputs/langgraph_run
```

LangGraph changes only orchestration: graph nodes call the same shared workflow stage functions used by the standard path. It does not add evidence sources, change retrieval, change LLM prompts or validation semantics, add LLM calls, approve projects, require LangSmith, or require LangGraph Cloud. The trace records `orchestrator`, `langgraph_requested`, `langgraph_available`, `graph_orchestration_status`, and bounded node statuses when the graph path is used.

## Supported source file types

Supported extensions are:

- `.md`
- `.txt`
- `.json`
- `.yaml`
- `.yml`
- `.csv`

Unsupported files are not treated as review failures. They are skipped with a reason in the source inventory and do not create evidence chunks. PDF, DOCX, OCR, web pages, remote services, external connectors, embeddings, and vector databases are not implemented in this PR. LangGraph is supported only as optional local orchestration, not as a cloud service or source of review semantics.

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

Install optional LangGraph orchestration support:

```bash
python -m pip install -e ".[graph]"
```

Install development tools with both optional groups when desired:

```bash
python -m pip install -e ".[dev,llm,graph]"
```

LLM mode uses the OpenAI Responses API through a small wrapper. It does not use web search, file uploads, code interpreter, MCP, tools, function calling, or streaming.

If `--sources` is supplied and `--no-llm` is not supplied, the CLI attempts LLM claim review and then follow-up analysis for missing evidence and contradiction candidates after claim review succeeds. If OpenAI is not installed or `OPENAI_API_KEY` is not configured, the command fails cleanly and explains how to rerun with `--no-llm`.

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
outputs/claim_review_run/missing_evidence.json
outputs/claim_review_run/contradiction_log.json
outputs/claim_review_run/project_evidence_report.md
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


In deterministic mode, the command does not write:

- `llm_safe_review_context.json`
- `claim_review.json`
- `missing_evidence.json`
- `contradiction_log.json`
- `project_evidence_report.md`

After a successful full LLM-enabled run, open `project_evidence_report.md` first. It assembles the validated claim review, missing evidence signals, contradiction candidates, selected evidence map, source map, limitations, and recommended human checks. In `--no-llm` mode, open `evidence_pack.md` first because no claim review or report is written.

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

## What `project_evidence_report.md` contains

`project_evidence_report.md` is the human-readable report for a successful full run. It does not make another LLM call. It does not reinterpret evidence beyond the validated artifacts already written. It separates:

- **Claim review**: bounded claims with statuses, cited evidence IDs, explanations, caveats, and recommended human checks.
- **Missing evidence signals**: gap signals from the supplied evidence pack. These are not proof that evidence does not exist elsewhere.
- **Contradiction candidates**: possible tensions between cited evidence chunks. These are not final findings and require human review.

The report also includes a selected evidence map, source map, limitations, an artifact list, and an authority boundary. It is not approval, readiness certification, compliance certification, or go-live approval. Human review remains the final authority.

## What the trace records

`project_evidence_trace.json` records the deterministic artifact statuses plus LLM, follow-up, report, and orchestration fields such as:

- `orchestrator`
- `langgraph_requested`
- `langgraph_available`
- `graph_orchestration_status`
- `graph_node_statuses`
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
- `missing_evidence_written`
- `missing_evidence_status`
- `missing_evidence_validation_status`
- `missing_evidence_count`
- `rejected_missing_evidence_count`
- `contradiction_log_written`
- `contradiction_detection_status`
- `contradiction_validation_status`
- `contradiction_candidate_count`
- `rejected_contradiction_count`
- `project_evidence_report_written`
- `project_evidence_report_path`
- `project_evidence_report_status`
- `report_input_artifacts`
- `report_claim_count`
- `report_missing_evidence_count`
- `report_contradiction_candidate_count`
- `report_human_check_count`
- `final_report_is_not_approval`

The trace confirms no approval or go-live decision.

## Safety and authority boundaries

The workflow is intended to help a human review evidence. It must not become an approval engine.

Current and future outputs should preserve these boundaries:

- The tool separates inventory, evidence indexing, retrieval, bounded LLM context construction, claim review, and validation.
- Loading a file does not imply that the file supports any project claim.
- Creating a chunk does not imply that the chunk is relevant to the review question.
- Selecting a chunk does not imply that the chunk supports or contradicts the question.
- The LLM must reason only over bounded supplied evidence.
- Claims that indicate support must cite evidence IDs.
- Missing evidence and possible contradictions are follow-up artifacts and are review prompts, not final verdicts.
- The final report is assembled review material, not project approval.
- The report cannot certify readiness, compliance, privacy, security, legal status, or go-live.
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
9. PR #9 optional LangGraph orchestration
10. PR #10 docs, examples, comments, and release polish


## What `missing_evidence.json` and `contradiction_log.json` contain

`missing_evidence.json` records LLM-assisted, validation-bounded gap signals. A gap may mean the selected evidence does not appear to contain a specific artifact, the evidence is unclear, the area was not searched in the bounded context, or a human follow-up is needed. Missing evidence is not proof that something does not exist.

Each missing evidence entry uses a deterministic `ME-0001`-style ID, an allowed gap type, related claim and evidence IDs when available, a practical human check, and a low/medium/high confidence value. Entries may have no related evidence IDs when the point is that evidence was not found.

`contradiction_log.json` records contradiction candidates, not final findings. Every candidate uses a deterministic `CON-0001`-style ID and must cite valid `EV-0001`-style evidence IDs on both side A and side B. Source IDs alone are rejected. Invented evidence IDs are rejected.

Both artifacts are produced only after `claim_review.json` passes validation. If follow-up validation fails, failed artifacts preserve validator messages and rejected item summaries instead of pretending the analysis succeeded. The final Markdown report is `project_evidence_report.md` when the full LLM-enabled workflow succeeds. It assembles these validated artifacts and stays non-authoritative.
