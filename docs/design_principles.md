# Design principles

These principles describe how Project Evidence Review Agent should behave as it grows.

## Local-first by default

The workflow reads local files supplied by the user. It does not perform web search or connect to external document stores at runtime.

This keeps the source boundary visible: the review can only be about the supplied material.

## Evidence grounding before interpretation

The tool organizes evidence before asking for interpretation.

It inventories files, chunks supported content, records evidence IDs, retrieves likely relevant chunks, and writes the evidence pack before any LLM-backed review.

## Bounded evidence chunks

Evidence is split into small chunks. Bounded chunks make citations more useful than whole-file references because a human can inspect the specific excerpt used for a claim.

## Stable source IDs and evidence IDs

Sources receive `SRC-0001`-style IDs. Evidence chunks receive `EV-0001`-style IDs.

Stable IDs help connect retrieval, LLM review, validation, follow-up analysis, and the final report.

## Retrieval is not review

Retrieval selects chunks that appear lexically relevant to the review question. A high retrieval score does not mean a claim is true. A selected chunk may be useful, unclear, incomplete, or in tension with another chunk.

## The LLM is useful but not authoritative

In full mode, the LLM is central to claim review and follow-up analysis. It helps draft structured review material from selected evidence.

The LLM is not allowed to approve a project, decide readiness, invent evidence, or make final verdicts.

## Deterministic validation after LLM output

LLM output must pass deterministic validation before later successful artifacts are written.

Validation checks structure, citation IDs, required fields, allowed statuses, and authority boundaries. It does not prove truth, completeness, or compliance.

## Missing evidence is a gap signal

A missing evidence entry means the supplied selected evidence did not show something that appears important to check. It is not proof that the evidence does not exist somewhere else.

## Contradiction candidates are possible tensions

A contradiction candidate means two cited pieces of evidence may point in different directions. It is not a final contradiction finding. A human needs to inspect the cited chunks.

## The final report is assembled from validated artifacts

`project_evidence_report.md` is assembled after successful validation. It does not make another LLM call and does not add a new decision stage.

## Human review remains final

The workflow supports human review. It does not replace it.

No artifact approves a project, certifies readiness, approves go-live, or makes legal, privacy, security, compliance, or governance verdicts.

## Optional LangGraph orchestration does not own business logic

LangGraph can coordinate stages when installed and requested. The business logic remains in normal shared modules so standard and LangGraph runs keep the same meaning.
