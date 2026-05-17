# ProofFlow v0.1.8 Release Decision

Date: 2026-05-18
Branch: `Hyperion/v0-1-8-release-closure`
Validated ref: `bf955d6d3e3ca260a4687e7c90bacdfd5e2ff213`
Scope: Agent Work Ledger release closure

## Decision

SHIP release preparation for v0.1.8.

v0.1.8 is ready to move from release draft to final release notes after this
docs-only closure PR is merged. Do not create the `v0.1.8` tag or GitHub
Release in this PR. The next release PR should convert
[`docs/releases/V0_1_8_RELEASE_DRAFT.md`](V0_1_8_RELEASE_DRAFT.md) into the
final GitHub Release body and update public README release pointers.

## Evidence

| Gate | Result | Evidence / notes |
| --- | --- | --- |
| Release draft | PASS | `docs/releases/V0_1_8_RELEASE_DRAFT.md` covers highlights, main flow, dogfood evidence, validation, breaking changes, and intentionally excluded scope. |
| Ledger MCP smoke | PASS | `python scripts\ledger_mcp_smoke.py --cleanup` completed with evaluation `ready_for_review`; case `16042774-dec4-4df6-878b-f8e52e3246e1`; temp dir cleaned up. |
| Backend selected tests | PASS | `python -m pytest backend/tests/test_agent_work_ledger.py backend/tests/test_reports_export.py backend/tests/test_case_packet_api.py backend/tests/test_cases_api.py backend/tests/test_artifacts_api.py backend/tests/test_search_api.py backend/tests/test_agentguard_review.py`; `38 passed`. |
| MCP tests | PASS | From `mcp-server`: `python -m pytest tests/ -v`; `40 passed`. |
| Frontend tests | PASS | From `frontend`: `npm test`; 7 test files and 29 tests passed. |
| Frontend build | PASS | From `frontend`: `npm run build`; `tsc -b && vite build` completed. |
| Compile check | PASS | `python -m compileall backend\proofflow mcp-server\src\proofflow_mcp` completed. |
| Whitespace check | PASS | `git diff --check` completed without blocking errors. |
| CI | PASS | GitHub CI for PRs #107 through #113 was green before merge during the v0.1.8 preparation chain. |
| Ledger docs | PASS | Architecture guide, MCP quickstart, dogfood packet, and PR comment template exist under `docs/`. |
| Ledger hard rules | PASS | Dogfood covered missing tests, scope violations, claim-without-evidence rejection, risk acceptance requirements, non-ready finish state, and missing final snapshot rejection. |

## Release Body Cleanup

The final GitHub Release should use the release draft as source material and
remove draft-only wording:

- Title: `ProofFlow v0.1.8`.
- Status: release.
- Keep the main flow: Work Contract -> Snapshot -> Evidence -> Claim ->
  Evaluation -> Packet.
- Keep the hard-rule table because it explains what makes the Ledger verifiable.
- Keep the intentionally-not-included section to preserve v0.1 scope.

This task did not create the tag or GitHub Release.

## Intentionally Not Included

- No dedicated Ledger database table.
- No hosted service, cloud sync, telemetry, or remote review backend.
- No merge blocking.
- No VS Code Ledger panel.
- No standalone Ledger CLI command.
- No GitHub Action Ledger comment automation.
- No README latest-release pointer update in this closure PR.

## Remaining Risks

- README release pointers still need final publish cleanup.
- The Ledger is proven through backend, MCP, smoke, and documentation flows, but
  there is no first-class visual Ledger UI yet.
- CI evidence is release-chain evidence from merged PRs, not a new tag build.

## Next Version Candidates

- VS Code Ledger panel.
- Standalone `proofflow ledger` CLI.
- GitHub Action that posts Ledger evaluation and Proof Packet links to PRs.
- Richer Ledger UI for browsing Work Contracts, snapshots, Claims, Evidence,
  and evaluations.
- README and localized docs polish for the public v0.1.8 announcement.
