# Policy Gate Input / Output Contract Review

## Status

This is Checkpoint C. It is a docs/design-only contract review that follows the
merged Checkpoint A/B evidence in `docs/checkpoint-a-dogfood-readiness.md`.

This document does not implement runtime policy gate enforcement, wire policy
gate results into action execution, change backend or frontend behavior, add API
endpoints, add database migrations, change tests, or authorize release work.

This document does not authorize runtime policy gate integration. It does not
authorize live restore, destructive restore, backup/restore behavior changes,
DB migrations, API changes, UI behavior changes, `rc2`, or release/tag work.
`v0.1.0-rc1` remains untouched.

## Source Basis

| Path | Type | What it contributed | Confidence / notes |
| --- | --- | --- | --- |
| `README.md` | doc | Product invariants, local-first scope, and docs navigation. | Confirmed in this pass. |
| `docs/policy-gate-integration-checkpoints.md` | doc | Checkpoint C scope, fail-closed expectations, and future enforcement boundary requirements. | Confirmed in this pass. |
| `docs/checkpoint-a-dogfood-readiness.md` | doc | Checkpoint A/B evidence, source map, and docs-only scope guard. | Confirmed in this pass. |
| `docs/high_risk_action_policy_gates.md` | doc | Future policy outcomes, risk categories, suggested metadata, and non-goals. | Confirmed in this pass; design foundation only. |
| `docs/agent_transparency_log.md` | doc | Future transparency event model, redaction/hash expectations, and policy gate event context. | Confirmed in this pass; no implementation confirmed. |
| `docs/threat_models/AGENT_INTERMEDIARY_TAMPERING.md` | doc | Threat model for intermediary tampering and fail-closed future hardening requirements. | Confirmed in this pass; design gate only. |
| `CHANGELOG.md` | doc | Post-RC1 policy gate result, evaluation summary, and fail-closed bugfix history. | Confirmed in this pass. |
| `backend/proofflow/services/policy_gate_service.py` | source | Observed policy gate result dataclass, outcome/category/severity enums, aggregation helper, evaluation summary, and JSON-safe serialization. | Confirmed in this pass. |
| `backend/tests/test_policy_gate_service.py` | test | Observed expected behavior for precedence, empty evaluation fail-closed behavior, serialization, immutability, alias safety, and caller downgrade rejection. | Confirmed in this pass. |

The requested `rg` search could not run in this local shell because `rg.exe`
returned `Access is denied`. `git grep` was used as a tracked-file-only fallback
for the same policy-gate search terms.

## Current Policy Gate Contract Summary

Observed in this pass:

- The current code-level policy gate contract is local helper code only. It is
  not wired into action execution, API endpoints, frontend behavior, DB schema,
  restore behavior, or release flow.
- `PolicyGateResult` represents one policy result item with identity,
  category, severity, outcome, reason, optional surface/path/command context,
  optional ProofFlow object references, optional transparency event reference,
  redaction status, and remaining risks.
- `PolicyGateEvaluation` accepts a collection of `PolicyGateResult` values and
  an optional caller-provided `final_outcome`.
- The effective `final_outcome` is computed restrictively from the
  result-derived aggregate and the caller-provided outcome when present.
- Empty result aggregation defaults to `fail_closed`.
- `block` and `fail_closed` are blocking outcomes.
- `require_decision` requires operator decision but is not treated as blocking
  by the current helper.
- Serialization emits JSON-safe snake_case keys and enum string values.
- Result and evaluation collections are frozen or tuple-normalized, and tests
  cover alias safety for list inputs and serialized payload mutation.

Inferred from tests:

- Caller-provided `final_outcome` is advisory for permissive or less restrictive
  claims and cannot downgrade result-derived restrictive outcomes.
- Caller-provided `final_outcome` can make the evaluation stricter.
- A caller-provided `allow` with no policy results still resolves to
  `fail_closed`.

Not confirmed in this pass:

- A concrete runtime policy input object that includes action preview hashes,
  actor identity, freshness timestamp, request/response hashes, or tamper
  binding.
- Any runtime enforcement boundary.
- Any API request/response schema for policy evaluation.
- Any DB table for policy evaluations or transparency events.
- Any parser/validator for malformed external policy JSON.
- Any implementation that attaches policy results to Evidence, Decisions,
  Reports, or Proof Packets.

Future integration must verify every not-confirmed item before relying on policy
evaluation for runtime enforcement.

## Inputs

| Input / field / concept | Source anchor | Purpose | Trust level | Required for future runtime enforcement? | Notes / open questions |
| --- | --- | --- | --- | --- | --- |
| `PolicyGateEvaluation.results` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Carries result items to aggregate into an effective policy outcome. | Authoritative only if produced by a trusted local policy evaluator and bound to the action being enforced. | Yes. | Current code accepts constructed objects; external parsing and freshness binding are not confirmed. |
| Caller-provided `final_outcome` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Lets the caller request or report a final outcome. | Advisory unless it is stricter than the result-derived aggregate. | No as an override; future runtime may record it as metadata. | It cannot downgrade result-derived `block` or `fail_closed`. |
| Result-derived outcome | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Supplies the per-policy outcome used for restrictive aggregation. | Authoritative after local validation and action binding. | Yes. | Current source does not prove the result was produced by a trusted evaluator. |
| `policy_id` / `policy_name` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Identifies the gate or rule that produced a result. | Descriptive unless bound to a trusted local evaluator. | Yes. | Versioning and policy configuration source are not confirmed. |
| `category` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Classifies risk surface such as filesystem escape, secret access, network execution, package mutation, process persistence, destructive local operation, backup/restore target risk, mismatch, or unattended mode. | Descriptive classification. | Yes for high-risk routing. | Future review must decide category coverage and ownership. |
| `severity` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Records informational through critical severity. | Advisory context. | Likely yes. | Current aggregation is by outcome, not severity. |
| `reason` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Operator-facing explanation for the result. | Evidence context, not a permission source. | Yes. | Redaction and localization expectations are not confirmed. |
| `matched_surface` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Names the surface that matched policy review, such as restore target or command surface. | Evidence context. | Likely yes. | Canonical values are not confirmed. |
| `redaction_status` | `backend/proofflow/services/policy_gate_service.py`; `docs/agent_transparency_log.md` | Records whether sensitive material was redacted or not applicable. | Evidence safety signal. | Yes for secret-bearing surfaces. | Current code stores a string; allowed values beyond tests are not confirmed. |
| `affected_paths` / `affected_commands` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Records paths and commands implicated by the policy result. | Evidence context after local normalization. | Yes for filesystem, restore, command, and package flows. | Current contract does not include preview hash or normalized plan hash. |
| `allowed_roots_snapshot` | `backend/proofflow/services/policy_gate_service.py`; `README.md`; `docs/high_risk_action_policy_gates.md` | Captures local root boundaries relevant to path policy. | Evidence context. | Yes for filesystem and restore actions. | Freshness relative to execution is not confirmed. |
| `related_case_id` | `backend/proofflow/services/policy_gate_service.py`; `README.md` | Links the policy result to a Case. | Required binding context. | Yes. | Future runtime must enforce "No Case, no workflow"; current helper only stores an optional ID. |
| `related_action_id` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Links the policy result to a proposed or previewed Action. | Required binding context. | Yes. | Current helper does not prove the result is fresh for the exact action. |
| `related_decision_id` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Links operator decision material where required. | Evidence and approval context. | Yes when outcome requires decision. | Future runtime must invalidate decisions if preview/action changes. |
| `related_evidence_id` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Links policy output to Evidence. | Required trust context. | Yes. | Evidence attachment semantics are not implemented in the current helper. |
| `transparency_event_id` | `backend/proofflow/services/policy_gate_service.py`; `docs/agent_transparency_log.md` | Connects result to future transparency log events. | Audit context; not currently implemented. | Yes when transparency logging is part of the future boundary. | No transparency log table/service confirmed in this pass. |
| `remaining_risks` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Records risks that remain after evaluation or decision. | Evidence context. | Yes for operator review and reports. | No report/export policy result attachment confirmed. |
| High-risk action context | `docs/high_risk_action_policy_gates.md`; `docs/threat_models/AGENT_INTERMEDIARY_TAMPERING.md` | Describes future action surfaces that need policy review. | Design input only. | Yes in future. | No concrete runtime input object confirmed. |
| ProofFlow invariant signals | `README.md`; `docs/policy-gate-integration-checkpoints.md` | Case, Evidence, Preview, Undo, Test, and Source requirements that future enforcement must preserve. | Product invariants. | Yes. | Most invariants are not directly represented as current policy gate fields. |

Current helper fields do not represent `artifact_id`, `run_id`, `claim_id`,
`report_id`, actor identity, agent identity, preview hash, normalized action
plan hash, policy evaluation timestamp, or policy configuration version. Those
are not confirmed in this pass.

## Outputs

| Output / field / concept | Source anchor | Meaning | Restrictiveness | Can caller override? | Future enforcement requirement |
| --- | --- | --- | --- | --- | --- |
| `allow` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | No known high-risk condition matched. | Least restrictive. | Caller cannot use it to downgrade result-derived restrictive outcomes. | Must never bypass preview, evidence, undo, source, or test invariants. |
| `warn` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Reviewable risk exists, but current helper does not block. | More restrictive than `allow`. | Caller cannot use it to downgrade `require_decision`, `block`, or `fail_closed`. | Must be visible and evidence-backed if used at runtime. |
| `require_decision` | `backend/proofflow/services/policy_gate_service.py`; `docs/high_risk_action_policy_gates.md` | Explicit operator decision is required. | More restrictive than `warn`, less than `block`. | Caller cannot use it to downgrade `block` or `fail_closed`. | Decision must bind to the exact preview/action and be invalidated by changes. |
| `block` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Policy violation that must not execute. | Blocking. | No downgrade allowed. | Enforcement boundary must prevent execution and record evidence/decision context where appropriate. |
| `fail_closed` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Policy evaluation could not safely produce a permissive result, or no results were available. | Most restrictive and blocking. | No downgrade allowed. | Missing, malformed, ambiguous, stale, or tampered policy state must land here or another non-permissive state. |
| Result-derived aggregate outcome | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Most restrictive outcome across result items, defaulting to `fail_closed` for empty input. | Authoritative after trusted local evaluation. | Caller-provided final outcome is combined restrictively, not trusted as a downgrade. | Runtime boundary must prove this aggregate is fresh and action-bound. |
| Caller-provided `final_outcome` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Optional caller request/report that participates in final aggregation. | Advisory unless stricter than aggregate. | Can make the final result stricter; cannot make it more permissive. | Must be logged as caller-provided metadata, not treated as authority to allow execution. |
| Effective `final_outcome` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | Final restrictive outcome stored on `PolicyGateEvaluation`. | Computed by most-restrictive aggregation. | No post-computation caller override confirmed. | Runtime enforcement must use this value or a stricter boundary result. |
| `is_blocking` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | True for `block` and `fail_closed`. | Blocking signal. | Derived; caller should not override. | Execution boundary must treat true as non-executable. |
| `requires_operator_decision` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | True for `require_decision`. | Decision-required signal. | Derived; caller should not override. | Operator approval must bind to exact preview/action. |
| `has_warnings` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | True when final outcome or any result is `warn`. | Visibility signal. | Derived; caller should not override. | Warnings must remain visible and not silently become allow. |
| Serialized `results` | `backend/proofflow/services/policy_gate_service.py`; `backend/tests/test_policy_gate_service.py` | JSON-safe list of result item dictionaries. | Evidence payload. | Serialized payload mutation does not mutate frozen evaluation. | Future evidence/export must preserve redaction and avoid secret leakage. |

Result-derived `block` and `fail_closed` outcomes must not be downgraded by a
caller-provided `final_outcome`.

## Trust And Authority Model

Policy result-derived restrictive outcomes are authoritative only when they are
produced by trusted local policy evaluation and bound to the exact action being
reviewed. Once present, result-derived `block` and `fail_closed` outcomes are
not advisory; a caller-provided `final_outcome` must not downgrade them.

Caller-provided `final_outcome` is not a permission source. It can make the
evaluation stricter, but it cannot convert a restrictive aggregate into a
permissive outcome.

Future runtime enforcement must treat missing, malformed, ambiguous, stale, or
tampered intermediary state as non-permissive unless the state is explicitly
proven safe. High-risk paths must fail closed.

Policy evaluation visibility is not the same as runtime enforcement. A visible
policy evaluation that is not enforced must be labeled as non-enforcing so an
operator does not mistake evidence for a blocker or approval gate.

## Fail-Closed Aggregation Rules

Observed fail-closed rules:

- Aggregation is restrictive by precedence:
  `allow < warn < require_decision < block < fail_closed`.
- Empty outcome aggregation defaults to `fail_closed`.
- `PolicyGateEvaluation()` defaults to `fail_closed`.
- `PolicyGateEvaluation(final_outcome=allow)` with no results still resolves to
  `fail_closed`.
- Result-derived `block` cannot be downgraded to `allow`.
- Result-derived `fail_closed` cannot be downgraded to `require_decision`.
- Caller-provided `final_outcome` may make the evaluation stricter, such as
  turning result-derived `warn` into `block`.

Unknown or untrusted policy state should not create an `allow`. Any future
runtime boundary must prove the same semantics with tests before enforcement is
accepted.

## Enforcement Boundary Implications

This section is future-facing and docs/design-only. It does not implement any
runtime integration.

A future runtime integration would have to prove:

- The action is associated with a Case.
- Artifact source is known where relevant.
- Claims are backed by Evidence where relevant.
- A preview occurred before action.
- A destructive action has undo or rollback support.
- A code workflow has test evidence before acceptance.
- The policy evaluation result is fresh and bound to the action being enforced.
- Restrictive outcomes cannot be bypassed by caller-supplied metadata.
- An audit/transparency record exists, or missing audit state fails closed for
  high-risk paths.
- The enforcement result is recorded as Evidence or Decision material where
  appropriate.

Backend safety checks remain authoritative. Policy gates may add review context
and fail-closed behavior, but they must not replace existing invariant
enforcement.

## Out Of Scope

Out of scope for this Checkpoint C document:

- Runtime policy gate wiring.
- Action execution enforcement.
- Live restore.
- Destructive restore.
- Backup/restore behavior changes.
- DB migration.
- API endpoint changes.
- UI behavior changes.
- Backend/frontend runtime changes.
- Test changes.
- Package/lock/config changes.
- `rc2`.
- Release/tag changes.

## Open Questions / Gaps

Real gaps found during inspection:

- No concrete runtime policy input object was confirmed.
- No runtime enforcement boundary was confirmed.
- No policy API endpoint or request/response schema was confirmed.
- No DB persistence model for policy evaluations was confirmed.
- No transparency log table/service implementation was confirmed.
- No parser or validator for malformed external policy JSON was confirmed.
- No freshness binding was confirmed for policy result versus preview/action.
- No tamper binding was confirmed through hashes, policy configuration version,
  or normalized action-plan hash.
- No direct `artifact_id`, `run_id`, `claim_id`, `report_id`, actor ID, or agent
  ID field was confirmed in the current helper.
- No evidence attachment or Proof Packet export semantics for policy results
  were confirmed.
- No authoritative source was confirmed for caller-supplied
  `PolicyGateResult` fields outside local helper construction.

These are review inputs for future owner decision. They are not implementation
tasks in this phase.

## Readiness Conclusion

Checkpoint C docs/design review is locally captured by this document.

This review can support a future owner decision about whether to proceed to
Checkpoint D enforcement boundary design review. It does not authorize runtime
integration.

Recommended next step after merge is owner review of this contract document,
then possibly Checkpoint D enforcement boundary design review, still
docs/design-only.

## Release / Tag Safety Note

`v0.1.0-rc1` remains untouched. No `rc2` is authorized. `HEAD` should not point
at a release tag for this checkpoint.
