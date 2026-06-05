# Artifacts

This page lists the local artifacts written by the current workflow and what each is for.

- `source_inventory.json` — records supported and skipped local sources, source IDs, parser metadata, and lightweight fingerprints.
- `evidence_index.json` — records deterministic bounded chunks with stable `EV-0001`-style evidence IDs and source references.
- `review_question.json` — records the supplied review question and normalized retrieval terms.
- `retrieval_trace.json` — explains deterministic lexical retrieval, selected chunks, matched terms, scores, and limitations.
- `evidence_pack.json` — contains the bounded selected evidence chunks and source map used by later stages.
- `evidence_pack.md` — readable view of selected evidence excerpts; this is the first artifact to open in `--no-llm` mode.
- `llm_safe_review_context.json` — records exactly what is supplied to the LLM in full mode.
- `claim_review.json` — validated bounded claim review with claim IDs, statuses, cited evidence IDs, caveats, and human checks.
- `missing_evidence.json` — validated gap signals from the supplied evidence pack; these are not proof of absence.
- `contradiction_log.json` — validated possible contradiction candidates; these are not final findings.
- `project_evidence_report.md` — assembled human-readable report for a successful full run; this is the first artifact to open after full LLM-enabled validation succeeds.
- `project_evidence_trace.json` — run trace with artifact statuses, counts, report status, orchestrator metadata (`orchestrator`, `langgraph_requested`, `langgraph_available`, `graph_orchestration_status`, and optional `graph_node_statuses`), and the explicit no-approval/no-go-live boundary.
