"""Create a deterministic evidence index from loaded local sources.

Source inventory answers, "what local files were found, loaded, or skipped?"
Evidence indexing is the next preparation step: it turns loaded supported files
into small, bounded chunks that later retrieval and review stages can cite.

This module deliberately does not retrieve evidence for a question, decide
whether a chunk supports or contradicts a claim, build an evidence pack, call an
LLM, write a review report, or approve readiness, compliance, certification, or
go-live. A chunk existing only means that a bounded piece of a loaded local file
is available for later inspection.

Stable ``EV-0001``-style identifiers are assigned in deterministic source and
chunk order. Later stages can use those IDs for citation and validation without
depending on changing model output. Chunks are bounded so future prompts and
human review surfaces do not accidentally receive whole documents when a smaller
source reference is enough.
"""

from __future__ import annotations

import csv
import importlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EVIDENCE_INDEX_FILE_NAME = "evidence_index.json"
MAX_CHUNK_CHARS = 2000
MAX_CHUNK_LINES = 35
MAX_CSV_DATA_ROWS = 25
TEXT_PREVIEW_CHARS = 240
YAML_MODULE = (
    importlib.import_module("yaml")
    if importlib.util.find_spec("yaml") is not None
    else None
)


@dataclass(frozen=True)
class EvidenceIndexSummary:
    """Small summary of evidence index results for the run trace."""

    path: Path
    chunk_count: int
    status: str


def build_evidence_index(
    inventory: dict[str, Any], sources_path: Path
) -> dict[str, Any]:
    """Build an evidence index from loaded source inventory records.

    The inventory remains the authority on which files were loaded or skipped.
    This function only chunks records marked ``loaded`` and only for supported
    source types. Unsupported or skipped files never become evidence chunks.
    """

    resolved_sources_path = sources_path.expanduser()
    loaded_records = sorted(
        (
            record
            for record in inventory.get("records", [])
            if record.get("status") == "loaded"
        ),
        key=lambda record: (
            str(record.get("path", "")),
            str(record.get("source_id", "")),
        ),
    )

    chunks_without_ids: list[dict[str, Any]] = []
    for record in loaded_records:
        source_file = _source_file_path(resolved_sources_path, record)
        chunks_without_ids.extend(_chunk_loaded_source(record, source_file))

    chunks = [
        {"evidence_id": f"EV-{index:04d}", **chunk}
        for index, chunk in enumerate(chunks_without_ids, start=1)
    ]

    return {
        "evidence_index_version": 1,
        "source_inventory_version": inventory.get("inventory_version"),
        "source_path": inventory.get("source_path", str(sources_path)),
        "chunking_parameters": {
            "max_chunk_chars": MAX_CHUNK_CHARS,
            "max_chunk_lines": MAX_CHUNK_LINES,
            "max_csv_data_rows": MAX_CSV_DATA_ROWS,
            "text_preview_chars": TEXT_PREVIEW_CHARS,
        },
        "chunks": chunks,
        "summary": {
            "loaded_sources_considered": len(loaded_records),
            "evidence_chunks": len(chunks),
            "skipped_sources_excluded": inventory.get("summary", {}).get(
                "skipped_sources", 0
            ),
        },
        "boundary_note": (
            "Evidence indexing creates bounded local source chunks for later citation. "
            "It is not retrieval, evidence review, LLM review, or a project decision."
        ),
    }


def write_evidence_index(
    inventory: dict[str, Any], sources_path: Path, output_dir: Path
) -> EvidenceIndexSummary:
    """Write ``evidence_index.json`` and return counts for the trace."""

    evidence_index = build_evidence_index(
        inventory=inventory, sources_path=sources_path
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_index_path = output_dir / EVIDENCE_INDEX_FILE_NAME
    evidence_index_path.write_text(
        json.dumps(evidence_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    chunk_count = evidence_index["summary"]["evidence_chunks"]
    return EvidenceIndexSummary(
        path=evidence_index_path,
        chunk_count=chunk_count,
        status="completed" if chunk_count > 0 else "completed_no_chunks",
    )


def _source_file_path(root: Path, record: dict[str, Any]) -> Path:
    if root.is_file():
        return root
    return root / str(record["path"])


def _chunk_loaded_source(record: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    source_type = str(record.get("source_type", ""))
    if source_type == "markdown":
        return _chunk_markdown(record, path)
    if source_type == "text":
        return _chunk_text(record, path)
    if source_type == "json":
        return _chunk_json(record, path)
    if source_type == "yaml":
        return _chunk_yaml(record, path)
    if source_type == "csv":
        return _chunk_csv(record, path)
    return []


def _chunk_markdown(record: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: list[tuple[str | None, int, list[str]]] = []
    current_heading: str | None = None
    current_start = 1
    current_lines: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        heading = _markdown_heading(line)
        if heading is not None and current_lines:
            sections.append((current_heading, current_start, current_lines))
            current_lines = []
            current_start = line_number
        if heading is not None:
            current_heading = heading
        current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_start, current_lines))

    chunks: list[dict[str, Any]] = []
    for heading, start_line, section_lines in sections:
        chunks.extend(
            _chunk_line_window(
                record=record,
                lines=section_lines,
                start_line=start_line,
                heading=heading,
                strategy="markdown_heading_and_bounded_lines",
            )
        )
    return _with_chunk_indexes(chunks)


def _chunk_text(record: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return _with_chunk_indexes(
        _chunk_line_window(
            record=record,
            lines=lines,
            start_line=1,
            heading=None,
            strategy="bounded_text_lines",
        )
    )


def _chunk_json(record: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(parsed, dict):
        chunks = []
        for key in sorted(parsed, key=str):
            text = json.dumps({key: parsed[key]}, indent=2, sort_keys=True)
            chunks.extend(
                _chunk_serialized_text(
                    record=record,
                    text=text,
                    heading=str(key),
                    strategy="json_top_level_key",
                )
            )
        return _with_chunk_indexes(chunks)

    text = json.dumps(parsed, indent=2, sort_keys=True)
    return _with_chunk_indexes(
        _chunk_serialized_text(
            record=record,
            text=text,
            heading=None,
            strategy="json_pretty_print_bounded",
        )
    )


def _chunk_yaml(record: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    parsed = (
        YAML_MODULE.safe_load(text) if YAML_MODULE is not None else _minimal_yaml(text)
    )
    if isinstance(parsed, dict):
        chunks = []
        for key in sorted(parsed, key=str):
            chunk_text = _dump_yaml({key: parsed[key]})
            chunks.extend(
                _chunk_serialized_text(
                    record=record,
                    text=chunk_text,
                    heading=str(key),
                    strategy="yaml_top_level_key",
                )
            )
        return _with_chunk_indexes(chunks)

    return _with_chunk_indexes(
        _chunk_serialized_text(
            record=record,
            text=_dump_yaml(parsed),
            heading=None,
            strategy="yaml_parsed_bounded",
        )
    )


def _chunk_csv(record: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        return []
    header = rows[0]
    data_rows = rows[1:]
    chunks: list[dict[str, Any]] = []
    for offset in range(0, len(data_rows), MAX_CSV_DATA_ROWS):
        row_group = data_rows[offset : offset + MAX_CSV_DATA_ROWS]
        if not row_group:
            continue
        text = _csv_rows_to_text(header, row_group)
        start_row = offset + 2
        end_row = start_row + len(row_group) - 1
        chunks.append(
            _base_chunk(
                record=record,
                chunk_index=0,
                text=text,
                heading="CSV rows",
                strategy="csv_header_and_bounded_rows",
                start_row=start_row,
                end_row=end_row,
            )
        )
    return _with_chunk_indexes(chunks)


def _chunk_line_window(
    record: dict[str, Any],
    lines: list[str],
    start_line: int,
    heading: str | None,
    strategy: str,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    window: list[str] = []
    window_start = start_line

    for offset, line in enumerate(lines):
        candidate = [*window, line]
        if window and (
            len(candidate) > MAX_CHUNK_LINES
            or len("\n".join(candidate)) > MAX_CHUNK_CHARS
        ):
            chunks.extend(
                _bounded_text_chunks(
                    record=record,
                    text="\n".join(window),
                    heading=heading,
                    strategy=strategy,
                    start_line=window_start,
                    end_line=window_start + len(window) - 1,
                )
            )
            window = [line]
            window_start = start_line + offset
        else:
            window = candidate
    if window:
        chunks.extend(
            _bounded_text_chunks(
                record=record,
                text="\n".join(window),
                heading=heading,
                strategy=strategy,
                start_line=window_start,
                end_line=window_start + len(window) - 1,
            )
        )
    return chunks


def _chunk_serialized_text(
    record: dict[str, Any], text: str, heading: str | None, strategy: str
) -> list[dict[str, Any]]:
    return _chunk_line_window(
        record=record,
        lines=text.splitlines(),
        start_line=1,
        heading=heading,
        strategy=strategy,
    )


def _bounded_text_chunks(
    record: dict[str, Any],
    text: str,
    heading: str | None,
    strategy: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> list[dict[str, Any]]:
    if not text.strip():
        return []
    if len(text) <= MAX_CHUNK_CHARS:
        return [
            _base_chunk(
                record=record,
                chunk_index=0,
                text=text,
                heading=heading,
                strategy=strategy,
                start_line=start_line,
                end_line=end_line,
            )
        ]

    chunks = []
    for start in range(0, len(text), MAX_CHUNK_CHARS):
        part = text[start : start + MAX_CHUNK_CHARS]
        if part.strip():
            chunks.append(
                _base_chunk(
                    record=record,
                    chunk_index=0,
                    text=part,
                    heading=heading,
                    strategy=f"{strategy}_char_split",
                    start_line=start_line,
                    end_line=end_line,
                )
            )
    return chunks


def _base_chunk(
    record: dict[str, Any],
    chunk_index: int,
    text: str,
    heading: str | None,
    strategy: str,
    start_line: int | None = None,
    end_line: int | None = None,
    start_row: int | None = None,
    end_row: int | None = None,
) -> dict[str, Any]:
    chunk: dict[str, Any] = {
        "source_id": record["source_id"],
        "source_path": record["path"],
        "source_file_name": record["file_name"],
        "source_type": record["source_type"],
        "chunk_index": chunk_index,
        "heading": heading,
        "text": text,
        "text_preview": _preview(text),
        "char_count": len(text),
        "word_count": len(text.split()),
        "chunk_strategy": strategy,
    }
    if start_line is not None:
        chunk["start_line"] = start_line
    if end_line is not None:
        chunk["end_line"] = end_line
    if start_row is not None:
        chunk["start_row"] = start_row
    if end_row is not None:
        chunk["end_row"] = end_row
    return chunk


def _with_chunk_indexes(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**chunk, "chunk_index": index} for index, chunk in enumerate(chunks, start=1)
    ]


def _markdown_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    marker, _, title = stripped.partition(" ")
    if marker and set(marker) == {"#"} and 1 <= len(marker) <= 6 and title.strip():
        return title.strip()
    return None


def _csv_rows_to_text(header: list[str], rows: list[list[str]]) -> str:
    output_lines = ["Columns: " + ", ".join(header)]
    for row in rows:
        values = []
        for index, column in enumerate(header):
            value = row[index] if index < len(row) else ""
            values.append(f"{column}={value}")
        output_lines.append("; ".join(values))
    return "\n".join(output_lines)


def _dump_yaml(value: Any) -> str:
    if YAML_MODULE is not None:
        return YAML_MODULE.safe_dump(value, sort_keys=True).strip()
    return json.dumps(value, indent=2, sort_keys=True)


def _minimal_yaml(text: str) -> Any:
    parsed: dict[str, Any] = {}
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        parsed[key.strip()] = value.strip().strip("\"'")
    return parsed or None


def _preview(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= TEXT_PREVIEW_CHARS:
        return compact
    return f"{compact[:TEXT_PREVIEW_CHARS]}…"
