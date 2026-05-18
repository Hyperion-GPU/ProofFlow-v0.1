"""Run a cross-domain Ledger Risk Hints dogfood matrix.

This script keeps the exercise local and cheap. It starts the ProofFlow backend
in-process, routes MCP tool calls through the real handlers, and creates a
separate temporary git repo for each scenario.

Usage:
    python scripts/ledger_risk_hints_dogfood_matrix.py [--cleanup]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
MCP_SERVER_ROOT = REPO_ROOT / "mcp-server"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(MCP_SERVER_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_ROOT / "src"))


@dataclass(frozen=True)
class Scenario:
    slug: str
    title: str
    purpose: str
    filename: str
    baseline_content: str
    final_content: str
    objective: str
    test_command: str
    algorithm_requirements: list[str]
    cost_budget_contract: dict[str, Any]
    decision_summary: str
    chosen_approach: str
    rationale: str
    forbidden_approaches: list[str]
    budget: dict[str, Any]
    event_content: str
    test_usage: dict[str, Any]
    method_evidence_type: str | None = None
    method_evidence_content: str | None = None
    expected_hints: set[str] = field(default_factory=set)
    clean: bool = False


SCENARIOS = [
    Scenario(
        slug="data-conversion-lineage",
        title="Data conversion lineage",
        purpose="Detects regenerate-over-mapping, forbidden route, budget overrun, and test-only proof.",
        filename="pipeline.py",
        baseline_content=(
            "def convert(rows):\n"
            "    return [{'source_id': row['id'], 'derived': row['value'] * 2} for row in rows]\n"
        ),
        final_content=(
            "def convert(rows):\n"
            "    return [{'derived': row['value'] * 2} for row in rows]\n"
        ),
        objective="Preserve source mapping and lineage in a data conversion pipeline",
        test_command="python -m pytest data_conversion",
        algorithm_requirements=["preserve source mapping and lineage"],
        cost_budget_contract={"max_api_calls": 0, "max_gpu_jobs": 0},
        decision_summary="Regenerate derived records",
        chosen_approach="Regenerate derived records with a new API call.",
        rationale="This is simpler than preserving source mapping through the transform.",
        forbidden_approaches=["regenerate derived records"],
        budget={"max_api_calls": 0, "max_gpu_jobs": 0},
        event_content="Implemented derived-row conversion by regenerating records.",
        test_usage={"api_calls": 3, "gpu_jobs": 1},
        expected_hints={
            "forbidden_algorithm_mentioned",
            "regeneration_over_mapping",
            "cost_budget_possible_overrun",
            "test_proves_output_not_method",
        },
    ),
    Scenario(
        slug="state-sync",
        title="State sync",
        purpose="Detects recreation when the contract asks for source mapping, while method evidence avoids test-only noise.",
        filename="sync_state.py",
        baseline_content="def sync(source, target):\n    return target.apply_patch(source.diff())\n",
        final_content="def sync(source, target):\n    return target.recreate_from_cache(source.cache())\n",
        objective="Preserve source mapping while applying state sync patches",
        test_command="python -m pytest state_sync",
        algorithm_requirements=["preserve source mapping while applying patches"],
        cost_budget_contract={"max_iterations": 3},
        decision_summary="Recreate state before sync",
        chosen_approach="Recreate remote state from local cache, then verify output.",
        rationale="The recreated state is easier to compare than patch application.",
        forbidden_approaches=[],
        budget={"max_iterations": 3},
        event_content="State sync uses recreate-from-cache before verification.",
        test_usage={"iterations": 2},
        method_evidence_type="mapping",
        method_evidence_content="Mapping evidence: source state IDs are mapped to recreated target IDs.",
        expected_hints={"regeneration_over_mapping"},
    ),
    Scenario(
        slug="expensive-external-call",
        title="Expensive external call",
        purpose="Detects API/GPU/LLM batch usage when the ledger has no structured budget.",
        filename="enrich.py",
        baseline_content="def enrich(rows):\n    return rows\n",
        final_content="def enrich(rows):\n    return [{'label': 'remote', **row} for row in rows]\n",
        objective="Evaluate enrichment strategy for records",
        test_command="python -m pytest enrichment",
        algorithm_requirements=["choose enrichment strategy"],
        cost_budget_contract={},
        decision_summary="Use external enrichment",
        chosen_approach="Use an external API call and LLM batch to enrich rows.",
        rationale="The remote enrichment service gives stable labels for this test fixture.",
        forbidden_approaches=[],
        budget={},
        event_content="Called external service with API calls, one GPU job, and an LLM batch.",
        test_usage={"api_calls": 2, "gpu_jobs": 1},
        expected_hints={"expensive_action_without_budget"},
    ),
    Scenario(
        slug="refactor-behavior-preservation",
        title="Refactor behavior preservation",
        purpose="Detects output-only tests when a method-sensitive refactor lacks trace evidence.",
        filename="parser.py",
        baseline_content="def parse(value):\n    return value.strip().lower()\n",
        final_content="def parse(value):\n    cleaned = value.strip()\n    return cleaned.lower()\n",
        objective="Preserve parser behavior during refactor",
        test_command="python -m pytest parser_refactor",
        algorithm_requirements=["preserve parser behavior"],
        cost_budget_contract={"max_runtime_seconds": 60},
        decision_summary="Refactor parser branches",
        chosen_approach="Refactor parser branches while keeping output snapshots stable.",
        rationale="The parser remains deterministic and local.",
        forbidden_approaches=[],
        budget={"max_runtime_seconds": 60},
        event_content="Parser refactor completed with output snapshot tests.",
        test_usage={"runtime_seconds": 12},
        expected_hints={"test_proves_output_not_method"},
    ),
    Scenario(
        slug="clean-method-evidence",
        title="Clean method-evidence baseline",
        purpose="Confirms a method-sensitive contract stays quiet when mapping, trace, and cost evidence exist.",
        filename="transform.py",
        baseline_content=(
            "def transform(rows):\n"
            "    return [{'source_id': row['id'], 'value': row['value']} for row in rows]\n"
        ),
        final_content=(
            "def transform(rows):\n"
            "    return [{'source_id': row['id'], 'value': row['value'] * 2} for row in rows]\n"
        ),
        objective="Preserve source mapping and lineage while transforming rows",
        test_command="python -m pytest clean_transform",
        algorithm_requirements=["preserve source mapping and lineage"],
        cost_budget_contract={"max_api_calls": 0, "max_gpu_jobs": 0, "max_runtime_seconds": 60},
        decision_summary="Use local mapping transform",
        chosen_approach="Maintain source mapping through a local transform and algorithm trace.",
        rationale="The local transform preserves lineage without remote calls.",
        forbidden_approaches=[],
        budget={"max_api_calls": 0, "max_gpu_jobs": 0, "max_runtime_seconds": 60},
        event_content="Local transform kept source_id mapping.",
        test_usage={"api_calls": 0, "gpu_jobs": 0, "runtime_seconds": 8},
        method_evidence_type="algorithm_trace",
        method_evidence_content=(
            "Algorithm_trace evidence: mapping and lineage preserved for every source row. "
            "Cost_report: api_calls=0, gpu_jobs=0, runtime_seconds=8."
        ),
        expected_hints=set(),
        clean=True,
    ),
]


def run_matrix(temp_root: Path) -> dict[str, Any]:
    temp_root = temp_root.resolve()
    db_path = temp_root / "ledger-risk-hints-matrix.db"
    data_dir = temp_root / "data"

    os.environ["PROOFFLOW_DB_PATH"] = str(db_path)
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)
    os.environ["PROOFFLOW_BASE_URL"] = "http://testserver"

    from fastapi.testclient import TestClient
    from proofflow.main import app
    from proofflow_mcp import server as mcp_server

    with TestClient(app) as test_client:
        patched_http = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda req: _sync_to_httpx_response(test_client, req)
            ),
            base_url="http://testserver",
        )
        mcp_server._client._http = patched_http
        mcp_server._client._base_url = "http://testserver"

        results = asyncio.run(_run_scenarios(temp_root))
        asyncio.run(patched_http.aclose())

    return {
        "db_path": str(db_path),
        "data_dir": str(data_dir),
        "scenario_count": len(SCENARIOS),
        "results": results,
    }


def _sync_to_httpx_response(test_client: Any, request: httpx.Request) -> httpx.Response:
    method = request.method.lower()
    parsed = urlparse(str(request.url))
    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    kwargs: dict[str, Any] = {}
    if request.content:
        kwargs["content"] = request.content
        kwargs["headers"] = dict(request.headers)

    response = getattr(test_client, method)(path, **kwargs)
    return httpx.Response(
        status_code=response.status_code,
        headers=dict(response.headers),
        content=response.content,
    )


async def _run_scenarios(temp_root: Path) -> list[dict[str, Any]]:
    health = await _call("proofflow_health", {})
    _assert_contains(health, "ProofFlow is running")
    print("  [PASS] proofflow_health")

    results: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        print(f"\nScenario: {scenario.title}")
        repo = _init_repo(temp_root / scenario.slug, scenario)
        result = await _run_scenario(repo, scenario)
        results.append(result)

        missing = result["missing_hints"]
        unexpected = result["unexpected_hints"]
        print(f"  expected: {', '.join(sorted(scenario.expected_hints)) or 'none'}")
        print(f"  actual:   {', '.join(result['actual_hints']) or 'none'}")
        print(f"  missing:  {', '.join(missing) or 'none'}")
        print(f"  extra:    {', '.join(unexpected) or 'none'}")

        if missing:
            raise AssertionError(f"{scenario.slug} missing hints: {', '.join(missing)}")
        if scenario.clean and unexpected:
            raise AssertionError(f"{scenario.slug} clean scenario emitted hints: {', '.join(unexpected)}")

    return results


async def _run_scenario(repo: Path, scenario: Scenario) -> dict[str, Any]:
    start = await _call(
        "proofflow_start_work_contract",
        {
            "objective": scenario.objective,
            "repo_path": str(repo),
            "allowed_scope": [scenario.filename],
            "required_tests": [scenario.test_command],
            "done_criteria": [scenario.purpose],
            "evidence_requirements": [
                "git_diff",
                "test_output",
                "algorithm_decision",
                "cost_budget",
            ],
            "algorithm_requirements": scenario.algorithm_requirements,
            "cost_budget": scenario.cost_budget_contract,
        },
    )
    case_id = _extract_value(start, "Case ID")

    await _call(
        "proofflow_capture_snapshot",
        {
            "case_id": case_id,
            "repo_path": str(repo),
            "phase": "start",
            "base_ref": "HEAD",
            "include_untracked": True,
        },
    )
    await _call(
        "proofflow_record_algorithm_decision",
        {
            "case_id": case_id,
            "summary": scenario.decision_summary,
            "chosen_approach": scenario.chosen_approach,
            "rationale": scenario.rationale,
            "alternatives_considered": ["Use the contract-first evidence route"],
            "invariants": ["Keep outputs reviewable"],
            "forbidden_approaches": scenario.forbidden_approaches,
        },
    )
    await _call(
        "proofflow_record_cost_budget",
        {
            "case_id": case_id,
            "summary": f"{scenario.title} budget",
            "budget": scenario.budget,
            "expected_operations": ["local transform", "local test evidence"],
            "limits": ["Stay within the contract budget"],
        },
    )

    (repo / scenario.filename).write_text(scenario.final_content, encoding="utf-8")
    await _call(
        "proofflow_record_event",
        {
            "case_id": case_id,
            "event_type": "implementation",
            "summary": scenario.title,
            "content": scenario.event_content,
            "metadata": {"scenario": scenario.slug, "file": scenario.filename},
        },
    )
    test_evidence = await _call(
        "proofflow_record_evidence",
        {
            "case_id": case_id,
            "evidence_type": "test_output",
            "content": f"COMMAND: {scenario.test_command}\nRETURN_CODE: 0\n1 passed\n",
            "source_ref": "ledger_risk_hints_dogfood_matrix.py",
            "metadata": {
                "command": scenario.test_command,
                "returncode": 0,
                "usage": scenario.test_usage,
            },
        },
    )
    evidence_ids = [_extract_value(test_evidence, "Evidence")]
    if scenario.method_evidence_type and scenario.method_evidence_content:
        method_evidence = await _call(
            "proofflow_record_evidence",
            {
                "case_id": case_id,
                "evidence_type": scenario.method_evidence_type,
                "content": scenario.method_evidence_content,
                "source_ref": "ledger_risk_hints_dogfood_matrix.py",
                "metadata": {"scenario": scenario.slug},
            },
        )
        evidence_ids.append(_extract_value(method_evidence, "Evidence"))

    await _call(
        "proofflow_record_claim",
        {
            "case_id": case_id,
            "claim_text": f"{scenario.title} scenario reached recorded test evidence.",
            "severity": "info",
            "evidence_ids": evidence_ids,
        },
    )
    await _call(
        "proofflow_capture_snapshot",
        {
            "case_id": case_id,
            "repo_path": str(repo),
            "phase": "final",
            "base_ref": "HEAD",
            "include_untracked": True,
        },
    )

    evaluation = await _call("proofflow_evaluate_contract", {"case_id": case_id})
    _assert_contains(evaluation, "Status: ready_for_review")
    actual_hints = _parse_hint_codes(evaluation)
    packet = await _call("proofflow_export_packet", {"case_id": case_id})
    _assert_contains(packet, "Proof Packet exported")
    _assert_contains(packet, "## Done Criteria Evaluation")

    expected_hints = set(scenario.expected_hints)
    actual_hint_set = set(actual_hints)
    return {
        "slug": scenario.slug,
        "title": scenario.title,
        "case_id": case_id,
        "expected_hints": sorted(expected_hints),
        "actual_hints": actual_hints,
        "missing_hints": sorted(expected_hints - actual_hint_set),
        "unexpected_hints": sorted(actual_hint_set - expected_hints),
        "clean": scenario.clean,
    }


async def _call(name: str, args: dict[str, Any]) -> str:
    from proofflow_mcp.server import call_tool

    result = await call_tool(name, args)
    text = result[0].text
    if text.startswith("Error:"):
        raise RuntimeError(text)
    return text


def _parse_hint_codes(evaluation_output: str) -> list[str]:
    codes: list[str] = []
    for line in evaluation_output.splitlines():
        match = re.match(r"\s+- \[[^\]]+\] ([A-Za-z0-9_]+):", line)
        if match:
            codes.append(match.group(1))
    return sorted(codes)


def _extract_value(text: str, label: str) -> str:
    prefix = f"{label}:"
    for line in text.splitlines():
        if prefix in line:
            value = line.split(prefix, 1)[1].strip()
            if value:
                return value
    raise RuntimeError(f"could not find {label!r} in output:\n{text}")


def _assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"expected {expected!r} in output:\n{text}")


def _init_repo(repo: Path, scenario: Scenario) -> Path:
    if shutil.which("git") is None:
        raise RuntimeError("git executable was not found")

    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "ledger-risk-hints@example.test")
    _git(repo, "config", "user.name", "Ledger Risk Hints Matrix")
    (repo / scenario.filename).write_text(scenario.baseline_content, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def _print_summary(results: list[dict[str, Any]]) -> None:
    print("\nMatrix summary")
    for result in results:
        print(
            "  - "
            f"{result['slug']}: expected={result['expected_hints'] or ['none']} "
            f"actual={result['actual_hints'] or ['none']} "
            f"missing={result['missing_hints'] or ['none']} "
            f"extra={result['unexpected_hints'] or ['none']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ledger Risk Hints dogfood matrix")
    parser.add_argument("--cleanup", action="store_true", help="Remove temp files on success")
    args = parser.parse_args()

    temp_root = Path(tempfile.mkdtemp(prefix="proofflow-ledger-risk-hints-matrix-"))
    print("Ledger Risk Hints Dogfood Matrix")
    print(f"  temp_root: {temp_root}")
    print()

    try:
        output = run_matrix(temp_root)
        _print_summary(output["results"])
        print()
        print("All Ledger Risk Hints matrix checks passed.")
        print(f"  Scenarios: {output['scenario_count']}")
        if args.cleanup:
            shutil.rmtree(temp_root, ignore_errors=True)
            print(f"  Cleaned up: {temp_root}")
        else:
            print(f"  Temp files preserved at: {temp_root}")
    except Exception as error:
        print(f"\nDOGFOOD MATRIX FAILED: {error}")
        print(f"  Temp files preserved at: {temp_root}")
        sys.exit(1)


if __name__ == "__main__":
    main()
