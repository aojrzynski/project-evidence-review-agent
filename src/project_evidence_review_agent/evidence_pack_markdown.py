"""Render deterministic Markdown from an evidence pack JSON payload.

This module exists after ``evidence_pack.json`` because the JSON artifact is the
machine-readable contract for later stages, while ``evidence_pack.md`` is a
human-readable view of the same bounded evidence. The Markdown helps a reviewer
inspect selected chunks before any LLM-assisted review is introduced.

The renderer deliberately does not call an LLM, re-run retrieval, infer project
readiness, decide whether a claim is supported, detect missing evidence, detect
contradictions, or write the final project evidence report. A selected chunk is
only a deterministic lexical retrieval result. It is not automatically supporting
evidence, and a retrieval score means lexical relevance rather than truth or
completeness. Preserving evidence IDs, source IDs, source references, matched
terms, scores, and bounded excerpts keeps this preparation artifact useful for
human review and for later citation-bound validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

EVIDENCE_PACK_MARKDOWN_FILE_NAME = "evidence_pack.md"
MAX_EXCERPT_CHARS = 4_000


def write_evidence_pack_markdown(
    evidence_pack: dict[str, Any], output_dir: Path
) -> Path:
    """Write ``evidence_pack.md`` rendered from the supplied pack payload.

    The caller passes the same in-memory payload that was written to
    ``evidence_pack.json``. This keeps Markdown consistent with JSON and avoids
    a second retrieval pass with a separate source of truth.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / EVIDENCE_PACK_MARKDOWN_FILE_NAME
    markdown_path.write_text(render_evidence_pack_markdown(evidence_pack), "utf-8")
    return markdown_path


def render_evidence_pack_markdown(evidence_pack: dict[str, Any]) -> str:
    """Return deterministic Markdown for a bounded evidence pack payload.

    The renderer reads the supplied JSON payload and never reruns retrieval, so
    ``evidence_pack.md`` is a view of the selected evidence rather than a second
    selection process. In ``--no-llm`` mode this is often the first artifact a
    reviewer should open.
    """

    selected_chunks = list(evidence_pack.get("selected_chunks", []))
    source_map = evidence_pack.get("source_map", {}) or {}
    limitations = list(evidence_pack.get("limitations", []))
    warning_count = _source_fingerprint_warning_count(evidence_pack)

    retrieval_strategy = _inline_code(
        evidence_pack.get("retrieval_strategy", "unknown")
    )
    max_chunks = _plain_value(evidence_pack.get("max_chunks", "not recorded"))
    selected_count = _plain_value(
        evidence_pack.get("selected_chunk_count", len(selected_chunks))
    )

    lines: list[str] = [
        "# Evidence Pack",
        "",
        "## Review question",
        "",
        _paragraph(str(evidence_pack.get("question", ""))),
        "",
        "## How this pack was built",
        "",
        "* Local sources were inventoried from the supplied path.",
        "* Supported files were indexed into bounded evidence chunks.",
        (
            "* Deterministic lexical retrieval selected chunks that matched "
            "review question terms."
        ),
        "* The selected chunks were bounded by the configured maximum chunk count.",
        "* No LLM was used to create this artifact.",
        "",
        "## Important boundary",
        "",
        "* This evidence pack is review preparation, not project approval.",
        "* A selected chunk is not automatically supporting evidence.",
        "* Retrieval score means lexical relevance, not truth or completeness.",
        "* Human review remains the final authority.",
        (
            "* This artifact does not approve readiness, compliance, "
            "certification, or go-live decisions."
        ),
        "",
        "## Retrieval summary",
        "",
        f"* Retrieval strategy: `{retrieval_strategy}`",
        f"* Max chunks: {max_chunks}",
        f"* Selected chunk count: {selected_count}",
        f"* Source fingerprint warning count: {warning_count}",
        (
            "* Limitations: deterministic lexical retrieval may miss relevant "
            "evidence that uses different wording, and scores do not evaluate "
            "claims."
        ),
        "",
        "## Selected evidence",
        "",
    ]

    if selected_chunks:
        for chunk in selected_chunks:
            lines.extend(_render_chunk(chunk))
    else:
        lines.extend(
            [
                "No chunks were selected by deterministic lexical retrieval.",
                "",
            ]
        )

    lines.extend(
        [
            "## Source map",
            "",
            "| Source ID | File name | Path | Type | Fingerprint |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if source_map:
        for source_id in sorted(source_map):
            source = source_map[source_id] or {}
            fingerprint = _compact_fingerprint(source)
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(source.get("source_id", source_id)),
                        _table_cell(source.get("source_file_name", "")),
                        _table_cell(source.get("source_path", "")),
                        _table_cell(source.get("source_type", "")),
                        _table_cell(fingerprint),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| _None_ | _None_ | _None_ | _None_ | _None_ |")

    lines.extend(["", "## Limitations", ""])
    if limitations:
        lines.extend(f"* {_plain_value(limitation)}" for limitation in limitations)
    lines.extend(
        [
            "* Deterministic retrieval uses local lexical matching only.",
            "* This artifact does not identify missing evidence or contradictions yet.",
            (
                "* Source fingerprints are lightweight local metadata, not an "
                "authenticity or audit guarantee."
            ),
            "",
            "## Next steps",
            "",
            (
                "* A human reviewer should inspect the selected evidence and "
                "the source files."
            ),
            (
                "* Later workflow stages will add bounded LLM claim review "
                "over supplied evidence."
            ),
            "* This artifact does not identify missing evidence or contradictions yet.",
            (
                "* This artifact is not the final project evidence report and "
                "does not make a project decision."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _render_chunk(chunk: dict[str, Any]) -> list[str]:
    """Render one selected evidence chunk with citation metadata."""

    evidence_id = str(chunk.get("evidence_id", "Evidence chunk"))
    lines = [
        f"### {_heading_text(evidence_id)}",
        "",
        f"* Source file: {_plain_value(chunk.get('source_file_name', ''))}",
        f"* Source path: {_plain_value(chunk.get('source_path', ''))}",
        f"* Source ID: `{_inline_code(chunk.get('source_id', ''))}`",
        f"* Source type: {_plain_value(chunk.get('source_type', ''))}",
    ]
    reference = _reference_text(chunk)
    if reference:
        lines.append(f"* Reference: {reference}")
    if chunk.get("heading"):
        lines.append(f"* Heading: {_plain_value(chunk.get('heading'))}")
    matched_terms = chunk.get("matched_terms", []) or []
    lines.extend(
        [
            f"* Matched terms: {_list_value(matched_terms)}",
            f"* Retrieval score: {_plain_value(chunk.get('retrieval_score', 0))}",
            f"* Source fingerprint: {_plain_value(_compact_fingerprint(chunk))}",
        ]
    )
    if chunk.get("source_consistency_warning"):
        lines.append(
            "* Source fingerprint warning: "
            f"{_plain_value(chunk['source_consistency_warning'])}"
        )
    lines.extend(
        [
            "",
            "Excerpt:",
            "",
            "```text",
            _bounded_excerpt(str(chunk.get("text") or chunk.get("text_preview") or "")),
            "```",
            "",
        ]
    )
    return lines


def _reference_text(payload: dict[str, Any]) -> str:
    if "start_line" in payload and "end_line" in payload:
        return f"lines {payload['start_line']}-{payload['end_line']}"
    if "start_row" in payload and "end_row" in payload:
        return f"rows {payload['start_row']}-{payload['end_row']}"
    return ""


def _compact_fingerprint(payload: dict[str, Any]) -> str:
    sha256 = payload.get("sha256")
    status = payload.get("fingerprint_status") or payload.get(
        "source_consistency_status"
    )
    modified = payload.get("modified_time_utc")
    parts: list[str] = []
    if sha256:
        parts.append(f"sha256={str(sha256)[:12]}…")
    if status:
        parts.append(f"status={status}")
    if modified:
        parts.append(f"modified={modified}")
    return "; ".join(parts) if parts else "not recorded"


def _source_fingerprint_warning_count(evidence_pack: dict[str, Any]) -> int:
    sources = evidence_pack.get("source_map", {}) or {}
    return sum(
        1
        for source in sources.values()
        if isinstance(source, dict) and source.get("source_consistency_warning")
    )


def _bounded_excerpt(text: str) -> str:
    """Keep Markdown excerpts bounded even when selected chunks are long."""

    if len(text) <= MAX_EXCERPT_CHARS:
        return text
    return (
        f"{text[:MAX_EXCERPT_CHARS]}\n[excerpt truncated for bounded Markdown output]"
    )


def _list_value(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "none"
    return ", ".join(f"`{_inline_code(value)}`" for value in values)


def _paragraph(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _heading_text(value: object) -> str:
    return str(value).replace("#", "＃").strip() or "Evidence chunk"


def _table_cell(value: object) -> str:
    text = _plain_value(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def _plain_value(value: object) -> str:
    if value is None or value == "":
        return "not recorded"
    return str(value)


def _inline_code(value: object) -> str:
    return str(value).replace("`", "\\`")
