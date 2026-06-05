"""Build a deterministic local source inventory before evidence review.

The source inventory stage answers a narrow question: what local material was
supplied, what can this tool safely load today, and what was skipped? It exists
before evidence chunking so later stages can work from an explicit, reviewable
list of bounded local inputs instead of discovering files implicitly.

This module deliberately does not chunk documents, retrieve evidence, assemble
evidence packs, call an LLM, interpret whether a file supports a claim, or make
readiness or go-live decisions. Loading a file only means the file type is
supported and basic metadata could be recorded. Human review remains the final
authority over project claims and decisions.
"""

from __future__ import annotations

import csv
import importlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SOURCE_INVENTORY_FILE_NAME = "source_inventory.json"
SUPPORTED_EXTENSIONS = {".csv", ".json", ".md", ".txt", ".yaml", ".yml"}
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "venv",
}
PREVIEW_CHARACTER_LIMIT = 500
MAX_RECORDED_KEYS = 25
YAML_MODULE = (
    importlib.import_module("yaml")
    if importlib.util.find_spec("yaml") is not None
    else None
)


@dataclass(frozen=True)
class InventorySummary:
    """Small summary of source inventory results for the run trace."""

    path: Path
    loaded_count: int
    skipped_count: int


def build_source_inventory(sources_path: Path) -> dict[str, Any]:
    """Inspect a local source path and return inventory records.

    Args:
        sources_path: Existing local file or directory to inspect.

    Returns:
        A JSON-serializable payload containing deterministic records for loaded
        supported files and skipped unsupported files.

    Raises:
        FileNotFoundError: If the supplied path does not exist.
        PermissionError: If the supplied path cannot be read.
        NotADirectoryError: If a path component cannot be inspected as needed.
    """

    resolved_sources_path = sources_path.expanduser()
    if not resolved_sources_path.exists():
        raise FileNotFoundError(f"--sources path does not exist: {sources_path}")

    source_files = _discover_source_files(resolved_sources_path)
    records = [
        _build_record(
            source_id=f"SRC-{index:04d}", path=path, root=resolved_sources_path
        )
        for index, path in enumerate(source_files, start=1)
    ]
    loaded_count = sum(1 for record in records if record["status"] == "loaded")
    skipped_count = sum(1 for record in records if record["status"] == "skipped")

    return {
        "inventory_version": 1,
        "source_path": str(sources_path),
        "source_path_type": "directory" if resolved_sources_path.is_dir() else "file",
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "records": records,
        "summary": {
            "total_sources_inspected": len(records),
            "loaded_sources": loaded_count,
            "skipped_sources": skipped_count,
        },
        "boundary_note": (
            "Source inventory describes local material only. It is not evidence "
            "review and does not say whether any file supports a project claim."
        ),
    }


def write_source_inventory(sources_path: Path, output_dir: Path) -> InventorySummary:
    """Write ``source_inventory.json`` and return counts for the trace."""

    inventory = build_source_inventory(sources_path)
    return write_source_inventory_payload(inventory=inventory, output_dir=output_dir)


def write_source_inventory_payload(
    inventory: dict[str, Any], output_dir: Path
) -> InventorySummary:
    """Write a prebuilt inventory payload without changing its contract."""

    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / SOURCE_INVENTORY_FILE_NAME
    inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = inventory["summary"]
    return InventorySummary(
        path=inventory_path,
        loaded_count=summary["loaded_sources"],
        skipped_count=summary["skipped_sources"],
    )


def _discover_source_files(sources_path: Path) -> list[Path]:
    """Return source files in deterministic order while ignoring tool caches."""

    if sources_path.is_file():
        return [sources_path]
    if not sources_path.is_dir():
        raise FileNotFoundError(
            f"--sources path is not a readable file or directory: {sources_path}"
        )

    discovered: list[Path] = []
    for child in sorted(
        sources_path.rglob("*"),
        key=lambda path: path.relative_to(sources_path).as_posix(),
    ):
        relative_parts = child.relative_to(sources_path).parts
        if any(_should_ignore_directory(part) for part in relative_parts[:-1]):
            continue
        if child.is_file():
            discovered.append(child)
    return discovered


def _should_ignore_directory(name: str) -> bool:
    """Return whether a directory name is hidden or a Python/tooling cache."""

    return name in IGNORED_DIRECTORY_NAMES or name.startswith(".")


def _build_record(source_id: str, path: Path, root: Path) -> dict[str, Any]:
    """Build one inventory record without interpreting project meaning."""

    extension = path.suffix.lower()
    record: dict[str, Any] = {
        "source_id": source_id,
        "path": _display_path(path=path, root=root),
        "file_name": path.name,
        "extension": extension,
        "source_type": _source_type(extension),
        "size_bytes": _safe_size(path),
    }

    if extension not in SUPPORTED_EXTENSIONS:
        record.update(
            {
                "status": "skipped",
                "skip_reason": f"unsupported file extension: {extension or '<none>'}",
            }
        )
        return record

    try:
        if extension in {".md", ".txt"}:
            return _load_plain_text(record, path)
        if extension == ".json":
            return _load_json(record, path)
        if extension in {".yaml", ".yml"}:
            return _load_yaml(record, path)
        if extension == ".csv":
            return _load_csv(record, path)
    except UnicodeDecodeError as exc:
        record.update(
            {"status": "skipped", "skip_reason": f"could not read as UTF-8 text: {exc}"}
        )
        return record
    except OSError as exc:
        record.update(
            {"status": "skipped", "skip_reason": f"source file cannot be read: {exc}"}
        )
        return record

    record.update({"status": "skipped", "skip_reason": "unsupported file extension"})
    return record


def _load_plain_text(record: dict[str, Any], path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    record.update(
        {
            "status": "loaded",
            "parser": "utf-8-text",
            "line_count": _line_count(text),
            "content_preview": _bounded_preview(text),
        }
    )
    return record


def _load_json(record: dict[str, Any], path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        record.update({"status": "skipped", "skip_reason": f"invalid JSON: {exc.msg}"})
        return record

    record.update(
        {
            "status": "loaded",
            "parser": "python-json",
            "line_count": _line_count(text),
            "json_top_level_type": type(parsed).__name__,
        }
    )
    if isinstance(parsed, dict):
        record["json_top_level_keys"] = sorted(str(key) for key in parsed)[
            :MAX_RECORDED_KEYS
        ]
    return record


def _load_yaml(record: dict[str, Any], path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        parsed = _safe_load_yaml(text)
    except ValueError as exc:
        record.update({"status": "skipped", "skip_reason": f"invalid YAML: {exc}"})
        return record

    record.update(
        {
            "status": "loaded",
            "parser": "pyyaml-safe_load"
            if YAML_MODULE is not None
            else "minimal-yaml-fallback",
            "line_count": _line_count(text),
            "yaml_top_level_type": type(parsed).__name__,
        }
    )
    if isinstance(parsed, dict):
        record["yaml_top_level_keys"] = sorted(str(key) for key in parsed)[
            :MAX_RECORDED_KEYS
        ]
    return record


def _safe_load_yaml(text: str) -> Any:
    """Parse YAML with PyYAML, or a tiny fallback for offline test environments."""

    if YAML_MODULE is not None:
        try:
            return YAML_MODULE.safe_load(text)
        except YAML_MODULE.YAMLError as exc:
            raise ValueError(exc.__class__.__name__) from exc

    parsed: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("-"):
            if current_list_key is None:
                raise ValueError("list item without a key")
            parsed.setdefault(current_list_key, []).append(stripped[1:].strip())
            continue
        if ":" not in stripped:
            raise ValueError("expected key-value mapping")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError("empty key")
        if value == "":
            parsed[key] = []
            current_list_key = key
        else:
            parsed[key] = _parse_yaml_scalar(value)
            current_list_key = None
    return parsed or None


def _parse_yaml_scalar(value: str) -> Any:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value.strip("\"'")


def _load_csv(record: dict[str, Any], path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    rows = list(csv.reader(text.splitlines()))
    column_names = rows[0] if rows else []
    record.update(
        {
            "status": "loaded",
            "parser": "python-csv",
            "line_count": _line_count(text),
            "row_count": max(len(rows) - 1, 0) if column_names else 0,
            "column_names": column_names,
            "content_preview": _bounded_preview(
                "\n".join(",".join(row) for row in rows[:3])
            ),
        }
    )
    return record


def _display_path(path: Path, root: Path) -> str:
    if root.is_dir():
        return path.relative_to(root).as_posix()
    return path.name


def _source_type(extension: str) -> str:
    return {
        ".csv": "csv",
        ".json": "json",
        ".md": "markdown",
        ".txt": "text",
        ".yaml": "yaml",
        ".yml": "yaml",
    }.get(extension, "unsupported")


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _line_count(text: str) -> int:
    if text == "":
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _bounded_preview(text: str) -> str:
    compact = text.strip()
    if len(compact) <= PREVIEW_CHARACTER_LIMIT:
        return compact
    return f"{compact[:PREVIEW_CHARACTER_LIMIT]}…"
