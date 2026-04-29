# Checkpoint A Dogfood Readiness Report

## Status

Checkpoint A completed on latest `main`.

- Checked branch: `main`.
- Checked commit: `46fca1f docs: add policy gate integration checkpoints`.
- PR #26 is present on latest `main`:
  <https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/26>.
- No P0/P1 blocker was found.
- This document is docs-only evidence capture for readiness review.
- "Readiness" here means docs/design review readiness only.
- This document does not authorize runtime policy gate integration.
- This document does not authorize `rc2` or any release/tag action.

## Scope Guard

Out of scope for this evidence record:

- Runtime policy gate enforcement.
- Live restore.
- Destructive restore.
- Backup/restore behavior changes.
- Database migrations.
- API endpoint changes.
- UI behavior changes.
- Backend/frontend runtime changes.
- Release/tag changes.
- `rc2`.

## Commands Run

| Command | Result |
| --- | --- |
| `git checkout main` / `git pull --ff-only origin main` | Latest `main` confirmed. |
| `git diff --check` | Passed. |
| `git tag --points-at HEAD` | No output. |
| `python -m pytest tests/test_policy_gate_service.py` | 15 passed; local pytest cache/temp cleanup permission warning only; exit code 0. |
| `python -m pytest` | 123 passed, 3 skipped; same local pytest cache/temp cleanup permission warning only; exit code 0. |
| `npm run test` | 6 files / 21 tests passed. |
| `npm run build` | Passed. |
| `python .\scripts\rc_api_smoke.py --cleanup` | Passed; created and cleaned temp DB/data; covered LocalProof case/actions, AgentGuard case, and Proof Packet export. |
| `python .\scripts\backup_restore_api_smoke.py --cleanup` | Passed; covered backup preview/create/list/detail/verify, restore preview, restore-to-new-location, and verified live DB/data sentinel was not overwritten. |
| Final `git status --short` | Only `.playwright-mcp/` and `项目总结.txt` were untracked. |
| Final `git diff --name-only` | No output. |

The pytest cache/temp cleanup warning is classified as an environment issue
because both pytest commands exited 0.

## Dogfood Evidence By Invariant

| Area | Evidence observed | Invariant signal | Result |
| --- | --- | --- | --- |
| Case | `rc_api_smoke.py` created a LocalProof case and an AgentGuard case. | No Case, no workflow. | Passed. |
| Artifact | LocalProof scan and AgentGuard diff review produced traceable inputs; backup smoke treated archive, manifest, and restored files as inspectable objects. | No Source, no Artifact. | Passed. |
| Claim / Evidence | AgentGuard packet checks confirmed claims and evidence are non-empty; backup verification remained a trusted-backup precondition. | No Evidence, no trusted Claim. | Passed. |
| Action preview | LocalProof suggest-actions followed approve/execute/undo; backup/restore smoke previewed before create and restore-to-new-location. | No Preview, no Action. | Passed. |
| Undo / rollback | LocalProof move/mkdir undo passed; changed-file undo was rejected, showing the hash/rollback guard still works. | No Undo, no destructive Action. | Passed. |
| Code workflow tests | Backend, frontend, and targeted policy tests passed. | No Test, no accepted code workflow. | Passed. |
| Decision / Report | AgentGuard packet and report export succeeded; Proof Packet did not leak the sensitive untracked marker. | Decisions and reports remain evidence-backed workflow outputs. | Passed. |
| Backup / restore safety | Restore only wrote to a new inspection location; live DB/data sentinel was not overwritten; no live or destructive restore was introduced. | No Verify, no trusted Backup; No Preview, no Restore; No Restore to live DB in foundation phase. | Passed. |
| Policy gate visibility | Policy targeted tests preserved fail-closed aggregation semantics; the main workflow smoke was not prematurely blocked by runtime policy gate enforcement. | Policy foundation remains visible without runtime enforcement overreach. | Passed. |
| Agent transparency / tampering model | Docs review produced no findings; transparency and tampering material remains an auditability foundation. | ProofFlow remains an evidence dashboard, not a generic chat app or file manager. | Passed. |

## Failure Classification

| Class | Finding |
| --- | --- |
| Environment issue | Pytest cache/temp cleanup permission warning; all pytest commands exited 0. |
| Docs issue | None. |
| Workflow regression | None. |
| Possible P0/P1 blocker | None. |

## Source Map For Future Checkpoint B/C Review

| Foundation area | Existing source/doc/test/script anchors | Why it matters | Notes / gaps |
| --- | --- | --- | --- |
| Managed backup / restore | `docs/managed_backup_restore.md`; `backend/proofflow/services/backup_service.py`; `backend/proofflow/services/restore_service.py`; `backend/proofflow/routers/backups.py`; `backend/proofflow/routers/restore.py`; `backend/tests/test_backup_api.py`; `backend/tests/test_backup_service.py`; `backend/tests/test_restore_api.py`; `backend/tests/test_restore_service.py`; `backend/tests/test_backup_restore_api_smoke.py`; `backend/tests/test_managed_backup_restore_contract.py`; `scripts/backup_restore_api_smoke.py`; `frontend/src/pages/ManagedBackupRestore.tsx`; `frontend/src/pages/ManagedBackupRestore.test.tsx`. | Defines and verifies manifest, verify, preview, restore-to-new-location, overwrite rejection, and live-root protection. | Live/destructive restore remains future-only and was not exercised. |
| Agent intermediary tampering threat model | `docs/threat_models/AGENT_INTERMEDIARY_TAMPERING.md`. | Defines why agent/router/tool output is proposal material until local validation, evidence capture, preview, and decision. | Design gate only; no runtime intermediary enforcement implementation confirmed in this pass. |
| Agent transparency log foundation | `docs/agent_transparency_log.md`. | Defines future audit events such as `policy_gate_triggered`, `preview_created`, `decision_recorded`, and proof packet export alignment. | Foundation document only; no transparency log service/table implementation confirmed in this pass. |
| High-risk action policy gate design | `docs/high_risk_action_policy_gates.md`. | Defines future policy outcomes and metadata expectations for local-first high-risk action review. | Design foundation only; no runtime policy gate wiring. |
| Policy gate result foundation | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py`. | Provides local policy result types, categories, severity, serialization, and helper semantics. | Helper foundation only; not wired into action execution. |
| Policy gate evaluation summary | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py`. | Aggregates multiple policy results into one summary for future evidence or enforcement-boundary review. | Summary helper only; no runtime enforcement boundary. |
| Fail-closed aggregation semantics | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py`; `docs/policy-gate-integration-checkpoints.md`; `CHANGELOG.md`. | Preserves restrictive aggregation: result-derived `block` / `fail_closed` cannot be downgraded by caller-provided `final_outcome`. | Runtime boundary proof remains future Checkpoint C/D work. |
| LocalProof main workflow smoke | `scripts/rc_api_smoke.py`; `backend/proofflow/routers/localproof.py`; `backend/proofflow/services/file_scanner.py`; `backend/proofflow/services/action_suggestion_service.py`; `backend/tests/test_localproof_scan.py`; `backend/tests/test_localproof_suggest_actions.py`; `frontend/src/pages/LocalProof.tsx`; `frontend/src/pages/LocalProof.test.tsx`; `docs/V0_1_DOGFOOD.md`; `docs/V0_1_RC_CHECKLIST.md`. | Confirms case-backed scan, artifact indexing, suggest-actions, preview, approval, execution, undo, and allowed-root metadata. | Manual UI dogfood can continue separately; this report used existing automated smoke/tests. |
| AgentGuard / Proof Packet export | `scripts/rc_api_smoke.py`; `backend/proofflow/routers/agentguard.py`; `backend/proofflow/services/review_service.py`; `backend/proofflow/routers/reports.py`; `backend/proofflow/services/report_service.py`; `backend/tests/test_agentguard_review.py`; `backend/tests/test_case_packet_api.py`; `backend/tests/test_reports_export.py`; `docs/code_review.md`; `docs/proof_packet.md`; `frontend/src/pages/AgentGuard.test.tsx`; `frontend/src/pages/CaseDetail.test.tsx`. | Confirms evidence-backed claims, test metadata, packet retrieval, report export, and sensitive untracked content omission. | No new report format or export behavior was added. |
| Frontend tests/build | `frontend/package.json`; `frontend/vite.config.ts`; `frontend/src/pages/ManagedBackupRestore.test.tsx`; `frontend/src/pages/LocalProof.test.tsx`; `frontend/src/pages/AgentGuard.test.tsx`; `frontend/src/pages/CaseDetail.test.tsx`; `docs/V0_1_DOGFOOD.md`; `docs/V0_1_RC_CHECKLIST.md`. | Confirms the documented `npm run test` and `npm run build` validation path for visible workflows. | No UI behavior was changed in this evidence record. |

## Readiness Conclusion

Checkpoint A passed. No P0/P1 blocker was found.

The main ProofFlow workflow was not distorted by the post-RC1 safety
foundation: Case, Artifact, Claim, Evidence, Action, Decision, Report,
backup/restore, policy visibility, and transparency/tampering concepts remained
bounded and evidence-oriented.

Future work may proceed only to docs/design review readiness, not runtime
enforcement. The recommended next step is Checkpoint C policy gate input/output
contract review, still docs/design-only, and only after owner review of this
evidence.

## Release / Tag Safety Note

`v0.1.0-rc1` remains untouched. No `rc2` was cut. `HEAD` should not point at a
release tag for this evidence record.
