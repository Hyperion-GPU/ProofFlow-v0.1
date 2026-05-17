# ProofFlow v0.1.8 Closure Checklist

## Goal

Close the v0.1.8 release preparation with release-level evidence that the Agent
Work Ledger story is complete enough to publish:

- Work Contract first.
- Snapshot-backed repository state.
- Evidence-backed Claims.
- Done criteria evaluation.
- Proof Packet export.

## Current Release

| Field | Value |
| --- | --- |
| Target version | v0.1.8 |
| Status | release closure ready after this docs-only PR |
| Branch | `Hyperion/v0-1-8-release-closure` |
| Validated ref | `bf955d6d3e3ca260a4687e7c90bacdfd5e2ff213` |
| Scope | Agent Work Ledger adoption, packaging, validation, and release decision |

## Release Notes Checklist

- [x] Release notes exist:
  [`docs/releases/V0_1_8_RELEASE_NOTES.md`](V0_1_8_RELEASE_NOTES.md).
- [x] Release notes explain the main product narrative:
  Agent Work Ledger for AI coding.
- [x] Release notes include the main flow:
  Work Contract -> Snapshot -> Evidence -> Claim -> Evaluation -> Packet.
- [x] Release notes list hard rules:
  evidence-bound Claims, final snapshot before finish, risk-aware finish state,
  and snapshot diff/hash in Proof Packets.
- [x] Release notes list intentionally excluded scope.
- [x] README release pointers are ready for the `v0.1.8` tag.

## Automated Validation Checklist

| Gate | Status | Evidence |
| --- | --- | --- |
| Ledger MCP smoke | PASS | `python scripts\ledger_mcp_smoke.py --cleanup`; case `16042774-dec4-4df6-878b-f8e52e3246e1`; evaluation `ready_for_review`; temp dir cleaned up. |
| Backend selected tests | PASS | `python -m pytest backend/tests/test_agent_work_ledger.py backend/tests/test_reports_export.py backend/tests/test_case_packet_api.py backend/tests/test_cases_api.py backend/tests/test_artifacts_api.py backend/tests/test_search_api.py backend/tests/test_agentguard_review.py`; `38 passed`. |
| MCP tests | PASS | From `mcp-server`: `python -m pytest tests/ -v`; `40 passed`. |
| Frontend tests | PASS | From `frontend`: `npm test`; 7 test files and 29 tests passed. |
| Frontend build | PASS | From `frontend`: `npm run build`; `tsc -b && vite build` completed. |
| Python compile check | PASS | `python -m compileall backend\proofflow mcp-server\src\proofflow_mcp`. |
| Whitespace check | PASS | `git diff --check`; no blocking whitespace errors. |
| GitHub CI | PASS | PRs #107 through #113 merged with green required checks recorded during release preparation. |

## Ledger Documentation Checklist

- [x] Architecture and adoption guide:
  [`docs/agent_work_ledger.md`](../agent_work_ledger.md).
- [x] Five-minute MCP quickstart:
  [`docs/ledger_quickstart_mcp.md`](../ledger_quickstart_mcp.md).
- [x] Public-safe dogfood packet:
  [`docs/examples/proof_packet_agent_work_ledger_dogfood.md`](../examples/proof_packet_agent_work_ledger_dogfood.md).
- [x] PR comment template:
  [`docs/examples/pr_comment_agent_work_ledger.md`](../examples/pr_comment_agent_work_ledger.md).
- [x] Maintainer plugin guidance points complex tasks through the Ledger flow:
  `plugins/proofflow-maintainer/skills/proofflow-maintainer/SKILL.md`.

## Ledger Dogfood Checklist

- [x] Start a work contract.
- [x] Capture start and final snapshots.
- [x] Record command or test output as Evidence.
- [x] Bind Claims to Evidence.
- [x] Evaluate done criteria.
- [x] Finish the Ledger.
- [x] Export a Proof Packet.

## Hard-Rule Checklist

| Rule | Status | Evidence |
| --- | --- | --- |
| Claim must bind Evidence | PASS | Empty `evidence_ids` returns HTTP 422. |
| Final snapshot required before finish | PASS | Finish without final snapshot returns HTTP 400. |
| Non-ready evaluation cannot look like clean success | PASS | Finish after non-ready evaluation stores `finished_with_risks`. |
| Missing required test evidence is detected | PASS | Evaluator returns `needs_tests`. |
| Scope violations are detected | PASS | Evaluator returns `scope_violation`. |
| Open medium/high risk requires acceptance | PASS | Evaluator returns `risk_acceptance_required` without an accepted Decision. |
| Snapshot diff/hash appears in packet | PASS | Proof Packet includes snapshot diff and hash details. |

## Known Gaps

- No dedicated Ledger database table. The Ledger intentionally reuses the
  existing Evidence Graph for v0.1.8.
- No VS Code Ledger panel, standalone Ledger CLI, or GitHub Action Ledger
  comment automation yet.
- No hosted service, cloud sync, telemetry, or remote review backend.

## Closure Result

v0.1.8 is ready to tag after the final release-notes PR is reviewed and merged.
