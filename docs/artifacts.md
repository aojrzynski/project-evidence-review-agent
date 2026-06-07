# Artifacts

Project Evidence Review Agent writes local artifacts to the selected output directory. Each artifact has a different job. Some are deterministic. Some are LLM-generated but validation-bounded. Some are assembled from earlier artifacts.

No artifact is project approval. No artifact decides readiness or go-live.

## What to open first

- Successful full LLM-enabled run: open `project_evidence_report.md` first.
- Deterministic `--no-llm` run: open `evidence_pack.md` first.
- To audit the model input: open `llm_safe_review_context.json`.
- To inspect retrieval: open `retrieval_trace.json`.
- To inspect run status: open `project_evidence_trace.json`.

## How artifacts relate to each other

```text
source_inventory.json
-> evidence_index.json
-> review_question.json
-> retrieval_trace.json
-> evidence_pack.json
-> evidence_pack.md
-> llm_safe_review_context.json
-> claim_review.json
-> missing_evidence.json and contradiction_log.json
-> project_evidence_report.md
-> project_evidence_trace.json
```

`project_evidence_trace.json` is written as a concise status record. It is not a duplicate of every artifact.

## Common exclusions

The artifacts do not include:

- approval decisions;
- readiness decisions;
- go-live decisions;
- compliance certification;
- security, privacy, legal, or governance verdicts;
- proof that the supplied evidence is complete;
- proof that selected evidence is true;
- web search results;
- unsupported file contents.

## `source_inventory.json`

### Purpose

Records which local files were found, which were loaded, and which were skipped.

### When written

Written when `--sources` is supplied and the source path can be inspected.

### Open it for

Use it to check whether the expected files were seen and whether any files were skipped because of format, path handling, or read limitations.

### What it contains

It contains source IDs, paths, supported or skipped status, parser metadata, lightweight fingerprints, and skip reasons where applicable.

### What it excludes

It does not contain claim review, support judgments, missing evidence analysis, contradiction candidates, or approval decisions.

### Artifact type

Deterministic.

### Authority boundary

This is not evidence review. It only records source handling.

## `evidence_index.json`

### Purpose

Records bounded evidence chunks created from loaded supported files.

### When written

Written after source inventory when supported sources are available.

### Open it for

Use it to inspect all chunks before retrieval narrows them for the review question.

### What it contains

It contains stable `EV-0001`-style evidence IDs, links back to `SRC-0001`-style source IDs, excerpt text, and line or row references where practical.

### What it excludes

It does not decide which chunks support a claim. It does not rank chunks for the question. It does not review the project.

### Artifact type

Deterministic.

### Authority boundary

This is not evidence review. It is a structured index of loaded local evidence chunks.

## `review_question.json`

### Purpose

Records the supplied human review question and normalized terms used for deterministic retrieval.

### When written

Written before retrieval when sources are supplied.

### Open it for

Use it to confirm that the run used the intended question.

### What it contains

It contains the original question and retrieval terms derived from it.

### What it excludes

It does not contain an answer, a recommendation, or a decision.

### Artifact type

Deterministic.

### Authority boundary

The question frames review preparation. It does not authorize the tool to decide readiness or approval.

## `retrieval_trace.json`

### Purpose

Explains how deterministic lexical retrieval selected chunks for the evidence pack.

### When written

Written after `review_question.json` and `evidence_index.json`.

### Open it for

Use it to inspect selected chunks, matched terms, retrieval scores, and why chunks were included.

### What it contains

It contains selected evidence IDs, matched terms, scores, and retrieval metadata.

### What it excludes

It does not prove support. It does not prove truth. It does not make claim judgments. A retrieval score means lexical relevance, not correctness.

### Artifact type

Deterministic.

### Authority boundary

This explains selection, not support.

## `evidence_pack.json`

### Purpose

Stores the bounded selected evidence that later stages may use.

### When written

Written after deterministic retrieval.

### Open it for

Use it to audit the exact selected evidence in structured JSON form.

### What it contains

It contains the review question, selected evidence chunks, source map, evidence IDs, source IDs, references, scores, and retrieval context.

### What it excludes

It does not contain LLM interpretation, claim review, missing evidence analysis, contradiction candidates, or approval decisions.

### Artifact type

Deterministic.

### Authority boundary

This is selected evidence, not a decision.

## `evidence_pack.md`

### Purpose

Provides a human-readable view of `evidence_pack.json`.

### When written

Written after `evidence_pack.json`.

### Open it for

Open this first in deterministic `--no-llm` mode. Use it to read selected excerpts and retrieval notes without reading JSON.

### What it contains

It contains the review question, selected evidence excerpts, evidence IDs, source references, matched terms, scores, limitations, and review-preparation boundaries.

### What it excludes

It does not contain LLM claim review. It does not say whether the project is ready. It does not approve go-live.

### Artifact type

Deterministic Markdown rendered from deterministic JSON.

### Authority boundary

This is evidence preparation material for a human reviewer.

## `llm_safe_review_context.json`

### Purpose

Shows exactly what the LLM could see in full mode.

### When written

Written after `evidence_pack.json` when `--no-llm` is not supplied.

### Open it for

Use it to audit the model input boundary before reading `claim_review.json` or `project_evidence_report.md`.

### What it contains

It contains the review question, selected evidence chunks, allowed evidence IDs, source metadata needed for citations, and instructions with authority boundaries.

### What it excludes

It excludes unselected files, unselected chunks, web content, external tools, file uploads, and any instruction to make final approval decisions.

### Artifact type

Deterministic context for an LLM-backed stage.

### Authority boundary

This constrains what the LLM may use. It does not make the LLM authoritative.

## `claim_review.json`

### Purpose

Records structured claim review material produced by the LLM and checked by deterministic validation.

### When written

Written in full mode after the LLM claim-review call. If validation fails, the artifact records failure details instead of accepted review material.

### Open it for

Use it to inspect claim statuses, cited evidence IDs, caveats, validator messages, and human checks.

### What it contains

It may contain claim IDs, statuses such as supported or partially supported, cited evidence IDs, short rationales, caveats, and human follow-up checks.

### What it excludes

It does not contain final approval, readiness certification, compliance certification, legal verdicts, privacy verdicts, security verdicts, governance verdicts, or go-live approval.

### Artifact type

LLM-generated and validation-bounded.

### Authority boundary

This is validated review material, not a decision.

## `missing_evidence.json`

### Purpose

Records gap signals found during follow-up analysis.

### When written

Written only after successful claim-review validation and successful follow-up parsing and validation.

### Open it for

Use it to see what evidence a human may need to look for next.

### What it contains

It contains missing evidence entries, related claim references where applicable, reasons the gap matters, and human follow-up suggestions.

### What it excludes

It does not prove that evidence is absent. It does not search outside the supplied selected evidence. It does not decide that the project failed.

### Artifact type

LLM-generated and validation-bounded.

### Authority boundary

Gap signals are prompts for human follow-up, not findings of absence.

## `contradiction_log.json`

### Purpose

Records possible tension candidates between cited evidence chunks.

### When written

Written only after successful claim-review validation and successful follow-up parsing and validation.

### Open it for

Use it to inspect possible contradictions that need human review.

### What it contains

It contains candidate entries with evidence IDs on both sides, a short explanation of the possible tension, and human follow-up suggestions.

### What it excludes

It does not contain final contradiction findings. It does not prove one source is right and another is wrong.

### Artifact type

LLM-generated and validation-bounded.

### Authority boundary

Contradiction candidates are possible tensions, not final findings.

## `project_evidence_report.md`

### Purpose

Provides a human-readable report after a successful full run.

### When written

Written only after claim review, missing evidence, and contradiction candidate artifacts pass validation.

### Open it for

Open this first after a successful full LLM-enabled run.

### What it contains

It contains an assembled view of the question, selected evidence, supported or unclear points, gap signals, possible tensions, human checks, limitations, and authority boundaries.

### What it excludes

It does not contain a new LLM answer. It does not approve the project. It does not decide readiness or go-live. It does not certify compliance, privacy, security, legal status, or governance.

### Artifact type

Assembled from validated artifacts. The report stage does not make another LLM call.

### Authority boundary

This is review material for a human reviewer.

## `project_evidence_trace.json`

### Purpose

Records concise run status and artifact status.

### When written

Written during the run and updated with final statuses.

### Open it for

Use it to check whether stages ran, skipped, failed, or passed validation. Use it to see orchestrator metadata.

### What it contains

It contains package version, question, source path, artifact-written flags, counts, LLM status, validation status, follow-up status, report status, orchestrator fields, and the no-approval boundary.

### What it excludes

It is not a duplicate of every artifact. It does not contain all selected excerpts or all model output.

### Artifact type

Deterministic run trace.

### Authority boundary

Trace status is operational status, not project approval.
