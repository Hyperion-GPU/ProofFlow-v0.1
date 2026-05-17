from dataclasses import dataclass
from typing import Any

import hashlib
import re

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import IssueTriageRequest, IssueTriageResponse
from proofflow.services.json_utils import dumps_metadata

TEXT_CHUNK_LINES = 200
SEVERITY_ORDER = {"low": 0, "info": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class IssueSignals:
    component: str
    suggested_labels: list[str]
    has_reproduction_steps: bool
    has_expected_behavior: bool
    has_environment_details: bool
    bug_like: bool


@dataclass(frozen=True)
class ClaimSpec:
    severity: str
    text: str
    evidence_content: str
    source_ref: str


def triage_issue(payload: IssueTriageRequest) -> IssueTriageResponse:
    title = payload.title.strip()
    body = payload.body.strip()
    labels = _clean_labels(payload.labels)
    source_url = payload.source_url.strip() if payload.source_url else None
    issue_text = _format_issue_text(title, body, source_url, labels)
    signals = _extract_signals(title, body, labels)
    claim_specs = _build_claim_specs(title, body, labels, source_url, signals)
    risk_level = _risk_level(claim_specs)

    case_id = new_uuid()
    run_id = new_uuid()
    with connect() as connection:
        _insert_case(connection, case_id, title, source_url, labels, signals, risk_level)
        _insert_run(connection, run_id, case_id, risk_level)
        artifact_id = _insert_issue_artifact(
            connection=connection,
            case_id=case_id,
            title=title,
            content=issue_text,
            source_url=source_url,
            labels=labels,
            signals=signals,
        )
        claims_created, evidence_created = _insert_claims_and_evidence(
            connection,
            case_id,
            run_id,
            artifact_id,
            claim_specs,
        )
        connection.commit()

    return IssueTriageResponse(
        case_id=case_id,
        run_id=run_id,
        risk_level=risk_level,
        artifact_id=artifact_id,
        component=signals.component,
        suggested_labels=signals.suggested_labels,
        has_reproduction_steps=signals.has_reproduction_steps,
        has_expected_behavior=signals.has_expected_behavior,
        has_environment_details=signals.has_environment_details,
        claims_created=claims_created,
        evidence_created=evidence_created,
    )


def _insert_case(
    connection: Any,
    case_id: str,
    title: str,
    source_url: str | None,
    labels: list[str],
    signals: IssueSignals,
    risk_level: str,
) -> None:
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO cases (
            id, title, case_type, status, summary, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            f"Issue triage: {title}",
            "issue_triage",
            "open",
            f"ProofFlow issue triage for {title}",
            dumps_metadata(
                {
                    "source": "issue_triage",
                    "source_url": source_url,
                    "labels": labels,
                    "component": signals.component,
                    "suggested_labels": signals.suggested_labels,
                    "has_reproduction_steps": signals.has_reproduction_steps,
                    "has_expected_behavior": signals.has_expected_behavior,
                    "has_environment_details": signals.has_environment_details,
                    "risk_level": risk_level,
                }
            ),
            now,
            now,
        ),
    )


def _insert_run(connection: Any, run_id: str, case_id: str, risk_level: str) -> None:
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO runs (
            id, case_id, run_type, status, started_at, finished_at,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            case_id,
            "issue_triage",
            "completed",
            now,
            now,
            dumps_metadata({"risk_level": risk_level, "test_status": "not_applicable"}),
            now,
            now,
        ),
    )


def _insert_issue_artifact(
    *,
    connection: Any,
    case_id: str,
    title: str,
    content: str,
    source_url: str | None,
    labels: list[str],
    signals: IssueSignals,
) -> str:
    now = utc_now_iso()
    artifact_id = new_uuid()
    encoded = content.encode("utf-8")
    connection.execute(
        """
        INSERT INTO artifacts (
            id, artifact_type, uri, name, mime_type, sha256, size_bytes,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            "issue",
            f"issue-triage://{case_id}/issue.md",
            "issue.md",
            "text/markdown",
            hashlib.sha256(encoded).hexdigest(),
            len(encoded),
            dumps_metadata(
                {
                    "source": "issue_triage",
                    "source_url": source_url,
                    "title": title,
                    "labels": labels,
                    "component": signals.component,
                }
            ),
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT INTO case_artifacts (
            case_id, artifact_id, role, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (case_id, artifact_id, "primary", now, now),
    )
    _insert_text_chunks(connection, artifact_id, content)
    return artifact_id


def _insert_text_chunks(connection: Any, artifact_id: str, content: str) -> None:
    lines = content.splitlines() or [""]
    for chunk_index, start in enumerate(range(0, len(lines), TEXT_CHUNK_LINES)):
        now = utc_now_iso()
        chunk_lines = lines[start : start + TEXT_CHUNK_LINES]
        chunk_content = "\n".join(chunk_lines)
        cursor = connection.execute(
            """
            INSERT INTO artifact_text_chunks (
                id, artifact_id, chunk_index, content, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                artifact_id,
                chunk_index,
                chunk_content,
                dumps_metadata(
                    {
                        "start_line": start + 1,
                        "end_line": start + len(chunk_lines),
                        "source": "issue_triage",
                    }
                ),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO artifact_text_fts(rowid, content, artifact_id, chunk_index)
            VALUES (?, ?, ?, ?)
            """,
            (cursor.lastrowid, chunk_content, artifact_id, chunk_index),
        )


def _insert_claims_and_evidence(
    connection: Any,
    case_id: str,
    run_id: str,
    artifact_id: str,
    claims: list[ClaimSpec],
) -> tuple[int, int]:
    claims_created = 0
    evidence_created = 0
    for claim in claims:
        now = utc_now_iso()
        claim_id = new_uuid()
        connection.execute(
            """
            INSERT INTO claims (
                id, case_id, run_id, claim_text, claim_type, status,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                case_id,
                run_id,
                claim.text,
                "issue_triage",
                "open",
                dumps_metadata({"severity": claim.severity}),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO evidence (
                id, case_id, artifact_id, claim_id, evidence_type, content,
                source_ref, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                case_id,
                artifact_id,
                claim_id,
                "issue_text",
                claim.evidence_content,
                claim.source_ref,
                dumps_metadata({"source": "issue_triage"}),
                now,
                now,
            ),
        )
        claims_created += 1
        evidence_created += 1
    return claims_created, evidence_created


def _build_claim_specs(
    title: str,
    body: str,
    labels: list[str],
    source_url: str | None,
    signals: IssueSignals,
) -> list[ClaimSpec]:
    claims = [
        ClaimSpec(
            severity="info",
            text=f"Issue source captured for triage: {title}",
            evidence_content="\n".join(
                [
                    f"Title: {title}",
                    f"Source URL: {source_url or 'not provided'}",
                    f"Labels: {', '.join(labels) if labels else 'none'}",
                    f"Body characters: {len(body)}",
                ]
            ),
            source_ref="issue.md:1",
        ),
        ClaimSpec(
            severity="info",
            text=f"Issue appears to affect component: {signals.component}",
            evidence_content="\n".join(
                [
                    f"Component: {signals.component}",
                    f"Suggested labels: {', '.join(signals.suggested_labels)}",
                    "Title/body keywords inspected deterministically.",
                ]
            ),
            source_ref="issue.md:1",
        ),
    ]

    if not body:
        claims.append(
            ClaimSpec(
                severity="medium",
                text="Issue body is empty, so triage evidence is incomplete.",
                evidence_content="The issue title is present, but no body text was provided.",
                source_ref="issue.md:1",
            )
        )
    elif signals.bug_like and not signals.has_reproduction_steps:
        claims.append(
            ClaimSpec(
                severity="medium",
                text="Bug-like issue is missing clear reproduction steps.",
                evidence_content=(
                    "Bug label or bug-like wording was found, but no numbered steps "
                    "or reproduction section was detected."
                ),
                source_ref="issue.md:1",
            )
        )
    elif signals.has_reproduction_steps:
        claims.append(
            ClaimSpec(
                severity="info",
                text="Issue includes reproduction steps.",
                evidence_content="Detected numbered steps or a reproduction section in the issue body.",
                source_ref="issue.md:1",
            )
        )

    if signals.has_expected_behavior:
        claims.append(
            ClaimSpec(
                severity="info",
                text="Issue includes expected behavior context.",
                evidence_content="Detected expected-behavior wording in the issue body.",
                source_ref="issue.md:1",
            )
        )
    elif signals.bug_like:
        claims.append(
            ClaimSpec(
                severity="medium",
                text="Bug-like issue is missing expected behavior context.",
                evidence_content=(
                    "Bug label or bug-like wording was found, but no expected-behavior "
                    "section or wording was detected."
                ),
                source_ref="issue.md:1",
            )
        )

    if signals.has_environment_details:
        claims.append(
            ClaimSpec(
                severity="info",
                text="Issue includes environment details.",
                evidence_content="Detected OS, Python, Node, browser, version, or environment wording.",
                source_ref="issue.md:1",
            )
        )

    return claims


def _extract_signals(title: str, body: str, labels: list[str]) -> IssueSignals:
    text = f"{title}\n{body}".lower()
    label_text = " ".join(labels).lower()
    component = _infer_component(text, label_text)
    bug_like = _has_any(text, ("bug", "error", "fail", "crash", "broken", "regression")) or (
        "bug" in label_text
    )
    suggested_labels = _suggest_labels(component, bug_like, text, label_text)
    return IssueSignals(
        component=component,
        suggested_labels=suggested_labels,
        has_reproduction_steps=_has_reproduction_steps(body),
        has_expected_behavior=_has_expected_behavior(body),
        has_environment_details=_has_environment_details(body),
        bug_like=bug_like,
    )


def _infer_component(text: str, label_text: str) -> str:
    combined = f"{text}\n{label_text}"
    component_terms = (
        ("codex_plugin", ("codex", "plugin", "skill", "mcp config", ".mcp.json")),
        ("mcp_server", ("mcp", "proofflow-mcp", "tool")),
        ("agentguard", ("agentguard", "code review", "proof packet", "diff review")),
        ("localproof", ("localproof", "scan", "suggest", "action list")),
        ("policy_gate", ("policy gate", "pending_decision", "decision")),
        ("frontend", ("frontend", "ui", "browser", "button", "screen")),
        ("backend", ("backend", "api", "fastapi", "sqlite")),
        ("docs", ("readme", "docs", "documentation")),
    )
    for component, terms in component_terms:
        if any(term in combined for term in terms):
            return component
    return "unknown"


def _suggest_labels(
    component: str,
    bug_like: bool,
    text: str,
    label_text: str,
) -> list[str]:
    labels: list[str] = []
    if bug_like:
        labels.append("bug")
    elif _has_any(text, ("feature", "enhancement", "add support", "request")):
        labels.append("enhancement")
    else:
        labels.append("triage")
    if component != "unknown":
        labels.append(f"component:{component}")
    if "comfort" in text or "ux" in text or "usability" in text or "使用" in text:
        labels.append("usability")
    for label in label_text.split():
        if label and label not in labels:
            labels.append(label)
    return labels[:6]


def _has_reproduction_steps(body: str) -> bool:
    lowered = body.lower()
    if any(phrase in lowered for phrase in ("steps to reproduce", "reproduce", "复现", "重现")):
        return True
    numbered_steps = re.findall(r"(?m)^\s*(?:\d+[\.)]|[-*])\s+\S+", body)
    return len(numbered_steps) >= 2


def _has_expected_behavior(body: str) -> bool:
    lowered = body.lower()
    return any(
        phrase in lowered
        for phrase in (
            "expected behavior",
            "expected",
            "should",
            "i expected",
            "期望",
            "应该",
        )
    )


def _has_environment_details(body: str) -> bool:
    lowered = body.lower()
    return any(
        phrase in lowered
        for phrase in (
            "environment",
            "os:",
            "windows",
            "macos",
            "ubuntu",
            "python",
            "node",
            "browser",
            "version",
            "环境",
        )
    )


def _format_issue_text(
    title: str,
    body: str,
    source_url: str | None,
    labels: list[str],
) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- Source URL: {source_url or 'not provided'}",
            f"- Labels: {', '.join(labels) if labels else 'none'}",
            "",
            "## Body",
            "",
            body or "No issue body provided.",
        ]
    )


def _clean_labels(labels: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for label in labels:
        normalized = label.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        cleaned.append(normalized)
        seen.add(key)
    return cleaned


def _risk_level(claims: list[ClaimSpec]) -> str:
    highest = "info"
    for claim in claims:
        if SEVERITY_ORDER[claim.severity] > SEVERITY_ORDER[highest]:
            highest = claim.severity
    return highest


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
