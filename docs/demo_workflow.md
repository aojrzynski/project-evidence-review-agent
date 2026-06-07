# Demo workflow

This demo uses the small local files in `examples/project_pack`. It shows both deterministic evidence-pack mode and optional full LLM mode.

The demo output is review material. It is not project approval.

## 1. Create and activate a virtual environment

Bash:

```bash
python -m venv .venv
source .venv/bin/activate
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2. Install development dependencies

```bash
python -m pip install -e ".[dev]"
```

## 3. Run tests

```bash
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

The tests use fake or deterministic paths. They do not call a real LLM and do not require `OPENAI_API_KEY`.

## 4. Run a deterministic `--no-llm` demo

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/demo_no_llm
```

This writes the evidence inventory, evidence index, retrieval trace, evidence pack JSON, evidence pack Markdown, and run trace.

## 5. Open `evidence_pack.md`

```bash
cat outputs/demo_no_llm/evidence_pack.md
```

Open this first in deterministic mode. It shows selected cited excerpts and retrieval notes. It does not contain LLM claim review.

## 6. Inspect `project_evidence_trace.json`

```bash
cat outputs/demo_no_llm/project_evidence_trace.json
```

Use the trace to confirm that LLM-backed stages were skipped because `--no-llm` was supplied.

## 7. Optional full LLM run

Install the LLM extra:

```bash
python -m pip install -e ".[dev,llm]"
```

Set an API key.

Bash:

```bash
export OPENAI_API_KEY="your-api-key"
```

PowerShell:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
```

Run full mode:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --output-dir outputs/demo_full
```

If the LLM dependency or API key is missing, rerun with `--no-llm` for deterministic evidence-pack mode.

## 8. Open `project_evidence_report.md`

```bash
cat outputs/demo_full/project_evidence_report.md
```

Open this first after a successful full run. The report is assembled from validated artifacts. It does not make another LLM call.

To audit what the LLM could see:

```bash
cat outputs/demo_full/llm_safe_review_context.json
```

## 9. Optional LangGraph deterministic run

Install the graph extra:

```bash
python -m pip install -e ".[dev,graph]"
```

Run deterministic mode through LangGraph orchestration:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator langgraph \
  --output-dir outputs/demo_langgraph_no_llm
```

LangGraph changes orchestration only. It does not change evidence, review, validation, or authority boundaries.

## 10. Clean outputs

Bash:

```bash
rm -rf outputs/demo_no_llm outputs/demo_full outputs/demo_langgraph_no_llm
```

PowerShell:

```powershell
Remove-Item -Recurse -Force outputs/demo_no_llm, outputs/demo_full, outputs/demo_langgraph_no_llm
```

## 11. What not to conclude

Do not conclude that the project is approved.

Do not conclude that testing is complete in the real world just because selected evidence appears supportive.

Do not conclude that missing evidence signals prove absence.

Do not conclude that contradiction candidates are final contradictions.

A human reviewer remains responsible for final judgment.
