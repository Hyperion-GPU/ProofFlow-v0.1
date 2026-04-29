# Policy Gate Integration Checkpoints

## Status / Scope

This is a post-RC1 docs-only planning and verification artifact. It describes
the checkpoint path from the existing policy gate foundations toward possible
future runtime integration.

This document does not implement runtime policy gate enforcement, change
backend or frontend behavior, add API endpoints, add database migrations, or
authorize release work.

`v0.1.0-rc1` is immutable for this checkpoint. Do not move, rebuild, delete,
replace, recreate, or retag `v0.1.0-rc1`. This document does not authorize
`v0.1.0-rc2`; only the project owner can decide that for a real P0/P1 blocker.

For the current docs task, only Checkpoint A and Checkpoint B documentation work
is in scope. Later checkpoints may be described here, but they are not
implemented by this change.

## Existing Safety Foundation

Latest post-RC1 `main` has already landed the safety foundation chain below.
These items are foundations and guardrails, not runtime policy enforcement:

| Foundation | Current evidence / source map | Runtime status |
| --- | --- | --- |
| Managed Backup / Restore backend and thin UI | `docs/managed_backup_restore.md`, `backend/proofflow/services/backup_service.py`, `backend/proofflow/services/restore_service.py`, `frontend/src/pages/ManagedBackupRestore.tsx` | Inspection and restore-to-new-location only; no live restore. |
| Agent intermediary tampering threat model | `docs/threat_models/AGENT_INTERMEDIARY_TAMPERING.md` | Design and threat model only. |
| Agent transparency log foundation | `docs/agent_transparency_log.md` | Future event model only. |
| High-risk action policy gate design | `docs/high_risk_action_policy_gates.md` | Design foundation only; no runtime gate wiring. |
| Policy gate result foundation | `backend/proofflow/services/policy_gate_service.py`, `backend/tests/test_policy_gate_service.py` | Local result types and helpers only. |
| Policy gate evaluation summary | `backend/proofflow/services/policy_gate_service.py`, `backend/tests/test_policy_gate_service.py` | Local aggregation summary only. |
| Restrictive outcome bugfix for fail-closed aggregation semantics | `backend/proofflow/services/policy_gate_service.py`, `backend/tests/test_policy_gate_service.py`, `CHANGELOG.md` | Result-derived restrictive outcomes cannot be downgraded by caller input. |

The release boundary remains separate from post-RC1 `main`. Use
`docs/releases/V0_1_0_RC1_CLOSURE_DECISION.md` and
`docs/V0_1_RC_CHECKLIST.md` when checking RC1 release history.

## Non-Negotiable Invariants

Policy gate integration must preserve the ProofFlow product invariants:

- No Case, no workflow.
- No Evidence, no trusted Claim.
- No Preview, no Action.
- No Undo, no destructive Action.
- No Test, no accepted code workflow.
- No Source, no Artifact.

Managed backup and restore work must also preserve the foundation restore
invariants from `docs/managed_backup_restore.md`:

- No Manifest, no Backup.
- No Verify, no trusted Backup.
- No Preview, no Restore.
- No Pre-restore Backup, no destructive Restore.
- No Hash Match, no Restore.
- No Source Version, no Restore Trust.
- No Restore to live DB in foundation phase.

## Fail-Closed Semantics

Future integration must preserve restrictive policy aggregation:

- Result-derived `block` / `fail_closed` outcomes cannot be downgraded by a
  caller-provided `final_outcome`.
- Aggregation should select the most restrictive outcome.
- Missing, malformed, ambiguous, or tampered intermediary state must not produce
  permissive outcomes.
- Empty policy evaluation defaults to `fail_closed`.
- Any runtime wiring must prove that restrictive results remain restrictive at
  the enforcement boundary, not only inside helper tests.

Runtime enforcement is not allowed until the enforcement boundary can show:

- the exact policy input that was evaluated,
- the exact preview or action that the operator saw,
- the final policy evaluation result,
- the operator Decision when one is required,
- the execution or non-execution result,
- and the Evidence or transparency log records that connect those objects.

## Integration Checkpoint Table

| Checkpoint | Purpose | Required evidence | Allowed work | Explicitly forbidden work | Verification commands / acceptance criteria | Exit condition |
| --- | --- | --- | --- | --- | --- | --- |
| A. Dogfood latest main without new runtime wiring | Prove the main ProofFlow workflow still behaves like a local evidence dashboard before adding policy enforcement pressure. | Dogfood notes, screenshots or Proof Packet output, command results, any observed workflow distortion. | Run local demo, inspect existing Case / Artifact / Claim / Evidence / Action / Decision / Report flow, record gaps. | New runtime policy wiring, UI enforcement changes, restore behavior changes, DB migration, endpoint changes, release/tag changes. | Use existing dogfood guide and local commands. Acceptance: no policy infrastructure blocks or rewrites the normal workflow. | Latest `main` is understood and any workflow distortion is filed before implementation planning. |
| B. Documentation alignment and source map | Make the foundations auditable before any code integration starts. | Source map linking policy design, transparency log, threat model, backup/restore, fail-closed tests, and release boundary docs. | Docs-only updates, README or docs-index link, checklist refinement. | Runtime code changes, API/schema/UI changes, release/tag movement. | `git diff --check`; docs link review; diff remains docs-only. | Future contributors can find the checkpoints and source evidence without guessing. |
| C. Policy gate input/output contract review | Freeze the minimum contract for policy inputs, outputs, Evidence links, redaction, and operator-facing reasons. | Contract notes with example input/output shapes, redaction expectations, and failure-mode mapping. | Design review, non-runtime test planning, fixture planning. | Endpoint changes, DB migrations, runtime enforcement, UI behavior changes. | Targeted policy tests are identified or added only in a later approved implementation PR. Acceptance: contract covers malformed, missing, and tampered input. | Owner or maintainer accepts the contract as ready for implementation planning. |
| D. Enforcement boundary design review | Decide where policy evaluation may block, warn, or require a Decision without bypassing existing backend safety checks. | Boundary diagram or text map from proposal to preview to Decision to execution, including Evidence and transparency event references. | Docs and design review only unless a separate implementation milestone is approved. | Wiring policy checks into action execution, restore execution, AgentGuard, LocalProof, or frontend controls. | Acceptance: every enforcement point preserves "No Preview, no Action" and does not replace backend hard safety checks. | A specific future implementation boundary is approved and scoped. |
| E. Dry-run-only policy evaluation plan | Plan how policy evaluation can be observed without enforcing outcomes or changing user behavior. | Dry-run plan, expected log/Evidence shape, dogfood comparison checklist, rollback plan. | Future dry-run design only; possible later implementation must be separately approved. | Blocking runtime actions, UI enforcement, destructive restore, live restore, schema changes unless explicitly approved later. | Acceptance: dry-run cannot block, auto-approve, or mutate existing workflows; restrictive outcomes remain visible as evidence. | Dry-run behavior is considered safe enough for a separate implementation PR. |
| F. Runtime integration readiness decision | Decide whether runtime enforcement is allowed at all. | Completed A-E evidence, passing tests, dogfood notes, owner/maintainer signoff, unresolved-risk list. | Decision record and implementation scope proposal. | Starting implementation without signoff, broad feature expansion, release/tag work. | Acceptance: fail-closed behavior is proven at the proposed boundary and no existing invariant is weakened. | Owner or maintainer explicitly approves a scoped runtime integration PR. |
| G. Owner decision gate for any rc2 or blocker-driven release action | Keep release movement separate from routine hardening. | P0/P1 blocker evidence, impacted users/data, reproduction, fix validation, release artifact comparison. | Owner decision, release checklist preparation after approval. | Moving, deleting, rebuilding, replacing, or retagging `v0.1.0-rc1`; cutting `rc2` without owner decision. | `git tag --points-at HEAD`; release checklist; artifact/hash review if a release is approved. | Owner explicitly decides whether a release action is justified. |

## Dogfood Checklist

Use this checklist during Checkpoint A to prove hardening work has not bent the
main workflow around policy infrastructure:

- Create or select a Case before starting work.
- Add or inspect Artifact source information, including source path or source
  command where available.
- Review Claim and Evidence expectations; do not treat AI or heuristic output
  as trusted without Evidence.
- Confirm preview-before-action behavior for suggested actions.
- Confirm undo or rollback expectations before destructive operations.
- Confirm accepted code workflow still requires test evidence.
- Export or inspect Report / Proof Packet output and verify that evidence,
  decisions, limits, and reproduction steps remain clear.
- Review backup/restore safety expectations: manifest, verify, preview, hash
  match, source version, and restore-to-new-location inspection only.
- Confirm policy evaluation visibility does not become enforcement overreach:
  future policy material may inform evidence and review, but current workflow
  must not be blocked by unwired policy infrastructure.

## Verification Commands

These are recommended local verification commands for checkpoint work. They are
listed so future contributors can rerun them when available; a docs-only change
should not claim they passed unless they were actually run in that session.

Backend targeted policy tests:

```powershell
Push-Location .\backend
python -m pytest tests/test_policy_gate_service.py
Pop-Location
```

Backend full test suite:

```powershell
Push-Location .\backend
python -m pytest
Pop-Location
```

Frontend tests:

```powershell
Push-Location .\frontend
npm run test
Pop-Location
```

Frontend build:

```powershell
Push-Location .\frontend
npm run build
Pop-Location
```

Managed backup/restore API smoke:

```powershell
python .\scripts\backup_restore_api_smoke.py --cleanup
```

Diff hygiene:

```powershell
git diff --check
```

Release/tag boundary check:

```powershell
git tag --points-at HEAD
```

If running from a fresh checkout, install backend and frontend dependencies
first using the existing commands in `README.md` and `docs/V0_1_RC_CHECKLIST.md`.
No dedicated docs lint command is currently documented in the repository.

## P0/P1 Blocker Criteria

The default is no `rc2` and no release movement. A release or blocker decision
requires project owner approval and concrete evidence. Candidate P0/P1 blockers
include:

- Data loss risk.
- Destructive action without preview and undo or recovery safeguards.
- Policy gate fail-open behavior in a high-risk path.
- Backup/restore corruption or unrecoverable restore failure.
- Evidence or Proof Packet integrity break.
- Tag or release artifact mismatch.
- Accepted code workflow bypassing tests.

Each blocker report should include reproduction steps, affected invariant,
evidence, proposed fix scope, verification commands, and why the issue cannot
wait for normal post-RC1 hardening.

## Future Integration Warnings

The following remain future work only. Do not implement them in the current
docs checkpoint:

- Runtime policy gate enforcement.
- Live restore.
- Destructive restore.
- Database migration.
- API endpoint changes.
- UI enforcement.
- Release or tag work.

Any future implementation must start from the checkpoint evidence above and
must preserve the existing local-first trust boundary.
