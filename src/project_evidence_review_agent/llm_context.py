"""Build the bounded context that is safe to send to an LLM.

The evidence pack is the context boundary for claim review. This module deliberately
copies only the review question, the selected evidence chunks, citation metadata,
and explicit review boundaries from ``evidence_pack.json``. It does not expose the
full source inventory, the full evidence index, unsupported files, or raw project
folders.

Saving ``llm_safe_review_context.json`` makes the LLM input auditable: a human can
inspect exactly which evidence IDs the model was allowed to use before reading any
claim review. The saved context is review material only. It does not approve a
project, certify readiness, replace governance, detect missing evidence as a
separate workflow stage, or detect contradictions as a separate workflow stage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LLM_SAFE_REVIEW_CONTEXT_FILE_NAME = "llm_safe_review_context.json"
LLM_SAFE_REVIEW_CONTEXT_VERSION = 1

REVIEW_INSTRUCTIONS = [
    "Use only the supplied evidence items and the review question.",
    "Do not answer from general knowledge or memory.",
    "Do not invent evidence IDs or sources.",
    "Every evidence_supported or partially_supported claim must cite evidence IDs.",
    "Use unclear_from_supplied_evidence when the supplied evidence is insufficient.",
    "Do not approve the project or certify readiness.",
    (
        "Do not make legal, compliance, privacy, security, certification, or "
        "go-live verdicts."
    ),
    "Human review remains the final authority.",
    "Return only JSON matching the requested claim review structure.",
]
FORBIDDEN_OUTPUTS = [
    "approved",
    "approval granted",
    "certified",
    "compliant",
    "compliance confirmed",
    "go-live approved",
    "ready for go-live",
    "safe to launch",
    "production ready",
    "project is ready",
    "final decision",
    "legal verdict",
    "security verdict",
    "privacy verdict",
]
AUTHORITY_BOUNDARY = (
    "The LLM may reason only over the selected evidence in this context. It must "
    "not approve projects, certify readiness, replace governance, or make legal, "
    "compliance, privacy, security, certification, or go-live decisions. Human "
    "review remains the final authority."
)
CONTEXT_LIMIT_NOTES = [
    "This context contains only selected chunks from evidence_pack.json.",
    (
        "Unsupported files, unselected chunks, full inventories, and raw "
        "project folders are excluded."
    ),
    "Missing evidence and contradiction detection are future workflow stages.",
]


def build_llm_safe_review_context(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    """Build a bounded LLM context from an existing evidence pack.

    Claim review is separate from retrieval because retrieval only chooses bounded
    lexical matches. This context preserves that boundary by exposing selected
    evidence IDs and source metadata, but no broader project material. The later
    validator, not the model, decides whether the model's structured output is safe
    enough to write as a successful claim review.
    """

    selected_chunks = list(evidence_pack.get("selected_chunks", []))
    evidence = [_context_evidence_item(chunk) for chunk in selected_chunks]
    allowed_evidence_ids = [str(item["evidence_id"]) for item in evidence]
    source_map = _bounded_source_map(evidence_pack.get("source_map", {}), evidence)

    return {
        "llm_safe_review_context_version": LLM_SAFE_REVIEW_CONTEXT_VERSION,
        "question": str(evidence_pack.get("question", "")),
        "selected_evidence_count": len(evidence),
        "allowed_evidence_ids": allowed_evidence_ids,
        "evidence": evidence,
        "source_map": source_map,
        "review_instructions": REVIEW_INSTRUCTIONS,
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "context_limit_notes": CONTEXT_LIMIT_NOTES,
    }


def write_llm_safe_review_context(
    evidence_pack: dict[str, Any], output_dir: Path
) -> Path:
    """Write ``llm_safe_review_context.json`` and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / LLM_SAFE_REVIEW_CONTEXT_FILE_NAME
    payload = build_llm_safe_review_context(evidence_pack)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")
    return path


def _context_evidence_item(chunk: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "evidence_id": str(chunk.get("evidence_id", "")),
        "source_id": chunk.get("source_id"),
        "source_file_name": chunk.get("source_file_name"),
        "source_path": chunk.get("source_path"),
        "source_type": chunk.get("source_type"),
        "heading": chunk.get("heading"),
        "text": chunk.get("text", ""),
        "text_preview": chunk.get("text_preview", ""),
        "sha256": chunk.get("sha256"),
        "modified_time_ns": chunk.get("modified_time_ns"),
        "modified_time_utc": chunk.get("modified_time_utc"),
        "fingerprint_status": chunk.get("fingerprint_status"),
        "source_consistency_status": chunk.get("source_consistency_status"),
    }
    for key in ("start_line", "end_line", "start_row", "end_row"):
        if key in chunk:
            item[key] = chunk[key]
    if chunk.get("source_consistency_warning"):
        item["source_consistency_warning"] = chunk["source_consistency_warning"]
    return item


def _bounded_source_map(
    source_map: dict[str, Any], evidence: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    allowed_source_ids = {str(item.get("source_id")) for item in evidence}
    bounded: dict[str, dict[str, Any]] = {}
    for source_id, metadata in source_map.items():
        if str(source_id) not in allowed_source_ids or not isinstance(metadata, dict):
            continue
        bounded[str(source_id)] = {
            "source_id": metadata.get("source_id"),
            "source_path": metadata.get("source_path"),
            "source_file_name": metadata.get("source_file_name"),
            "source_type": metadata.get("source_type"),
            "sha256": metadata.get("sha256"),
            "modified_time_ns": metadata.get("modified_time_ns"),
            "modified_time_utc": metadata.get("modified_time_utc"),
            "fingerprint_status": metadata.get("fingerprint_status"),
            "source_consistency_status": metadata.get("source_consistency_status"),
        }
    return dict(sorted(bounded.items()))
