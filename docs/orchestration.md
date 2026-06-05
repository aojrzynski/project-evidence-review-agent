# Orchestration

Project Evidence Review Agent has two orchestration paths:

- **Standard Python orchestration** — the default path used by normal CLI runs.
- **Optional LangGraph orchestration** — an adapter requested with `--orchestrator langgraph` after installing the `graph` extra.

Both paths call the same shared workflow stages. Business logic remains in the normal modules for source inventory, evidence indexing, retrieval, evidence-pack Markdown, bounded LLM claim review, follow-up validation, report assembly, and trace writing.

## Why LangGraph is optional

LangGraph is useful for representing workflow nodes and branches, but it is not the product core. Normal deterministic runs and normal installs must not require graph dependencies. If a user requests LangGraph without installing the extra, the CLI fails cleanly and explains:

```text
LangGraph orchestration requires the optional graph dependencies. Install with: pip install -e '.[graph]'
```

No LangSmith tracing, LangGraph Cloud, external deployment service, web search, file upload, or extra LLM tool call is required.

## Branch behavior

The graph mirrors the standard workflow branches:

- no sources: write the scaffold trace only;
- `--no-llm`: write deterministic artifacts and skip LLM context, claim review, follow-up analysis, and final report;
- failed claim review: skip follow-up analysis and final report;
- failed follow-up validation: skip final report;
- successful full LLM mode: write claim review, missing evidence, contradiction log, final report, and trace.

These branches are orchestration decisions only. They do not change evidence semantics, validation rules, report semantics, or the authority boundary that human review remains final.

## Usage

Standard mode is explicit or default:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator standard \
  --output-dir outputs/standard_run
```

Install and use LangGraph mode:

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

`project_evidence_trace.json` records the chosen orchestrator and graph status fields so a reviewer can see whether standard or graph orchestration was used.
