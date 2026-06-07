# Example commands

These commands are copy-paste examples for common local runs.

## Help and version

```bash
project-evidence-review --help
```

Shows CLI options.

```bash
project-evidence-review --version
```

Shows the installed package version.

## Deterministic `--no-llm` run

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/no_llm_run
```

Builds local evidence artifacts and stops before LLM review.

## Deterministic run with explicit standard orchestrator

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --orchestrator standard \
  --output-dir outputs/standard_run
```

Runs the default standard Python orchestration explicitly.

## Deterministic run with LangGraph orchestrator

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

Runs the same deterministic stages through optional LangGraph orchestration.

## Full LLM run

```bash
python -m pip install -e ".[llm]"
export OPENAI_API_KEY="your-api-key"
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --output-dir outputs/full_run
```

Runs bounded LLM claim review and follow-up analysis after building the evidence pack.

PowerShell API key form:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
```

## Full LLM run with explicit model

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "Which evidence supports release readiness discussion?" \
  --max-chunks 10 \
  --llm-model gpt-4.1-mini \
  --output-dir outputs/full_explicit_model
```

Uses the named model for bounded claim review and follow-up analysis.

## Python module version

```bash
python -m project_evidence_review_agent --version
```

Shows the package version through `python -m`.

```bash
python -m project_evidence_review_agent \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/python_module_run
```

Runs the same CLI through `python -m`.

## Custom output directory

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What risks need human follow-up?" \
  --max-chunks 6 \
  --no-llm \
  --output-dir outputs/risk_follow_up_review
```

Writes artifacts to a named output directory for that review question.

## Single source file run

```bash
project-evidence-review \
  --sources examples/project_pack/testing_notes.txt \
  --question "What does the testing note say still needs review?" \
  --max-chunks 5 \
  --no-llm \
  --output-dir outputs/single_file_run
```

Inventories and retrieves from one supported local file.

## Missing LLM fallback

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --output-dir outputs/full_without_key
```

If the LLM extra or `OPENAI_API_KEY` is not configured, this fails cleanly and tells you to rerun with `--no-llm`.

Fallback command:

```bash
project-evidence-review \
  --sources examples/project_pack \
  --question "What evidence shows testing is complete?" \
  --max-chunks 8 \
  --no-llm \
  --output-dir outputs/no_llm_fallback
```

Builds the deterministic evidence pack without LLM review.

## Install extras

```bash
python -m pip install -e ".[dev]"
```

Installs development test and lint tools.

```bash
python -m pip install -e ".[llm]"
```

Installs the optional LLM client dependency.

```bash
python -m pip install -e ".[graph]"
```

Installs optional LangGraph orchestration support.

```bash
python -m pip install -e ".[dev,llm,graph]"
```

Installs development tools and both optional runtime extras.
