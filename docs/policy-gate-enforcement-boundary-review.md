# Policy Gate Enforcement Boundary Review

## Status / Scope

This is Checkpoint D: policy gate runtime boundary design review.

This document is based on post-RC1 `main` after:

- #26 `docs: add policy gate integration checkpoints`
- #27 `docs: capture checkpoint A dogfood readiness`
- #28 `docs: review policy gate input output contract`
- #29 `docs: align post-RC1 phase status`

At the start of this review, remote `main` was confirmed at
`3d3f0d7271305511d31c72abdbcb95cbfbdfa18c`.

This document is docs/design-only. It does not implement runtime policy gate
enforcement, wire policy checks into action execution, change APIs, add storage,
change UI behavior, or authorize runtime integration.

This document also does not authorize live restore, destructive restore,
backup/restore behavior changes, release work, `rc2`, or any movement of
`v0.1.0-rc1`. The `v0.1.0-rc1` tag remains untouched.

## Source Basis

| Source | Type | Confirmed use in this review |
| --- | --- | --- |
| `README.md` | doc | Current product status, post-RC1 policy gate links, and core invariants. |
| `PLANS.md` | doc | Managed backup/restore phase truth and deferred live DB restore status. |
| `CHANGELOG.md` | doc | Post-RC1 managed backup/restore and policy gate foundation history. |
| `docs/policy-gate-integration-checkpoints.md` | doc | Checkpoint sequence, fail-closed expectations, and Checkpoint D boundary purpose. |
| `docs/checkpoint-a-dogfood-readiness.md` | doc | Current dogfood evidence and source map before runtime enforcement pressure. |
| `docs/policy-gate-input-output-contract-review.md` | doc | Checkpoint C policy input/output contract, trust model, gaps, and non-authorization boundary. |
| `docs/high_risk_action_policy_gates.md` | doc | Future high-risk action categories, outcomes, and policy metadata expectations. |
| `docs/agent_transparency_log.md` | doc | Future transparency event model and policy/tamper context expectations. |
| `docs/threat_models/AGENT_INTERMEDIARY_TAMPERING.md` | doc | Intermediary tampering risks and why local validation must remain authoritative. |
| `docs/managed_backup_restore.md` | doc | Backup/restore invariants, restore preview, restore-to-new-location, and live restore non-goals. |
| `backend/proofflow/services/policy_gate_service.py` | source | Current local helper contract for outcomes, result fields, evaluation, and serialization. |
| `backend/tests/test_policy_gate_service.py` | test | Current proof for fail-closed aggregation, caller downgrade rejection, empty aggregation, and JSON-safe output. |
| `backend/proofflow/routers/actions.py` | source | Current action HTTP entry points for create, approve, execute, undo, and reject. |
| `backend/proofflow/services/action_service.py` | source | Current action lifecycle surface: create, approve, execute, undo, reject, status, preview, metadata, and undo records. |
| `backend/proofflow/services/action_suggestion_service.py` | source | LocalProof suggestion path and scope metadata creation before actions are created. |
| `backend/proofflow/services/action_safety.py` | source | Existing filesystem scope validation that future policy gates must not replace. |
| `backend/proofflow/models/schemas.py` | source | Current Action, backup, restore, and policy-facing response shapes. |
| `backend/proofflow/storage/schema.sql` | source | Current persisted action, backup, and restore preview tables. |
| `backend/proofflow/services/backup_service.py` | source | Backup preview/create/verify and manifest/hash trust surface. |
| `backend/proofflow/services/restore_service.py` | source | Restore preview persistence, `accepted_preview_id`, `plan_hash`, overwrite rejection, and live-root blocking. |
| `backend/tests/test_actions_api.py` | test | Current action lifecycle API behavior and state transitions. |
| `backend/tests/test_restore_api.py` | test | Current restore preview and restore-to-new-location API behavior. |

No source in this pass confirms a runtime policy endpoint, policy evaluation
table, transparency log table, UI enforcement surface, or policy parser for
external JSON. Those remain gaps for future owner decision.

## Current Runtime Facts

Checkpoint D must distinguish current implementation from future design:

- Current action HTTP entry points are `POST /actions`,
  `POST /actions/{id}/approve`, `POST /actions/{id}/execute`,
  `POST /actions/{id}/undo`, and `POST /actions/{id}/reject`.
- Current action creation stores a new action as `previewed` through
  `create_action`; there is no separate persisted proposal state or dedicated
  `/actions/preview` endpoint confirmed in this pass.
- Current execution only accepts an `approved` action, undo only accepts an
  `executed` action, and reject applies before execution.
- Current action responses expose `preview`, `result`, `undo`, and `metadata`.
- Current LocalProof suggestions create action previews with filesystem scope
  metadata; existing filesystem safety checks remain backend-authoritative.
- Current backup preview is read-only. Backup create writes archive and sidecar
  manifest records only after the create path succeeds.
- Current restore-to-new-location requires a verified backup, a persisted
  preview, matching `accepted_preview_id`, matching backup ID and target paths,
  and matching `plan_hash`.
- Current restore rejects `would_overwrite`, live DB/data/proof packet overlap,
  stale preview plans, and unsafe target paths.
- Current `PolicyGateEvaluation` is a helper contract only. It aggregates toward
  the most restrictive outcome, defaults empty results to `fail_closed`, and
  does not let caller-provided `final_outcome` downgrade result-derived
  `block` or `fail_closed`.
- Current transparency and tamper materials are future design foundations, not
  implemented runtime audit plumbing.

## Candidate Enforcement Boundaries

| Boundary | What it can catch | Risk if too early | Risk if too late | Required evidence | Fail-closed behavior | First runtime fit |
| --- | --- | --- | --- | --- | --- | --- |
| Action suggestion / proposal | Risky proposed path, command, or action category before the operator sees it. | No stable preview or action ID may exist yet, so results can become stale or unbound. | N/A. | Case context, proposed action shape, source artifact or run context, redaction status. | Missing case or unbound proposal must not create `allow`. | Useful for future dry-run visibility, not first enforcing boundary. |
| Preview | Mismatch between intended operation and preview material, risky target paths, missing source references. | Preview may be advisory and may not be accepted yet. | If preview is skipped, action execution could bypass policy. | Case ID, preview material, normalized preview hash, action category, affected paths/commands. | Missing or malformed preview for high-risk action blocks or fails closed. | Strong input source, but not enough by itself unless bound to execution. |
| Approval / Decision | Whether a human accepted the exact risk and preview for `require_decision`. | Can become stale if action or preview changes after approval. | If only checked after execution, decision is audit-only. | Decision ID, actor context, exact preview/action binding, policy result, timestamp/freshness. | Missing or mismatched Decision blocks `require_decision` path. | Good supporting boundary, not the only enforcement point. |
| Server-side pre-execution | Last safe point before mutation; can verify preview, policy result, Decision, and undo metadata together. | If invoked for too many harmless reads, it can distort normal ProofFlow browsing. | If skipped, policy becomes visible but non-enforcing. | Case ID, Action ID, action type/category, preview hash, policy evaluation, Evidence IDs, Decision ID when required, undo metadata for destructive actions, source/test context as relevant. | Missing, stale, malformed, tampered, or mismatched state blocks or fails closed. | Best first future enforcement boundary for high-risk Actions. |
| Execution result recording | Captures what happened and any policy context after execution. | N/A. | Too late to prevent unsafe mutation. | Execution result, policy evaluation used, action result, Evidence/Report links. | Missing result record should not retroactively allow execution. | Audit support only, not primary gate. |
| Undo / rollback | Detects missing undo metadata or unsafe rollback state. | May block recovery if too broad. | If only checked after unsafe execution, damage may already exist. | Undo JSON, hash guards, original paths, action status, filesystem scope. | Destructive action without undo metadata blocks before execution; unsafe undo fails closed. | Supporting requirement for destructive high-risk Actions. |
| Report / export | Ensures policy outcomes remain visible in Proof Packets and reports. | Can turn non-mutating report viewing into noisy policy prompts. | Cannot prevent unsafe action. | Evidence IDs, policy result, Decision IDs, redaction status, remaining risks. | Missing report policy context is a report completeness issue, not execution allow. | Not first enforcement boundary. |
| Backup / restore sensitive operation | Captures restore target risk, overwrite risk, live-root overlap, manifest/hash mismatch, and source version risk. | A restore-specific gate could duplicate existing hard checks or imply live restore readiness. | If only checked after restore write, it is too late. | Verified backup, manifest/archive hashes, restore preview ID, plan hash, planned writes, target paths, version/schema risks. | Missing verify, missing preview, stale plan hash, overwrite, or live-root overlap blocks. | Keep as future specialized high-risk action case; do not start with live/destructive restore. |

## Recommended Boundary Model

Future runtime integration should prefer a server-side pre-execution enforcement
boundary for high-risk Actions, after preview material exists and before
execution mutates state.

That means the future gate should sit on the backend execution path for
high-risk action execution, not as a UI-only gate, global app blocker, generic
permission system, or restore-first path. UI may display policy state, but UI
state must not be the authority that allows mutation.

This recommended direction does not authorize implementation. Before any
runtime integration, the owner must approve a scoped implementation milestone
and the future code must prove that backend hard safety checks remain
authoritative.

The future pre-execution gate must preserve these rules:

- It adds policy review on top of existing service safety checks.
- It does not replace `action_safety.py`, backup verification, restore target
  validation, manifest/hash checks, or undo/hash guards.
- It applies first to high-risk Actions only.
- It binds policy evaluation to the exact Case, Action, preview material, and
  execution request.
- It treats `warn`, `require_decision`, `block`, and `fail_closed` as review
  outcomes, not as UI labels that can be silently ignored.

## Evidence Binding Requirements

Future runtime enforcement should require these bindings before a high-risk
Action can execute:

- Case ID: no high-risk workflow without a Case.
- Action ID: policy evaluation must bind to one exact action, not a reused
  action-like payload.
- Action type and category: the evaluator must know the action surface, such as
  filesystem action, backup/restore target risk, package mutation, command
  execution, or autonomous/unattended mode.
- Preview ID or preview material hash: the evaluated preview must match the
  preview the operator saw and the server is about to execute.
- Policy evaluation ID or equivalent local record: the gate must know which
  evaluation was used.
- Policy result and result-derived aggregate: caller metadata cannot downgrade
  result-derived `block` or `fail_closed`.
- Freshness data: stale policy evaluation must require fresh evaluation or fail
  closed.
- Evidence IDs: policy result, warning, block, or decision-required state must
  be traceable as Evidence where relevant.
- Decision ID for `require_decision`: the Decision must bind to the same Case,
  Action, preview, policy result, and actor context.
- Undo or rollback metadata for destructive Actions: no undo metadata, no
  destructive execution.
- Artifact source reference for artifact-backed action: no source, no artifact
  action trust.
- Test evidence for accepted code workflow: no test evidence, no accepted code
  workflow.
- Transparency or tamper context for agent/tool/action intermediary: unknown,
  missing, or tampered intermediary state must not create `allow`.
- Actor, human, or agent context: current source does not confirm a complete
  actor identity contract; future design must either bind it or mark the
  enforcement path as not ready.

Policy evaluation must never be reused for another Action, another preview, a
changed target path, or a changed execution request.

## Fail-Closed Boundary Rules

Future runtime enforcement must use non-permissive outcomes for unsafe or
untrusted state:

- No Case plus high-risk action: block or `fail_closed`.
- No preview plus action execution: block.
- Destructive action without undo metadata: block.
- Missing policy evaluation for high-risk action: `fail_closed`.
- Malformed policy evaluation: `fail_closed`.
- Stale policy evaluation: `fail_closed` or require a fresh evaluation.
- Action ID mismatch: `fail_closed`.
- Preview hash or plan hash mismatch: `fail_closed`.
- Result-derived `block` or `fail_closed` cannot be downgraded.
- Caller-provided `final_outcome` is not an allow authority.
- Empty result aggregation remains `fail_closed`.
- Unknown intermediary, tamper, or redaction state must not create `allow`.
- `require_decision` without a bound Decision blocks execution.
- Backup restore without verified manifest/hash trust blocks restore.
- Restore target overwrite, live-root overlap, or stale restore preview blocks
  restore-to-new-location and does not imply live restore safety.

## What Not To Gate Yet

The first runtime boundary should not gate these surfaces:

- Ordinary read-only navigation.
- Normal Case browsing.
- Report viewing.
- Docs browsing.
- Harmless export preview.
- Global app startup.
- All UI visibility.
- General search and dashboard visibility.
- Live DB restore.
- Destructive restore.
- Global chat or file-manager-style permissions.
- Every warning-only policy result as a hard blocker.

Avoid turning ProofFlow into a general permission app. The first runtime
boundary should be narrow, server-side, evidence-backed, and limited to
high-risk Actions.

## Future Test Matrix

This matrix defines future coverage expectations only. It does not add or
authorize tests in this checkpoint.

| Scenario | Expected future outcome |
| --- | --- |
| No Case plus high-risk action | Block or `fail_closed`. |
| Case present but no preview | Block. |
| Destructive action without undo metadata | Block. |
| Code workflow without test evidence | Not accepted as a trusted code workflow. |
| Artifact action missing source reference | Block or remain untrusted. |
| Result `block` plus caller `final_outcome=allow` | Final outcome remains `block`. |
| Result `fail_closed` plus caller `final_outcome=warn` | Final outcome remains `fail_closed`. |
| Empty result aggregation | Final outcome is `fail_closed`. |
| Stale evaluation | Fail closed or require fresh evaluation. |
| Action ID mismatch | Fail closed. |
| Preview hash mismatch | Fail closed. |
| Missing transparency or tamper context | Non-permissive unless explicitly scoped out by owner decision. |
| `require_decision` without bound Decision | Block. |
| Valid preview plus valid evidence plus allow | May proceed through existing backend safety checks. |
| Warning policy result | Warning remains visible and evidence-backed; it does not silently become allow. |
| Restore preview `plan_hash` mismatch | Block restore and require a new preview. |
| Restore overwrite or live-root overlap | Block. |

## Open Questions / Gaps

These are design gaps for owner decision. They are not implementation tasks in
this checkpoint.

- Which backend service should own the future pre-execution boundary.
- The authoritative source for high-risk Action classification.
- Policy evaluation freshness window and invalidation rules.
- Policy evaluation persistence model.
- Whether policy results become Evidence, Decision material, or both.
- How enforcement results enter Proof Packet export.
- When the transparency log implementation should be introduced.
- How to define preview hash and normalized action plan hash.
- Whether actor, user, agent, or tool identity must enter the contract.
- Whether restore-specific policy gates need a separate design pass.
- How UI should distinguish non-enforcing policy visibility from enforcing
  policy state.
- How redaction status should be validated for secret-bearing surfaces.
- Whether warnings can ever require additional operator acknowledgement without
  becoming a hard block.

## Readiness Conclusion

Checkpoint D completes an enforcement boundary design review. It does not
authorize runtime integration, API changes, UI changes, database changes,
runtime behavior changes, live restore, destructive restore, release movement,
or `rc2`.

The recommended future direction is a narrow server-side pre-execution boundary
for high-risk Actions, after preview material exists and before execution
mutates state. That direction still requires owner approval before any
implementation.

After this checkpoint, the owner may decide to pause, continue dogfood, request
more design review, or move to a dry-run-only policy evaluation plan. This
review does not recommend jumping directly into runtime enforcement
implementation.

## Release / Tag Safety Note

`v0.1.0-rc1` remains untouched. No `rc2` is authorized. This checkpoint should
not move, rebuild, delete, replace, or retag any release artifact.
