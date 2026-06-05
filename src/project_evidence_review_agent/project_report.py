"""Render the final human-readable project evidence report.

The project evidence report is assembled only after the upstream bounded LLM
artifacts have already passed deterministic validation. This module deliberately
makes no LLM calls and does not add another reasoning stage: it copies and
organizes validated retrieval, claim-review, missing-evidence, and contradiction
payload fields into deterministic Markdown so a human reviewer has one clear
place to start.

Claim review, missing evidence, and contradiction candidates stay distinct in the
report because they mean different things. Claim review summarizes bounded
interpretation of selected evidence. Missing evidence entries are gap signals from
the supplied evidence pack, not proof that evidence does not exist elsewhere.
Contradiction entries are possible tensions in selected evidence, not final
findings. The report is review material only; it does not approve a project,
certify readiness, decide compliance, approve go-live, or replace human review.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_EVIDENCE_REPORT_FILE_NAME = "project_evidence_report.md"
SUPPORTED_STATUSES = {"evidence_supported"}
UNCLEAR_STATUSES = {
    "partially_supported",
    "unclear_from_supplied_evidence",
    "not_supported_by_supplied_evidence",
}
INPUT_ARTIFACTS = [
    "review_question.json",
    "retrieval_trace.json",
    "evidence_pack.json",
    "evidence_pack.md",
    "llm_safe_review_context.json",
    "claim_review.json",
    "missing_evidence.json",
    "contradiction_log.json",
]
GENERATED_ARTIFACTS = [
    "source_inventory.json",
    "evidence_index.json",
    "review_question.json",
    "retrieval_trace.json",
    "evidence_pack.json",
    "evidence_pack.md",
    "llm_safe_review_context.json",
    "claim_review.json",
    "missing_evidence.json",
    "contradiction_log.json",
    "project_evidence_report.md",
    "project_evidence_trace.json",
]


@dataclass(frozen=True)
class ProjectReportSummary:
    """Trace-facing summary for the rendered report artifact."""

    path: Path
    claim_count: int
    missing_evidence_count: int
    contradiction_candidate_count: int
    human_check_count: int


def write_project_evidence_report(
    *,
    output_dir: Path,
    evidence_pack: dict[str, Any],
    claim_review: dict[str, Any],
    missing_evidence: dict[str, Any],
    contradiction_log: dict[str, Any],
    trace_summary: dict[str, Any],
) -> ProjectReportSummary:
    """Write ``project_evidence_report.md`` from validated in-memory artifacts.

    The caller is responsible for invoking this only after claim review, missing
    evidence analysis, and contradiction analysis have completed and passed
    validation. Keeping that gate in the CLI prevents failed upstream artifacts
    from being presented as a successful final report.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / PROJECT_EVIDENCE_REPORT_FILE_NAME
    markdown = render_project_evidence_report(
        evidence_pack=evidence_pack,
        claim_review=claim_review,
        missing_evidence=missing_evidence,
        contradiction_log=contradiction_log,
        trace_summary=trace_summary,
    )
    path.write_text(markdown, encoding="utf-8")
    return ProjectReportSummary(
        path=path,
        claim_count=_claim_count(claim_review),
        missing_evidence_count=len(_list(missing_evidence.get("missing_evidence"))),
        contradiction_candidate_count=len(
            _list(contradiction_log.get("contradiction_candidates"))
        ),
        human_check_count=len(
            collect_recommended_human_checks(
                claim_review=claim_review,
                missing_evidence=missing_evidence,
                contradiction_log=contradiction_log,
            )
        ),
    )


def render_project_evidence_report(
    *,
    evidence_pack: dict[str, Any],
    claim_review: dict[str, Any],
    missing_evidence: dict[str, Any],
    contradiction_log: dict[str, Any],
    trace_summary: dict[str, Any] | None = None,
) -> str:
    """Return deterministic Markdown for validated report inputs.

    This renderer does not infer new facts. It preserves IDs and text from the
    validated artifacts, adds fixed explanatory boundary language, and uses
    deterministic ordering from the existing artifact lists and sorted source IDs.
    """

    trace_summary = trace_summary or {}
    question = str(evidence_pack.get("question") or claim_review.get("question") or "")
    claims = _list(claim_review.get("claims"))
    supported_claims = [c for c in claims if c.get("status") in SUPPORTED_STATUSES]
    unclear_claims = [c for c in claims if c.get("status") in UNCLEAR_STATUSES]
    missing_items = _list(missing_evidence.get("missing_evidence"))
    contradiction_items = _list(contradiction_log.get("contradiction_candidates"))
    human_checks = collect_recommended_human_checks(
        claim_review=claim_review,
        missing_evidence=missing_evidence,
        contradiction_log=contradiction_log,
    )

    lines: list[str] = [
        "# Project Evidence Report",
        "",
        "## Review question",
        "",
        _paragraph(question),
        "",
        "## How to read this report",
        "",
        "* This is review material, not project approval.",
        "* Claim review is bounded interpretation of selected evidence.",
        (
            "* Missing evidence means gap signals from the supplied evidence pack, "
            "not proof that evidence does not exist elsewhere."
        ),
        (
            "* Contradiction candidates are possible tensions in the supplied "
            "evidence, not final findings."
        ),
        "* Human review remains the final authority.",
        "",
        "## Run summary",
        "",
        "| Item | Value |",
        "| --- | --- |",
    ]
    summary_rows = [
        ("Sources loaded", trace_summary.get("loaded_source_count", "not recorded")),
        ("Sources skipped", trace_summary.get("skipped_source_count", "not recorded")),
        (
            "Evidence chunks indexed",
            trace_summary.get("evidence_chunk_count", "not recorded"),
        ),
        (
            "Evidence chunks selected",
            evidence_pack.get(
                "selected_chunk_count", len(_list(evidence_pack.get("selected_chunks")))
            ),
        ),
        ("Claim review status", claim_review.get("llm_review_status", "not recorded")),
        (
            "Claim review validation status",
            claim_review.get("validation_status", "not recorded"),
        ),
        ("Missing evidence count", len(missing_items)),
        ("Contradiction candidate count", len(contradiction_items)),
        (
            "Report status",
            trace_summary.get("project_evidence_report_status", "written"),
        ),
        (
            "No approval/go-live decision",
            (
                "approval_decision_status=not_performed; "
                "go_live_decision_status=not_performed"
            ),
        ),
    ]
    for label, value in summary_rows:
        lines.append(f"| {_table_cell(label)} | {_table_cell(value)} |")

    lines.extend(
        [
            "",
            "## Answer framing",
            "",
            (
                "* The supplied evidence supports, partially supports, or leaves "
                "unclear the following points."
            ),
            "* This section is not a readiness decision.",
            "* It should help a human reviewer decide what to inspect next.",
            "",
            "## Evidence-supported points",
            "",
        ]
    )
    if supported_claims:
        for claim in supported_claims:
            lines.extend(_render_claim(claim, include_status=False))
    else:
        lines.extend(
            [
                (
                    "No evidence-supported claims were included in the validated "
                    "claim review."
                ),
                "",
            ]
        )

    lines.extend(["## Partially supported or unclear points", ""])
    if unclear_claims:
        for claim in unclear_claims:
            lines.extend(_render_claim(claim, include_status=True))
    else:
        lines.extend(
            [
                (
                    "No partially supported, unclear, or not-supported claims were "
                    "included in the validated claim review."
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Missing evidence signals",
            "",
            (
                "Missing evidence is a gap signal from the supplied evidence pack. "
                "It is not proof that the evidence does not exist elsewhere."
            ),
            "",
        ]
    )
    if missing_items:
        for item in missing_items:
            lines.extend(_render_missing_evidence(item))
    else:
        lines.extend(
            [
                (
                    "No missing evidence signals were returned in the validated "
                    "follow-up analysis. This does not mean there are no gaps in "
                    "the real project."
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Possible contradiction candidates",
            "",
            (
                "Contradiction candidates are possible tensions in the supplied "
                "evidence. They require human review."
            ),
            "",
        ]
    )
    if contradiction_items:
        for item in contradiction_items:
            lines.extend(_render_contradiction(item))
    else:
        lines.extend(
            [
                (
                    "No contradiction candidates were returned in the validated "
                    "follow-up analysis. This does not mean there are no "
                    "contradictions in the real project."
                ),
                "",
            ]
        )

    lines.extend(_render_selected_evidence_map(evidence_pack))
    lines.extend(_render_source_map(evidence_pack))

    lines.extend(["## Recommended human checks", ""])
    if human_checks:
        lines.extend(f"* [ ] {_plain_value(check)}" for check in human_checks)
    else:
        lines.append(
            "No recommended human checks were included in the validated artifacts."
        )
    lines.append("")

    lines.extend(
        _render_limitations(
            evidence_pack, claim_review, missing_evidence, contradiction_log
        )
    )
    lines.extend(
        [
            "## Authority boundary",
            "",
            "* This report is review material, not project approval.",
            "* The agent cannot decide that a project is ready.",
            "* The agent cannot approve go-live.",
            (
                "* The agent cannot certify compliance, security, privacy, "
                "or legal status."
            ),
            "* Human review remains the final authority.",
            "",
            "## Artifact list",
            "",
        ]
    )
    lines.extend(f"* `{artifact}`" for artifact in GENERATED_ARTIFACTS)
    lines.append("")
    return "\n".join(lines)


def collect_recommended_human_checks(
    *,
    claim_review: dict[str, Any],
    missing_evidence: dict[str, Any],
    contradiction_log: dict[str, Any],
) -> list[str]:
    """Collect artifact-provided human checks with simple deterministic dedupe."""

    checks: list[str] = []
    checks.extend(
        str(item)
        for item in _list(claim_review.get("recommended_human_checks"))
        if item
    )
    checks.extend(
        str(item.get("suggested_human_check"))
        for item in _list(missing_evidence.get("missing_evidence"))
        if item.get("suggested_human_check")
    )
    checks.extend(
        str(item.get("suggested_human_check"))
        for item in _list(contradiction_log.get("contradiction_candidates"))
        if item.get("suggested_human_check")
    )
    deduped: list[str] = []
    seen: set[str] = set()
    for check in checks:
        key = " ".join(check.split()).casefold()
        if key and key not in seen:
            deduped.append(check)
            seen.add(key)
    return deduped


def _render_claim(claim: dict[str, Any], *, include_status: bool) -> list[str]:
    lines = [f"### {_heading(str(claim.get('claim_id', 'Claim')))}", ""]
    lines.append(f"* Claim ID: `{_plain_value(claim.get('claim_id', ''))}`")
    lines.append(f"* Claim text: {_plain_value(claim.get('claim_text', ''))}")
    if include_status:
        lines.append(f"* Status: `{_plain_value(claim.get('status', ''))}`")
    lines.append(f"* Cited evidence IDs: {_id_list(claim.get('evidence_ids'))}")
    lines.append(f"* Explanation: {_plain_value(claim.get('explanation', ''))}")
    caveats = _list(claim.get("caveats"))
    lines.append(f"* Caveats: {_joined_list(caveats)}")
    lines.append("")
    return lines


def _render_missing_evidence(item: dict[str, Any]) -> list[str]:
    heading = _heading(str(item.get("missing_evidence_id", "Missing evidence signal")))
    missing_id = _plain_value(item.get("missing_evidence_id", ""))
    human_check = _plain_value(item.get("suggested_human_check", ""))
    return [
        f"### {heading}",
        "",
        f"* Missing evidence ID: `{missing_id}`",
        f"* Gap type: `{_plain_value(item.get('gap_type', ''))}`",
        f"* Summary: {_plain_value(item.get('summary', ''))}",
        f"* Details: {_plain_value(item.get('details', ''))}",
        f"* Related claim IDs: {_id_list(item.get('related_claim_ids'))}",
        f"* Related evidence IDs: {_id_list(item.get('related_evidence_ids'))}",
        f"* Suggested human check: {human_check}",
        f"* Why it matters: {_plain_value(item.get('why_it_matters', ''))}",
        f"* Confidence: `{_plain_value(item.get('confidence', ''))}`",
        "",
    ]


def _render_contradiction(item: dict[str, Any]) -> list[str]:
    side_a = (
        item.get("evidence_side_a")
        if isinstance(item.get("evidence_side_a"), dict)
        else {}
    )
    side_b = (
        item.get("evidence_side_b")
        if isinstance(item.get("evidence_side_b"), dict)
        else {}
    )
    heading = _heading(str(item.get("contradiction_id", "Contradiction candidate")))
    contradiction_id = _plain_value(item.get("contradiction_id", ""))
    human_check = _plain_value(item.get("suggested_human_check", ""))
    return [
        f"### {heading}",
        "",
        f"* Contradiction ID: `{contradiction_id}`",
        f"* Summary: {_plain_value(item.get('summary', ''))}",
        f"* Evidence side A evidence IDs: {_id_list(side_a.get('evidence_ids'))}",
        f"* Evidence side A description: {_plain_value(side_a.get('description', ''))}",
        f"* Evidence side B evidence IDs: {_id_list(side_b.get('evidence_ids'))}",
        f"* Evidence side B description: {_plain_value(side_b.get('description', ''))}",
        f"* Explanation: {_plain_value(item.get('explanation', ''))}",
        f"* Related claim IDs: {_id_list(item.get('related_claim_ids'))}",
        f"* Suggested human check: {human_check}",
        f"* Confidence: `{_plain_value(item.get('confidence', ''))}`",
        "",
    ]


def _render_selected_evidence_map(evidence_pack: dict[str, Any]) -> list[str]:
    chunks = _list(evidence_pack.get("selected_chunks"))
    lines = [
        "## Selected evidence map",
        "",
        (
            "The selected evidence excerpts are in `evidence_pack.md`. The compact "
            "map below points to `evidence_pack.json` and `retrieval_trace.json` "
            "for retrieval details."
        ),
        "",
        (
            "| Evidence ID | Source ID | Source file | Reference | Matched "
            "terms | Retrieval score |"
        ),
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if chunks:
        for chunk in chunks:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(chunk.get("evidence_id", "")),
                        _table_cell(chunk.get("source_id", "")),
                        _table_cell(chunk.get("source_file_name", "")),
                        _table_cell(_reference(chunk)),
                        _table_cell(
                            ", ".join(
                                str(term) for term in _list(chunk.get("matched_terms"))
                            )
                        ),
                        _table_cell(chunk.get("retrieval_score", "")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| _None_ | _None_ | _None_ | _None_ | _None_ | _None_ |")
    lines.append("")
    return lines


def _render_source_map(evidence_pack: dict[str, Any]) -> list[str]:
    source_map = evidence_pack.get("source_map", {}) or {}
    lines = [
        "## Source map",
        "",
        "| Source ID | File name | Path | Type | Fingerprint metadata |",
        "| --- | --- | --- | --- | --- |",
    ]
    if isinstance(source_map, dict) and source_map:
        for source_id in sorted(source_map):
            source = source_map[source_id] or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(source.get("source_id", source_id)),
                        _table_cell(source.get("source_file_name", "")),
                        _table_cell(source.get("source_path", "")),
                        _table_cell(source.get("source_type", "")),
                        _table_cell(_fingerprint(source)),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| _None_ | _None_ | _None_ | _None_ | _None_ |")
    lines.append("")
    return lines


def _render_limitations(*payloads: dict[str, Any]) -> list[str]:
    lines = ["## Limitations", ""]
    fixed = [
        "The report only covers supplied local material.",
        "Retrieval is lexical and may miss relevant evidence.",
        "The LLM reviewed only selected evidence chunks.",
        "The LLM may still make mistakes.",
        "Validation checks structure and citations, not real-world truth.",
        "Human review remains required.",
    ]
    limitations: list[str] = []
    for payload in payloads:
        limitations.extend(
            str(item) for item in _list(payload.get("limitations")) if item
        )
    for item in _dedupe([*limitations, *fixed]):
        lines.append(f"* {_plain_value(item)}")
    lines.append("")
    return lines


def _claim_count(claim_review: dict[str, Any]) -> int:
    return len(_list(claim_review.get("claims")))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = " ".join(str(item).split()).casefold()
        if key and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def _paragraph(value: str) -> str:
    return _plain_value(value) if value else "_Not recorded._"


def _plain_value(value: Any) -> str:
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(text.split()) if text else "not recorded"


def _table_cell(value: Any) -> str:
    text = _plain_value(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def _heading(value: str) -> str:
    return _plain_value(value).replace("#", "").strip() or "Item"


def _id_list(value: Any) -> str:
    items = [str(item) for item in _list(value) if item]
    return ", ".join(f"`{item}`" for item in items) if items else "_None recorded_"


def _joined_list(items: list[Any]) -> str:
    return (
        "; ".join(_plain_value(item) for item in items) if items else "_None recorded_"
    )


def _reference(chunk: dict[str, Any]) -> str:
    if "start_line" in chunk or "end_line" in chunk:
        return f"lines {chunk.get('start_line', '?')}-{chunk.get('end_line', '?')}"
    if "start_row" in chunk or "end_row" in chunk:
        return f"rows {chunk.get('start_row', '?')}-{chunk.get('end_row', '?')}"
    return "not recorded"


def _fingerprint(source: dict[str, Any]) -> str:
    status = source.get("fingerprint_status", "not recorded")
    sha = str(source.get("sha256", ""))
    if sha:
        return f"{status}; sha256={sha[:12]}…"
    return str(status)
