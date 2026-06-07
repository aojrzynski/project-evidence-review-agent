# Architecture

Project Evidence Review Agent is a local workflow for preparing bounded evidence review material. It separates evidence collection, retrieval, LLM interpretation, validation, follow-up analysis, report assembly, and trace writing.

The separation matters because each stage has a different job. Loading a file is not the same as reviewing a claim. Retrieving a chunk is not the same as deciding whether the project is ready. Validation checks boundaries, but it does not prove truth.

## High-level workflow

```text
local project pack
-> source inventory
-> evidence index
-> review question
-> deterministic retrieval
-> evidence pack JSON/Markdown
-> LLM-safe review context
-> bounded LLM claim review
-> deterministic validation
-> missing evidence and contradiction follow-up
-> deterministic validation
-> project evidence report
-> trace
```

The full workflow writes `project_evidence_report.md` only after the LLM claim review and follow-up artifacts pass validation.

## Standard flow

The standard orchestrator is the default. It runs normal Python workflow stages in order:

1. Create the output directory.
2. Inventory supplied local sources.
3. Build the deterministic evidence index.
4. Record the review question.
5. Retrieve lexically relevant chunks.
6. Write `evidence_pack.json` and `evidence_pack.md`.
7. Either stop in `--no-llm` mode or continue into full mode.
8. Build `llm_safe_review_context.json`.
9. Run bounded LLM claim review.
10. Validate claim-review output.
11. Run follow-up analysis for missing evidence and contradiction candidates.
12. Validate follow-up output.
13. Assemble `project_evidence_report.md` from validated artifacts.
14. Write `project_evidence_trace.json`.

## Deterministic `--no-llm` flow

`--no-llm` mode stops after deterministic evidence-pack preparation.

It writes the local source and retrieval artifacts, including `evidence_pack.md`, then records skipped LLM and report stages in `project_evidence_trace.json`.

It does not write `llm_safe_review_context.json`, `claim_review.json`, `missing_evidence.json`, `contradiction_log.json`, or `project_evidence_report.md`.

Open `evidence_pack.md` first in this mode.

## Full LLM-enabled flow

Full mode is used when sources are supplied and `--no-llm` is not supplied.

The workflow still starts deterministically. It first builds the evidence pack, then creates `llm_safe_review_context.json`. The LLM receives the selected evidence only. The model output is not accepted just because it was produced. It must pass deterministic validation.

If claim-review validation fails, follow-up analysis and final report assembly are skipped. If follow-up validation fails, the final report is skipped.

Open `project_evidence_report.md` first only after a successful full run.

## Optional LangGraph orchestration

LangGraph orchestration is optional and requested with `--orchestrator langgraph` after installing the `graph` extra.

LangGraph changes orchestration only. Graph nodes call the same shared workflow stages used by the standard flow. LangGraph does not change evidence indexing, retrieval, prompts, validation, report assembly, or authority boundaries. It does not require LangSmith or LangGraph Cloud.

## Module responsibilities

| Module area | Responsibility |
| --- | --- |
| `cli.py` | Parses CLI arguments and selects the orchestrator. |
| `workflow.py` | Runs the standard stage sequence and shared workflow stage functions. |
| `langgraph_workflow.py` | Coordinates the same shared stages through optional LangGraph nodes. |
| `source_inventory.py` | Inventories local sources and records loaded or skipped files. |
| `evidence_index.py` | Builds bounded evidence chunks and stable evidence IDs. |
| `review_question.py` | Records the question and normalized retrieval terms. |
| `retrieval.py` | Runs deterministic lexical retrieval and writes the evidence pack. |
| `evidence_pack_markdown.py` | Renders `evidence_pack.md` from `evidence_pack.json`. |
| `llm_context.py` | Builds the bounded context that the LLM may see. |
| `llm_client.py` | Provides the optional OpenAI-backed review client. |
| `claim_review.py` | Runs and validates bounded claim review. |
| `follow_up_analysis.py` | Coordinates follow-up analysis for gaps and possible tensions. |
| `missing_evidence.py` | Validates missing evidence gap signals. |
| `contradictions.py` | Validates contradiction candidates and their evidence IDs. |
| `project_report.py` | Assembles the final Markdown report from validated artifacts. |
| `trace.py` | Writes concise run status and boundary metadata. |

## Why stages are separate

The workflow keeps stages separate so a reviewer can audit what happened:

- inventory shows what files were considered;
- evidence index shows the chunk boundary;
- retrieval trace shows why chunks were selected;
- LLM-safe context shows the model input boundary;
- validation records whether citations and authority language passed checks;
- report assembly uses already validated artifacts instead of making another LLM call.

This makes failure safer. A failed validation can stop downstream report writing instead of producing a polished but misleading report.

## Artifact chain

The artifacts form a chain:

1. `source_inventory.json` records local source handling.
2. `evidence_index.json` records chunks from loaded sources.
3. `review_question.json` records the question used for retrieval.
4. `retrieval_trace.json` explains selection.
5. `evidence_pack.json` stores selected chunks.
6. `evidence_pack.md` gives a readable deterministic view.
7. `llm_safe_review_context.json` records full-mode model input.
8. `claim_review.json` records validated review material or validation failure details.
9. `missing_evidence.json` and `contradiction_log.json` record validated follow-up material.
10. `project_evidence_report.md` assembles validated successful full-mode material.
11. `project_evidence_trace.json` records concise status for the run.

## Where validation happens

Validation happens after LLM-backed stages.

Claim-review validation checks required structure, allowed statuses, cited evidence IDs, and authority boundaries. Follow-up validation checks gap and contradiction structures, evidence ID references, claim ID references where needed, and authority boundaries.

Validation does not prove that the project material is true or complete. It checks whether model output stayed inside the allowed review format and citation boundary.

## Where human authority remains

Human authority remains outside the workflow.

The tool prepares review material. It cannot approve a project, decide readiness, approve go-live, certify compliance, or make legal, privacy, security, or governance verdicts.
