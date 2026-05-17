# Proof Packet Example: Agent Work Ledger Dogfood

> Public-safe summary of a real Agent Work Ledger dogfood run after the Ledger
> workflow landed. IDs and paths are representative, but the statuses and hard
> rule outcomes mirror the verified local run.

## Case Summary

- Case ID: `df90faf6-98e3-4dcc-8d53-edcc85ba5e66`
- Title: `Agent work ledger: End-to-end dogfood Agent Work Ledger after implementation`
- Workflow type: `agent_work_ledger`
- Status: `finished`
- Evaluation status: `ready_for_review`
- Trust boundary: localhost backend, local repository, local MCP client

## Work Contract

- Objective: End-to-end dogfood Agent Work Ledger after implementation.
- Repository path: `D:\ProofFlow v0.1`
- Allowed scope: `README.md`, `backend`, `mcp-server`, `plugins`, `docs`, `.codex`
- Forbidden actions: delete user data, remote sync, cloud telemetry, Docker scope expansion
- Required tests:
  - `python -m pytest backend/tests/test_agent_work_ledger.py backend/tests/test_reports_export.py backend/tests/test_case_packet_api.py`
  - `python -m pytest tests/ -v`
- Evidence requirements: `git_diff`, `test_output`
- Done criteria:
  - Ledger Case can be created through real HTTP.
  - Snapshot, events, test evidence, claim binding, evaluation, finish, and export all complete.
  - Evaluator returns `ready_for_review`.

## Ledger Timeline

| Step | Event | Evidence |
| --- | --- | --- |
| 1 | Started real Agent Work Ledger dogfood flow | Live backend at `http://127.0.0.1:8787` responded to MCP client calls. |
| 2 | Captured start snapshot | `ledger-start-diff.patch`, HEAD SHA, changed files, diff hash. |
| 3 | Recorded required test outputs | Backend and MCP test output Artifacts stored as `test_output`. |
| 4 | Bound Claim to Evidence | Claim: required backend and MCP Ledger tests passed. |
| 5 | Captured final snapshot | `ledger-final-diff.patch` with same HEAD SHA and diff hash. |
| 6 | Evaluated contract | `ready_for_review`; no failed criteria. |
| 7 | Exported Proof Packet | Packet contained contract, timeline, snapshots, claims, evidence, and evaluation. |

## Snapshots

| Phase | Changed files | Diff hash | Notes |
| --- | ---: | --- | --- |
| start | 17 | `340117ed719c594ef323b746445e3b67c5fa1c2fd64a139b4efb4e8ee782f5b1` | Captured implementation, MCP, tests, docs, and `.codex/config.toml`. |
| final | 17 | `340117ed719c594ef323b746445e3b67c5fa1c2fd64a139b4efb4e8ee782f5b1` | Matched start snapshot because dogfood did not modify files during execution. |

## Claims & Evidence

### Claim: Required backend and MCP Ledger tests passed during real dogfood.

- Severity: `info`
- Status: `open`
- Evidence:
  - Backend Ledger/report/packet tests returned code `0`.
  - MCP tool tests returned code `0`.
  - Test output was stored as `test_output` Evidence and bound to the Claim.

## Done Criteria Evaluation

| Check | Result |
| --- | --- |
| Required tests | passed |
| Evidence requirements | passed |
| Allowed scope | passed |
| Open risks | passed |
| Final status | `ready_for_review` |

## Hard Rule Dogfood

Additional negative scenarios verified the Ledger evaluator and finish rules:

| Scenario | Observed result |
| --- | --- |
| Missing required test evidence | `needs_tests` |
| Changed files outside allowed scope | `scope_violation` |
| Claim with empty `evidence_ids` | HTTP 422 |
| Open medium risk without accepted Decision | `risk_acceptance_required` |
| Finish after non-ready evaluation | `finished_with_risks` |
| Finish without final snapshot | HTTP 400 |

The dogfood run also found and fixed a dotfile scope bug: `.codex/config.toml`
must remain `.codex/config.toml`, not `codex/config.toml`.

## Remaining Risks

- This is a public-safe example, not the full generated packet with every
  evidence quote.
- Maintainers should still inspect the full Proof Packet and CI output before
  accepting high-risk work.
