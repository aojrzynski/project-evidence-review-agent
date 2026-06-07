"""Deterministic lexical retrieval over bounded evidence chunks.

Retrieval is separate from both review-question recording and the evidence pack.
The retrieval trace explains why chunks were selected without copying full chunk
text, while the evidence pack carries the bounded selected text for later
Markdown reporting or bounded LLM review.

This module uses local, deterministic term matching instead of embeddings,
external search, vector databases, fuzzy libraries, or LLM calls. That is useful
before LLM review because a human can inspect the scoring inputs and because the
future prompt surface stays bounded. Retrieval is still not evidence review: a
high score means lexical relevance only, not truth, completeness, support,
contradiction, readiness, approval, compliance, certification, or go-live.

Source fingerprints are carried forward when available so humans can see which
file version supplied a selected chunk. The metadata is practical traceability,
not a full audit or authenticity guarantee.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_evidence_review_agent.review_question import normalize_text, unique_terms

RETRIEVAL_TRACE_FILE_NAME = "retrieval_trace.json"
EVIDENCE_PACK_FILE_NAME = "evidence_pack.json"
RETRIEVAL_STRATEGY = "deterministic_term_overlap_v1"
MAX_UNSELECTED_CANDIDATES = 5
TEXT_PREVIEW_CHARS = 240
SCORING_PARAMETERS = {
    "text_term_weight": 2,
    "heading_term_weight": 3,
    "path_term_weight": 1,
    "exact_phrase_weight": 5,
    "project_review_term_weight": 1,
}
PROJECT_REVIEW_TERMS = {
    "acceptance",
    "decision",
    "go-live",
    "implementation",
    "readiness",
    "release",
    "requirement",
    "requirements",
    "risk",
    "risks",
    "test",
    "testing",
}
LIMITATIONS = [
    (
        "Retrieval uses deterministic keyword overlap and may miss relevant "
        "chunks that use different wording."
    ),
    (
        "A selected chunk is lexically relevant to the question, not "
        "automatically supporting evidence."
    ),
    (
        "A high retrieval score does not establish truth, completeness, "
        "contradiction, readiness, approval, compliance, certification, or go-live."
    ),
]
BOUNDARY_NOTE = (
    "Retrieval is not evidence review. The selected chunks matched question terms "
    "and were included in a bounded evidence pack for later human or LLM-assisted "
    "review, but no claim was evaluated or approved."
)
AUTHORITY_BOUNDARY = (
    "The evidence pack is a bounded set of retrieved local chunks. It does not "
    "approve projects, certify readiness, replace governance, or make legal, "
    "compliance, privacy, security, certification, or go-live decisions. Human "
    "review remains the final authority."
)


@dataclass(frozen=True)
class RetrievalSummary:
    """Small summary of retrieval artifacts for the run trace."""

    retrieval_trace_path: Path
    evidence_pack_path: Path
    evidence_pack_payload: dict[str, Any]
    selected_chunk_count: int
    source_fingerprint_warning_count: int


def validate_max_chunks(value: int) -> int:
    """Validate the bounded evidence-pack chunk limit.

    The limit protects downstream context size. It does not change scoring; it
    only caps how many ranked chunks become selected evidence.
    """

    if value <= 0:
        raise ValueError("--max-chunks must be a positive integer")
    return value


def build_retrieval_outputs(
    question: str, evidence_index: dict[str, Any], max_chunks: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build retrieval trace and selected-evidence payloads.

    ``retrieval_trace.json`` explains why chunks were selected.
    ``evidence_pack.json`` contains the selected bounded excerpts. Neither file
    answers the review question or makes project claims.
    """

    validate_max_chunks(max_chunks)
    question_terms = unique_terms(question)
    normalized_question = normalize_text(question)
    chunks = list(evidence_index.get("chunks", []))
    candidates = [_score_chunk(chunk, question, question_terms) for chunk in chunks]
    # Ranking is fully deterministic: score first, then evidence ID for stable
    # tie-breaking. This makes evidence packs easier to diff and reproduce.
    ranked = sorted(
        candidates,
        key=lambda item: (-item["score"], str(item["chunk"].get("evidence_id", ""))),
    )
    # Only positively scoring chunks enter the bounded evidence pack. Selection
    # still means lexical relevance, not support or contradiction.
    selected = [candidate for candidate in ranked if candidate["score"] > 0][
        :max_chunks
    ]
    unselected = [candidate for candidate in ranked if candidate not in selected]
    fingerprint_warnings = _fingerprint_warnings(evidence_index, selected)

    trace = {
        "retrieval_trace_version": 1,
        "question": question,
        "normalized_question": normalized_question,
        "question_terms": question_terms,
        "retrieval_strategy": RETRIEVAL_STRATEGY,
        "scoring_parameters": {
            **SCORING_PARAMETERS,
            "project_review_terms": sorted(PROJECT_REVIEW_TERMS),
        },
        "max_chunks": max_chunks,
        "total_chunks_considered": len(chunks),
        "selected_chunk_count": len(selected),
        "selected_chunks": [_trace_chunk(candidate) for candidate in selected],
        "rejected_or_unselected_top_candidates": [
            _trace_chunk(candidate, include_reasons=False)
            for candidate in unselected[:MAX_UNSELECTED_CANDIDATES]
            if candidate["score"] > 0
        ],
        "source_fingerprint_notes": _source_fingerprint_notes(fingerprint_warnings),
        "limitations": LIMITATIONS,
        "boundary_note": BOUNDARY_NOTE,
    }
    evidence_pack = {
        "evidence_pack_version": 1,
        "question": question,
        "retrieval_strategy": RETRIEVAL_STRATEGY,
        "max_chunks": max_chunks,
        "selected_chunk_count": len(selected),
        "selected_chunks": [_pack_chunk(candidate) for candidate in selected],
        "source_map": _source_map(selected),
        "limitations": LIMITATIONS,
        "authority_boundary": AUTHORITY_BOUNDARY,
    }
    return trace, evidence_pack


def write_retrieval_outputs(
    question: str, evidence_index: dict[str, Any], max_chunks: int, output_dir: Path
) -> RetrievalSummary:
    """Write retrieval trace and evidence pack artifacts."""

    trace, evidence_pack = build_retrieval_outputs(
        question=question, evidence_index=evidence_index, max_chunks=max_chunks
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    retrieval_trace_path = output_dir / RETRIEVAL_TRACE_FILE_NAME
    evidence_pack_path = output_dir / EVIDENCE_PACK_FILE_NAME
    retrieval_trace_path.write_text(
        json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    evidence_pack_path.write_text(
        json.dumps(evidence_pack, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return RetrievalSummary(
        retrieval_trace_path=retrieval_trace_path,
        evidence_pack_path=evidence_pack_path,
        evidence_pack_payload=evidence_pack,
        selected_chunk_count=evidence_pack["selected_chunk_count"],
        source_fingerprint_warning_count=len(
            trace.get("source_fingerprint_notes", {}).get("warnings", [])
        ),
    )


def _score_chunk(
    chunk: dict[str, Any], question: str, question_terms: list[str]
) -> dict[str, Any]:
    """Score one chunk with explainable lexical features.

    The score measures overlap with the question and review-related words. It
    does not measure truth, sufficiency, or whether the chunk supports a claim.
    """

    text = str(chunk.get("text", ""))
    heading = str(chunk.get("heading") or "")
    path_text = f"{chunk.get('source_file_name', '')} {chunk.get('source_path', '')}"
    text_terms = set(unique_terms(text))
    heading_terms = set(unique_terms(heading))
    path_terms = set(unique_terms(path_text))
    normalized_text = normalize_text(text)
    normalized_question = normalize_text(question)

    matched_terms = sorted(
        term
        for term in question_terms
        if term in text_terms or term in heading_terms or term in path_terms
    )
    score = 0
    reasons: list[str] = []
    text_matches = sorted(term for term in question_terms if term in text_terms)
    heading_matches = sorted(term for term in question_terms if term in heading_terms)
    path_matches = sorted(term for term in question_terms if term in path_terms)
    review_matches = sorted(
        term for term in matched_terms if term in PROJECT_REVIEW_TERMS
    )

    if text_matches:
        # Each boost has a plain-language reason so retrieval_trace.json can be
        # inspected without hidden model or embedding behavior.
        score += len(text_matches) * SCORING_PARAMETERS["text_term_weight"]
        reasons.append(f"text terms matched: {', '.join(text_matches)}")
    if heading_matches:
        score += len(heading_matches) * SCORING_PARAMETERS["heading_term_weight"]
        reasons.append(f"heading terms matched: {', '.join(heading_matches)}")
    if path_matches:
        score += len(path_matches) * SCORING_PARAMETERS["path_term_weight"]
        reasons.append(f"source path/file terms matched: {', '.join(path_matches)}")
    if normalized_question and normalized_question in normalized_text:
        score += SCORING_PARAMETERS["exact_phrase_weight"]
        reasons.append("normalized question phrase matched chunk text")
    if review_matches:
        score += len(review_matches) * SCORING_PARAMETERS["project_review_term_weight"]
        reasons.append(f"project-review terms matched: {', '.join(review_matches)}")
    if not reasons:
        reasons.append("no question terms matched")

    return {
        "chunk": chunk,
        "score": score,
        "matched_terms": matched_terms,
        "scoring_reasons": reasons,
    }


def _trace_chunk(
    candidate: dict[str, Any], include_reasons: bool = True
) -> dict[str, Any]:
    """Render retrieval reasoning without copying full chunk text."""

    chunk = candidate["chunk"]
    payload = {
        "evidence_id": chunk.get("evidence_id"),
        "source_id": chunk.get("source_id"),
        "source_path": chunk.get("source_path"),
        "heading": chunk.get("heading"),
        "score": candidate["score"],
        "matched_terms": candidate["matched_terms"],
        **_references(chunk),
    }
    if include_reasons:
        payload["scoring_reasons"] = candidate["scoring_reasons"]
    return payload


def _pack_chunk(candidate: dict[str, Any]) -> dict[str, Any]:
    """Render one selected chunk for the bounded evidence pack."""

    chunk = candidate["chunk"]
    return {
        "evidence_id": chunk.get("evidence_id"),
        "source_id": chunk.get("source_id"),
        "source_path": chunk.get("source_path"),
        "source_file_name": chunk.get("source_file_name"),
        "source_type": chunk.get("source_type"),
        "heading": chunk.get("heading"),
        **_references(chunk),
        "text": chunk.get("text"),
        "text_preview": chunk.get("text_preview")
        or _preview(str(chunk.get("text", ""))),
        "matched_terms": candidate["matched_terms"],
        "retrieval_score": candidate["score"],
        "sha256": chunk.get("sha256"),
        "modified_time_ns": chunk.get("modified_time_ns"),
        "modified_time_utc": chunk.get("modified_time_utc"),
        "fingerprint_status": chunk.get("fingerprint_status"),
        "source_consistency_status": chunk.get("source_consistency_status"),
        **_optional_warning(chunk),
    }


def _source_map(selected: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Summarize only sources that contributed selected chunks."""

    sources: dict[str, dict[str, Any]] = {}
    for candidate in selected:
        chunk = candidate["chunk"]
        source_id = str(chunk.get("source_id"))
        sources[source_id] = {
            "source_id": source_id,
            "source_path": chunk.get("source_path"),
            "source_file_name": chunk.get("source_file_name"),
            "source_type": chunk.get("source_type"),
            "sha256": chunk.get("sha256"),
            "modified_time_ns": chunk.get("modified_time_ns"),
            "modified_time_utc": chunk.get("modified_time_utc"),
            "fingerprint_status": chunk.get("fingerprint_status"),
            "source_consistency_status": chunk.get("source_consistency_status"),
            **_optional_warning(chunk),
        }
    return dict(sorted(sources.items()))


def _references(chunk: dict[str, Any]) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for key in ("start_line", "end_line", "start_row", "end_row"):
        if key in chunk:
            refs[key] = chunk[key]
    return refs


def _optional_warning(chunk: dict[str, Any]) -> dict[str, Any]:
    if chunk.get("source_consistency_warning"):
        return {"source_consistency_warning": chunk["source_consistency_warning"]}
    return {}


def _fingerprint_warnings(
    evidence_index: dict[str, Any], selected: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Carry forward traceability warnings only for selected sources."""

    selected_ids = {candidate["chunk"].get("source_id") for candidate in selected}
    warnings = [
        warning
        for warning in evidence_index.get("summary", {}).get(
            "source_consistency_warnings", []
        )
        if warning.get("source_id") in selected_ids
    ]
    return warnings


def _source_fingerprint_notes(warnings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "note": (
            "Source fingerprints identify the local file version used when practical. "
            "They are not an authenticity or audit guarantee."
        ),
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def _preview(text: str) -> str:
    """Return a bounded text preview for artifact readability."""

    compact = text.strip()
    if len(compact) <= TEXT_PREVIEW_CHARS:
        return compact
    return f"{compact[:TEXT_PREVIEW_CHARS]}…"
