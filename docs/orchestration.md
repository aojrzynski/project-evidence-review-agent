# Orchestration

Project Evidence Review Agent has two orchestration paths:

- standard Python orchestration, which is the default;
- optional LangGraph orchestration, requested with `--orchestrator langgraph` after installing the `graph` extra.

Both paths call the same shared workflow stages. Orchestration does not change review meaning.

## Standard orchestrator

Standard orchestration is used unless another orchestrator is requested.

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator standard \
  --output-dir outputs/standard_run
```

The `--orchestrator standard` flag is optional because standard is the default.

## Optional LangGraph orchestrator

Install the graph extra:

```bash
python -m pip install -e ".[graph]"
```

Run with LangGraph:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator langgraph \
  --output-dir outputs/langgraph_run
```

If the graph extra is not installed, the CLI fails cleanly and explains how to install it.

## What graph nodes do

LangGraph nodes coordinate existing shared workflow stages. They do not own the business logic.

The normal modules still handle source inventory, evidence indexing, review-question recording, retrieval, evidence-pack Markdown, LLM context creation, claim review, follow-up validation, report assembly, and trace writing.

## Business logic remains in normal modules

Keeping business logic outside the graph means standard and LangGraph runs keep the same evidence meaning.

LangGraph does not add evidence sources, change retrieval scoring, change validation rules, change report semantics, add approval decisions, or add LLM authority.

## Branch behavior

Both orchestrators preserve the same branch behavior:

- no sources: write the scaffold trace only;
- `--no-llm`: write deterministic artifacts and skip LLM context, claim review, follow-up analysis, and final report;
- failed claim review: skip follow-up analysis and final report;
- failed follow-up validation: skip final report;
- full success: write claim review, missing evidence, contradiction log, final report, and trace.

These branches are workflow status decisions. They do not change the authority boundary.

## Trace orchestrator metadata

`project_evidence_trace.json` records orchestrator status fields so a reviewer can see how the run was coordinated.

Trace metadata may include:

- `orchestrator`;
- `langgraph_requested`;
- `langgraph_available`;
- `graph_orchestration_status`;
- `graph_node_statuses` when applicable.

The trace is concise status. It is not a duplicate of every artifact.

## No LangSmith or cloud service required

LangGraph orchestration does not require LangSmith, LangGraph Cloud, external deployment, web search, or cloud tracing.

The workflow remains local-first except for the optional LLM provider call in full mode.

## Orchestration does not change review meaning

Changing the orchestrator does not change evidence, review, validation, report content, or authority boundaries.

The output remains review material, not approval.
