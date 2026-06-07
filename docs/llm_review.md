# LLM review

Full mode uses an LLM when it is configured and `--no-llm` is not supplied. The LLM is central to full claim review, but it is not authoritative.

The model receives bounded selected evidence. It is asked to produce structured review material. It is not asked to approve the project or make a final decision.

## Deterministic mode skips LLM review

When `--no-llm` is supplied, the workflow stops after deterministic evidence-pack artifacts and trace status.

It does not write `llm_safe_review_context.json`, `claim_review.json`, `missing_evidence.json`, `contradiction_log.json`, or `project_evidence_report.md`.

Open `evidence_pack.md` first in this mode.

## Full mode is LLM-backed when configured

When sources are supplied and `--no-llm` is not supplied, the CLI attempts full LLM review.

The `llm` extra and `OPENAI_API_KEY` must be configured for the default OpenAI client. If they are missing, the command fails cleanly and explains how to rerun with `--no-llm`.

## What `llm_safe_review_context.json` contains

`llm_safe_review_context.json` records exactly what is available to the model:

- the review question;
- selected evidence chunks;
- allowed `EV-0001`-style evidence IDs;
- source metadata needed for citations;
- review instructions;
- authority boundaries.

Saving the context lets a human audit the model input before reading the claim review.

## Why context is bounded

The context is bounded so the model reviews only selected evidence. It should not answer from memory, infer from unselected project material, or invent missing sources.

Bounded context also makes validation possible because supported claims must cite evidence IDs that exist in the selected evidence pack.

## Why supported claims need evidence IDs

Every claim marked `evidence_supported` or `partially_supported` must cite existing evidence IDs.

A source ID alone is not enough. The review is tied to selected chunks, not whole files.

## What validation rejects

Claim-review validation rejects output that:

- is malformed;
- misses required fields;
- uses unsupported claim statuses;
- invents evidence IDs;
- omits citations for supported or partially supported claims;
- cites source IDs in place of evidence IDs;
- uses approval or verdict language;
- crosses the authority boundary.

Follow-up validation rejects output that invents claim IDs or evidence IDs, omits required contradiction-side citations, gives unsupported structures, or uses verdict language.

## What happens on failed validation

A failed validation is treated as a safer stop.

The workflow records failure details and skips downstream successful report assembly. It does not turn unsafe model output into a polished final report.

## Follow-up analysis

After `claim_review.json` passes validation, the workflow runs bounded follow-up analysis using the saved LLM-safe context and the validated claim review.

This writes:

- `missing_evidence.json` for evidence gap signals;
- `contradiction_log.json` for possible tension candidates.

Missing evidence is not proof of absence. Contradiction candidates are not final findings. Both are prompts for human review.

## Final report assembly does not call the LLM again

`project_evidence_report.md` is assembled from validated artifacts. The report stage does not make another LLM call and does not add a new decision stage.

## No tools, web search, uploads, or streaming

The workflow does not give the LLM web search tools, runtime file upload tools, function calling tools, or streaming tool calls. The model input is the saved bounded context.

## Human authority

LLM-backed artifacts are review material. They do not approve readiness, compliance, certification, security, privacy, legal status, governance, or go-live.

Human review remains the final authority.
