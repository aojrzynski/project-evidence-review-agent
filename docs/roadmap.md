# Roadmap

Project Evidence Review Agent is functionally complete for its v1 scope. Future work should preserve the core boundary: the workflow supports human review of bounded local evidence, but it does not approve projects or replace governance.

## Current v1 scope

The v1 workflow includes:

- local project pack intake;
- source inventory;
- supported file loading for Markdown, text, JSON, YAML/YML, and CSV;
- evidence indexing with bounded chunks;
- stable source IDs and evidence IDs;
- deterministic lexical retrieval;
- `evidence_pack.json` and `evidence_pack.md`;
- bounded LLM claim review when configured;
- citation and authority-boundary validation;
- missing evidence gap signals;
- contradiction candidates;
- final report assembly from validated artifacts;
- optional LangGraph orchestration;
- tests and CI.

## What is intentionally not included

The v1 workflow does not include:

- project approval;
- readiness decisions;
- go-live approval;
- compliance certification;
- legal, privacy, security, or governance verdicts;
- PDF, DOCX, or OCR support;
- web search;
- Google Drive or GitHub runtime connectors;
- embeddings or a vector database;
- automatic source-of-truth decisions;
- replacement of human review.

## Possible future improvements

Possible future work could include:

- PDF or DOCX support, only if excerpts remain bounded, cited, and safe;
- better retrieval ranking while keeping selection explainable;
- richer policy or review-question templates;
- comparison of multiple evidence packs;
- reviewer annotation workflow;
- optional export formats;
- stronger source integrity checks;
- GitHub or Drive connectors as explicit future local or controlled integrations;
- embeddings as a future explainability-conscious option, not a v1 assumption.

## Boundary to preserve in future work

Future features should keep the same authority boundary.

The workflow may help organize evidence, cite selected chunks, identify gaps, and flag possible tensions. It must not approve projects, decide readiness, approve go-live, certify compliance, or make legal, privacy, security, or governance verdicts.

Human review remains final.
