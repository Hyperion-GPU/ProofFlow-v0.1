# Policy Gate Dry-run Evaluation Plan

## Status / Scope

This is Checkpoint E: dry-run-only policy evaluation plan.

This document is based on post-RC1 `main` after:

- #26 `docs: add policy gate integration checkpoints`
- #27 `docs: capture checkpoint A dogfood readiness`
- #28 `docs: review policy gate input output contract`
- #29 `docs: align post-RC1 phase status`
- #30 `docs: review policy gate enforcement boundary`

At the start of this checkpoint, `main` was confirmed at `047227d`.

This checkpoint is docs/design-only. It plans how a future implementation could
observe policy evaluation in dry-run mode. It does not implement dry-run,
connect policy evaluation to runtime paths, enforce action execution, change
APIs, change UI behavior, add database tables, add migrations, change tests, or
authorize runtime policy gate integration.

This checkpoint also does not authorize backup/restore behavior changes, live
restore, destructive restore, release work, `rc2`, or any movement of
`v0.1.0-rc1`. The `v0.1.0-rc1` tag remains untouched.

## Source Basis

| Source | Type | Confirmed use in this plan |
| --- | --- | --- |
| `README.md` | doc | Current status, post-RC1 policy gate navigation, and release candidate stamp. |
| `PLANS.md` | doc | MVP milestones, evidence/action/decision workflow, deferred future scope, and managed backup/restore boundaries. |
| `CHANGELOG.md` | doc | Post-RC1 policy gate foundation history and fail-closed aggregation fix. |
| `docs/policy-gate-integration-checkpoints.md` | doc | Checkpoint E purpose, fail-closed expectations, and owner decision gate for release movement. |
| `docs/checkpoint-a-dogfood-readiness.md` | doc | Current dogfood evidence before policy gate runtime pressure. |
| `docs/policy-gate-input-output-contract-review.md` | doc | Policy input/output contract, non-enforcing visibility warning, trust model, and open gaps. |
| `docs/policy-gate-enforcement-boundary-review.md` | doc | Checkpoint D recommendation for a future server-side pre-execution boundary. |
| `docs/high_risk_action_policy_gates.md` | doc | Future high-risk categories, outcomes, metadata, evidence expectations, and non-goals. |
| `docs/agent_transparency_log.md` | doc | Future transparency event model and `policy_gate_triggered` audit context. |
| `docs/threat_models/AGENT_INTERMEDIARY_TAMPERING.md` | doc | Intermediary tampering risks and local validation expectations. |
| `docs/managed_backup_restore.md` | doc | Managed backup/restore invariants, preview/verify/hash trust, restore-to-new-location limits, and live restore non-goal. |
| `backend/proofflow/services/policy_gate_service.py` | source | Current helper-only policy outcomes, result shape, evaluation aggregation, and serialization behavior. |
| `backend/tests/test_policy_gate_service.py` | test | Current proof for fail-closed empty aggregation, caller downgrade rejection, immutability, alias safety, and JSON-safe output. |
| `backend/proofflow/routers/actions.py` | source | Current action HTTP entry points for create, approve, execute, undo, and reject. |
| `backend/proofflow/services/action_service.py` | source | Current action lifecycle, status transitions, preview/result/undo records, and execution path. |
| `backend/proofflow/services/action_safety.py` | source | Existing backend-authoritative filesystem safety checks that policy gates must not replace. |

No source in this pass confirms a runtime dry-run endpoint, policy evaluation
table, dry-run UI surface, dry-run report/export inclusion, or transparency log
runtime implementation. Those remain future design gaps.

## Dry-run Definition

Dry-run policy evaluation is a non-enforcing evaluation mode that records what
a policy gate would have concluded for a bound action context, without changing
action execution, approval, rejection, undo, restore, report, or export
behavior.

Dry-run mode may say that enforcement would have produced `warn`,
`require_decision`, `block`, or `fail_closed`.

Dry-run mode must not say that an action was approved, allowed, blocked, or
made safe by policy enforcement. Dry-run output is observation, not runtime
authority.

Dry-run mode must preserve these rules:

- It cannot allow execution.
- It cannot block execution.
- It cannot override an existing backend refusal.
- It cannot bypass existing backend safety checks.
- It cannot change Action status.
- It cannot change, create, approve, or reject a Decision.
- It cannot change undo behavior.
- It cannot change restore behavior.
- It cannot replace Preview, Undo, Test, Source, Evidence, backup, or restore
  invariants.
- It must label every result as non-enforcing.

## Candidate Dry-run Attachment Points

| Attachment point | What dry-run can observe | Main limitation | Fit for first future implementation |
| --- | --- | --- | --- |
| Action proposal / suggestion | Risky proposed paths, commands, categories, or explanations before action creation. | The action ID, preview hash, and operator-visible material may not be stable yet. | Useful later for early signals, but not the first preferred point. |
| Preview time | Risk in the exact preview material shown to the operator. | Preview may still change before execution. | Useful supporting point if bound to the later execution request. |
| Approval / Decision time | Whether a human accepted a preview and known risk. | Decisions can become stale if preview or action changes. | Useful review context, not enough by itself. |
| Server-side pre-execution | The exact Case, Action, preview, existing safety state, and execution request immediately before mutation. | It must remain narrow to avoid turning normal workflows into policy prompts. | Preferred first future dry-run observation point for high-risk Actions. |
| Post-execution audit | What happened and which policy result would have applied. | Too late to prevent mutation if enforcement is later enabled. | Useful for comparison and false positive / false negative review. |
| Report / export inclusion | Whether policy observations are visible in Evidence, reports, or Proof Packets. | It cannot authorize or prevent execution. | Useful only if clearly labeled as observed, not enforced. |
| Backup / restore dry-run | Restore target risk, overwrite risk, manifest/hash/source-version context. | Easy to confuse with live restore readiness or restore authorization. | Keep as a future specialized case; do not start with restore-first authority. |

The recommended first future dry-run implementation should observe high-risk
Action execution paths near the future server-side pre-execution boundary,
aligned with Checkpoint D, while remaining non-enforcing.

This keeps future migration from dry-run to enforcement understandable without
turning dry-run into a hidden gate. It also keeps UI-only state, report export,
and restore-first flows from becoming authority surfaces.

## Dry-run Lifecycle

A future dry-run lifecycle should be:

1. An Action exists with Case context.
2. Preview material exists for the exact Action.
3. Dry-run policy evaluation is computed against the exact Action and preview
   material near the pre-execution observation point.
4. The dry-run result is recorded as a non-enforcing evidence candidate.
5. Existing runtime behavior continues unchanged.
6. The dry-run result may appear in a future report or Proof Packet only as
   "observed, not enforced."
7. The owner reviews false positives, false negatives, unclear results, and
   missing context before enforcement is considered.

Dry-run output must not become allow authority. Existing backend safety checks,
Action lifecycle rules, restore protections, preview requirements, undo
requirements, test expectations, source requirements, and Evidence trust rules
remain authoritative.

## Conceptual Data / Evidence Shape

These are conceptual future fields only. They are not the current DB schema,
API schema, Pydantic model, frontend type, or runtime contract. This plan does
not require renaming or changing the current `PolicyGateEvaluation.final_outcome`
helper field.

A future dry-run record should include:

- `dry_run_id`
- `case_id`
- `action_id`
- `action_type` or `category`
- `preview_id` or `preview_hash`
- `policy_evaluation_id`
- `would_have_outcome`
- result-derived aggregate outcome
- caller-provided `final_outcome`, if any
- `non_enforcing: true`
- `evaluated_at`
- freshness basis
- policy configuration version, if available
- source anchors, affected paths, or affected commands
- `evidence_ids`
- `decision_id`, if relevant
- `transparency_event_id`, if available
- remaining risks
- gaps or missing context
- redaction status

The dry-run field should be named `would_have_outcome`, not `final_outcome`,
when presented as a dry-run observation. `final_outcome` can exist as current
helper or caller metadata, but dry-run presentation must not make it look like a
runtime authorization result.

## Labeling Requirements

Every future dry-run result must be labeled:

- non-enforcing
- not an approval
- not a block
- not a release gate
- not proof of safety
- not a replacement for Preview, Undo, Test, Source, Evidence, backup, restore,
  or backend hard safety checks

Recommended operator-facing label:

> Dry-run policy result: observed only. This result did not allow, block, or
> modify execution.

Reports, Proof Packets, logs, API payloads, and UI surfaces must keep the same
meaning if they ever include dry-run material. A warning, block, or fail-closed
dry-run result is evidence for review, not an execution decision.

## Fail-closed Semantics In Dry-run

Dry-run is non-enforcing, but it should preserve policy semantics so future
comparison is meaningful:

- Empty aggregation reports `would_have_outcome = fail_closed`.
- Malformed input reports `would_have_outcome = fail_closed`.
- Missing Case context reports `would_have_outcome = fail_closed`.
- Missing preview context reports `would_have_outcome = fail_closed`.
- Action or preview mismatch reports `would_have_outcome = fail_closed`.
- Stale preview hash or stale policy evaluation reports
  `would_have_outcome = fail_closed`.
- Caller-provided `final_outcome` cannot downgrade a result-derived `block` or
  `fail_closed`.
- Unknown intermediary, tamper, or redaction state must not produce
  `would_have_outcome = allow`.

A dry-run `fail_closed` is evidence that enforcement would have failed closed.
It is not itself a runtime block in dry-run mode.

## False Positive / False Negative Review

Dry-run exists to collect evidence before enforcement. A future review loop
should classify observations:

- False positive: dry-run reports `block` or `fail_closed`, but owner review
  concludes the existing action was actually safe under the intended policy.
- False negative: dry-run reports `allow` or `warn`, but owner review concludes
  the action should have required a stricter outcome.
- Unclear: missing context, stale material, redaction limits, or unbound
  evidence prevents trust in the dry-run result.

Owner review is required before moving from dry-run observation to enforcement.
Dry-run evidence alone is not enough to authorize hard enforcement.

## What Dry-run Must Not Touch

Future dry-run design must not touch:

- Action status mutation.
- Action execution behavior.
- Approve or reject behavior.
- Undo behavior.
- Restore behavior.
- Backup behavior.
- Report or export behavior unless separately designed as labeled evidence.
- Live restore.
- Destructive restore.
- Runtime policy gate wiring.
- Dry-run runtime instrumentation in this checkpoint.
- API endpoint shape.
- UI behavior.
- DB schema, migrations, or models.
- Backend or frontend runtime code.
- Test logic.
- Package, lock, or config files.
- Release state.
- Tags, including `v0.1.0-rc1`.
- `rc2`.

Dry-run must also avoid becoming a global blocker, restore-first authority, or
UI authority. It should observe high-risk Action context without changing the
main workflow.

## Future Test Matrix

This matrix defines future coverage expectations only. It does not add or
authorize tests in this checkpoint.

| Scenario | Expected future dry-run behavior |
| --- | --- |
| Valid high-risk Action with Case and preview | Records `would_have_outcome` with `non_enforcing: true`. |
| Dry-run reports `block` | Action still follows existing runtime behavior in dry-run mode. |
| Dry-run reports `fail_closed` | Action still follows existing runtime behavior in dry-run mode. |
| Result-derived `block` plus caller `final_outcome=allow` | `would_have_outcome` remains `block`. |
| Result-derived `fail_closed` plus caller permissive value | `would_have_outcome` remains `fail_closed`. |
| Empty aggregation | Records `would_have_outcome = fail_closed`. |
| Missing Case | Records `fail_closed` or missing-context state as non-enforcing evidence. |
| Missing preview | Records `fail_closed` or missing-context state as non-enforcing evidence. |
| Action mismatch | Records `fail_closed`. |
| Stale preview hash | Records `fail_closed`. |
| Warning result | Warning remains visible as non-enforcing observation. |
| Dry-run result appears in report or Proof Packet | It appears only with non-enforcing labeling. |
| Dry-run result references Evidence | Evidence label makes clear that it was observed, not enforced. |
| Dry-run observes backup/restore target risk | Existing backup/restore behavior remains unchanged. |
| Dry-run observes restore risk | It does not authorize live restore or destructive restore. |
| Release/tag state exists | Dry-run does not change release state, tags, or `rc2` status. |

## Open Questions / Gaps

These are real gaps for future owner decision. They are not implementation
tasks in this checkpoint.

- Whether dry-run records need DB persistence.
- If there is no new table, whether dry-run material should begin as Evidence
  metadata or report-only material.
- Whether dry-run needs an API endpoint.
- Whether dry-run should start only on action execution or also cover restore
  preview.
- Whether dry-run results should enter Proof Packets.
- How UI should display non-enforcing policy results without implying
  approval or blocking.
- How the freshness window should be defined.
- How policy configuration version should be bound.
- How actor, user, agent, or tool identity should be bound.
- Whether transparency log implementation must land before dry-run records are
  trusted.
- How false positive, false negative, and unclear observations should be
  recorded.
- Which backend service should own future dry-run orchestration.
- Which high-risk Action classifier is authoritative.
- How redaction status should be validated for secret-bearing policy results.

## Readiness Conclusion

Checkpoint E only designs a dry-run plan. It does not authorize implementation,
runtime enforcement, API changes, UI changes, database changes, migrations,
tests, backup/restore behavior changes, release movement, `rc2`, or tag work.

The recommended future direction is:

> Future dry-run policy evaluation should observe high-risk Action execution
> paths near the future server-side pre-execution boundary, but must remain
> non-enforcing, evidence-labeled, and unable to allow, block, or override
> execution.

After this checkpoint, the owner can choose to pause, dogfood current `main`,
refine the docs-only dry-run plan, or explicitly authorize a separate future
dry-run foundation implementation. The next step should not jump directly to
hard enforcement without owner approval and evidence from dry-run planning.
