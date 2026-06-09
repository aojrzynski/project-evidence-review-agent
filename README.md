# Project Evidence Review Agent

Given a project claim or review question, what evidence do we actually have, what is missing, what may contradict it, and what should a human check next?

Project Evidence Review Agent helps answer that practical question from local project files.

Projects leave evidence scattered across notes, requirements, decision logs, risks, testing notes, and release summaries. Someone may ask whether testing is complete, whether a requirement is supported, or whether a project is ready to discuss for go-live. This tool gathers the supplied local material, breaks it into small cited chunks, selects evidence that appears relevant to the review question, and prepares review material.

In full mode, an LLM helps interpret only the selected evidence. The tool still does not make the final decision.

> [!NOTE]
> **Part of the Data Agent Suite.**
> 
> This repo is one of 10 local-first data/AI agents built around practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> The full ordered list of agents is included near the bottom of this README.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)

## The workplace problem

Project evidence is often spread across many files.

A decision may be in one place. A risk may be in another. Testing notes may be in a third file. Release notes may say something different from the plan. People may ask confident questions before the evidence has been organized.

A human reviewer needs to know:

- what is supported by the supplied evidence;
- what is unclear;
- what evidence appears to be missing;
- what may point in different directions;
- what should be checked next by a person.

The risk is either over-trusting scattered notes or asking an LLM to make a confident answer without clear evidence boundaries. This workflow is designed to keep the evidence boundary visible.

## What this project does

The workflow:

1. inventories local sources;
2. loads supported files;
3. chunks them into bounded evidence units;
4. records stable source IDs and evidence IDs;
5. retrieves likely relevant chunks for the review question;
6. writes `evidence_pack.json` and `evidence_pack.md`;
7. builds `llm_safe_review_context.json` in full mode;
8. runs bounded LLM claim review in full mode;
9. validates citations and authority boundaries;
10. writes `claim_review.json` after claim review;
11. writes `missing_evidence.json` and `contradiction_log.json` after successful claim-review validation;
12. writes `project_evidence_report.md` after successful full validation;
13. writes `project_evidence_trace.json` with concise run status.

The workflow is review support only. It does not approve projects, decide readiness, approve go-live, certify compliance, or replace human review.

## What to open first

- Full LLM-enabled run: open `project_evidence_report.md` first.
- Deterministic `--no-llm` run: open `evidence_pack.md` first.
- To audit the model input: open `llm_safe_review_context.json`.
- To inspect retrieval: open `retrieval_trace.json`.
- To inspect run status: open `project_evidence_trace.json`.

## Why evidence grounding matters

The tool should not answer from memory. It should show which selected evidence chunks it used.

Claims in the LLM-backed review need evidence IDs. Selected evidence is bounded. A retrieval score means lexical relevance to the question, not truth. Validation checks structure, citations, and authority boundaries. Validation does not prove real-world truth.

Human review still matters.

## Why not just ask an LLM?

A normal LLM prompt can sound confident without showing what project material it used.

This workflow first builds a local evidence pack. In full mode, the LLM receives only selected evidence from that pack. The LLM is asked for structured review material, not a decision. The output must pass deterministic validation before later artifacts are treated as successful.

Failed validation is safer than a misleading successful answer.

## Quick start

Create a virtual environment and install development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run a deterministic evidence-pack review without an LLM:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/deterministic_run
```

Open this first:

```bash
cat outputs/deterministic_run/evidence_pack.md
```

Install LLM dependencies for a full run:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="your-api-key"
```

Run the full LLM-enabled workflow:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --output-dir outputs/full_run
```

Open this first after a successful full run:

```bash
cat outputs/full_run/project_evidence_report.md
```

Install optional LangGraph orchestration support:

```bash
python -m pip install -e ".[dev,graph]"
```

Run the same deterministic workflow through LangGraph orchestration:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator langgraph \
  --output-dir outputs/langgraph_run
```

You can also run the CLI through Python:

```bash
python -m project_evidence_review_agent \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/python_module_run
```

## Example commands

Show help:

```bash
project-evidence-review --help
```

Show version:

```bash
project-evidence-review --version
```

Run deterministic mode with the standard orchestrator:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "Which evidence supports release readiness discussion?" \
  --max-chunks 10 \
  --no-llm \
  --orchestrator standard \
  --output-dir outputs/standard_run
```

Run full mode with an explicit model:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "Which evidence supports release readiness discussion?" \
  --max-chunks 10 \
  --llm-model gpt-4.1-mini \
  --output-dir outputs/full_model_run
```

See [docs/example_commands.md](docs/example_commands.md) for more copy-paste examples.

## Output artifacts

| Artifact | Purpose |
| --- | --- |
| `source_inventory.json` | Lists loaded and skipped local sources. It is not evidence review. |
| `evidence_index.json` | Lists bounded evidence chunks with stable evidence IDs. It is not evidence review. |
| `review_question.json` | Records the supplied question and normalized retrieval terms. |
| `retrieval_trace.json` | Explains lexical selection and scores. It does not prove support. |
| `evidence_pack.json` | Stores selected evidence chunks for later stages. |
| `evidence_pack.md` | Human-readable selected evidence. Open first in `--no-llm` mode. |
| `llm_safe_review_context.json` | Shows exactly what the LLM could see in full mode. |
| `claim_review.json` | Validated LLM-backed claim review material, not a decision. |
| `missing_evidence.json` | Gap signals from supplied evidence, not proof of absence. |
| `contradiction_log.json` | Possible tension candidates, not final findings. |
| `project_evidence_report.md` | Assembled report after successful full validation. Open first in full mode. |
| `project_evidence_trace.json` | Concise run status and artifact status. |

See [docs/artifacts.md](docs/artifacts.md) for detailed artifact guidance.

## Optional dependencies

The base install supports deterministic local evidence-pack mode.

- `dev`: installs test and lint tools such as `pytest` and `ruff`.
- `llm`: installs the OpenAI client used for full LLM-backed review.
- `graph`: installs LangGraph for optional graph orchestration.
- `dev,llm,graph`: installs development tools plus both optional runtime extras.

Examples:

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[llm]"
python -m pip install -e ".[graph]"
python -m pip install -e ".[dev,llm,graph]"
```

If `--sources` is supplied and `--no-llm` is not supplied, the CLI attempts full LLM review. If the optional LLM dependency or `OPENAI_API_KEY` is missing, the command fails cleanly and explains how to rerun with `--no-llm`.

## Orchestration

Standard orchestration is the default:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator standard \
  --output-dir outputs/standard_run
```

LangGraph orchestration is optional:

```bash
python -m pip install -e ".[graph]"
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator langgraph \
  --output-dir outputs/langgraph_run
```

LangGraph coordinates the same workflow stages. It does not change evidence, review, validation, report content, or authority boundaries. It does not require LangSmith, LangGraph Cloud, or other cloud services.

See [docs/orchestration.md](docs/orchestration.md) for details.

## Safety and authority boundaries

Output is review material, not project approval.

The tool cannot decide that a project is ready. It cannot approve go-live. It cannot certify compliance, security, privacy, legal status, or governance. It cannot replace a human reviewer.

Human review remains final.

See [docs/safety_boundaries.md](docs/safety_boundaries.md) for more detail.

## Project structure

```text
src/project_evidence_review_agent/  Python package and CLI workflow stages
docs/                               Plain-English user and design docs
examples/project_pack/              Small local example project pack
tests/                              Unit and CLI tests
```

## Run tests

```bash
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

The tests do not call a real LLM and do not require `OPENAI_API_KEY`.

## Limitations and non-goals

- Local files only.
- Supported formats only: Markdown, text, JSON, YAML/YML, and CSV.
- No PDF, DOCX, or OCR support.
- No web search.
- No Google Drive or GitHub runtime connectors.
- No embeddings or vector database in v1.
- Retrieval is lexical.
- The LLM may make mistakes.
- Validation is structural and citation validation, not truth validation.
- No final approval, readiness decision, or go-live decision.

## Further reading

- [Architecture](docs/architecture.md)
- [Design principles](docs/design_principles.md)
- [Artifacts](docs/artifacts.md)
- [Demo workflow](docs/demo_workflow.md)
- [Example commands](docs/example_commands.md)
- [Safety boundaries](docs/safety_boundaries.md)
- [LLM review](docs/llm_review.md)
- [Orchestration](docs/orchestration.md)
- [Roadmap](docs/roadmap.md)

---

> [!NOTE]
> **Data Agent Suite**  
> This repo is part of the **Data Agent Suite**: 10 local-first data/AI agents focused on practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)
>
> 1. [Data Quality Triage Agent](https://github.com/aojrzynski/data-quality-triage-agent)
> 2. [Data Reconciliation Agent](https://github.com/aojrzynski/data-reconciliation-agent)
> 3. [Data Dictionary Agent](https://github.com/aojrzynski/data-dictionary-agent)
> 4. [Data Contract Review Agent](https://github.com/aojrzynski/data-contract-review-agent)
> 5. [Sensitive Field Review Agent](https://github.com/aojrzynski/sensitive-field-review-agent)
> 6. [Data Test Suggestion Agent](https://github.com/aojrzynski/data-test-suggestion-agent)
> 7. [Dataset Onboarding Reviewer Workflow](https://github.com/aojrzynski/dataset-onboarding-reviewer-workflow)
> 8. [Data Quality Investigation Workflow](https://github.com/aojrzynski/data-quality-investigation-workflow)
> 9. **Project Evidence Review Agent**
> 10. [Data Migration Readiness Review Agent](https://github.com/aojrzynski/data-migration-readiness-review-agent)
