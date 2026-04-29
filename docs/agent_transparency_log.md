# Agent Transparency Log Foundation

## Summary

Agent, model, router, and tool output is not trusted just because it arrived.
ProofFlow should preserve a local evidence trail from the received payload to
the normalized action plan, preview, decision, execution, and verification
result.

The Agent Intermediary Tampering threat model motivates a future local
append-oriented audit log for agent/tool-call/action workflows. The log should
help ProofFlow compare what it received, what it proposed, what the operator
approved, and what actually ran. This foundation does not claim immutable or
tamper-proof logging.

This log is a future foundation for AgentGuard and ActionGuard hardening. It is
not cryptographic upstream model provenance, and this document does not
implement the feature.

## Design Goals

- Keep audit evidence local-first.
- Support evidence-backed review before trust is granted.
- Compare natural-language explanation against executable action plans.
- Detect or route unexpected tool-call and action-plan changes for review.
- Support post-hoc Proof Packet export.
- Avoid storing secrets in plaintext.
- Fail closed for dangerous actions when configured.

## Non-Goals

- No Phase 5 live restore.
- No autonomous execution endorsement.
- No cryptographic proof that an upstream model response was unmodified.
- No cloud transparency service.
- No provider or router integration.
- No backend or frontend behavior in this PR.
- No storage migration in this PR.

## Relationship To Existing ProofFlow Invariants

The transparency log design should reinforce existing ProofFlow invariants:

- No Case, no workflow.
- No Evidence, no trusted Claim.
- No Preview, no Action.
- No Undo, no destructive Action.
- No Test, no accepted code workflow.
- No Source, no Artifact.

It should also align with managed backup and restore invariants:

- No Manifest, no Backup.
- No Verify, no trusted Backup.
- No Preview, no Restore.
- No Pre-restore Backup, no destructive Restore.
- No Hash Match, no Restore.
- No Source Version, no Restore Trust.
- No Restore to live DB in foundation phase.

These are existing project principles. A rule such as "No Unlogged Agent
Action" is only a future candidate and is not implemented by this document.

## Event Model

A future transparency log should record high-level events that connect agent
material to ProofFlow evidence and decisions.

### `agent_request_prepared`

Records that ProofFlow prepared an agent or model request.
Typical metadata includes case ID, run ID, provider or router trust label,
request metadata hash, redaction status, and remaining risks.

### `agent_response_received`

Records that ProofFlow received a model or router response.
Typical metadata includes response body hash where safe, response metadata,
provider or router trust label, redaction status, and whether raw capture was
withheld because secrets may be present.

### `tool_call_envelope_received`

Records the tool-call envelope as received by ProofFlow before it becomes an
action plan.
Typical metadata includes the tool-call envelope hash, tool names, target
workflow, redaction status, and parsing outcome.

### `action_plan_normalized`

Records the normalized action plan that ProofFlow will preview or reject.
Typical metadata includes normalized action plan hash, affected roots, proposed
paths, declared risks, and references to source Evidence.

### `preview_created`

Records a preview before execution.
Typical metadata includes preview result hash, planned writes, affected roots,
blocking risks, and links to Evidence.

### `policy_gate_triggered`

Records that a local policy gate detected a risky command, path, network call,
secret access, restore target, or mode condition.
Typical metadata includes gate name, policy result, severity, operator options,
and redaction status.

### `decision_recorded`

Records the operator decision.
Typical metadata includes decision ID, outcome, rationale, accepted preview ID
where applicable, and remaining risks.

### `action_executed`

Records an approved action execution.
Typical metadata includes action ID, execution result, changed paths, produced
Artifacts or Evidence, and undo availability.

### `action_rejected`

Records a proposed action that was rejected before execution.
Typical metadata includes action ID, reason, policy gate references, and
operator rationale.

### `undo_executed`

Records a reversible action undo.
Typical metadata includes original action ID, undo result, hash guard outcome,
changed paths, and remaining risks.

### `tests_recorded`

Records test evidence for a code workflow.
Typical metadata includes command, exit status, output hash or excerpt, test
Evidence ID, and known gaps.

### `proof_packet_exported`

Records a Proof Packet export.
Typical metadata includes packet path, packet hash, included Case ID, selected
Evidence IDs, and omitted or redacted material.

### `restore_preview_created`

Records a managed restore preview.
Typical metadata includes backup ID, restore preview ID, target paths, plan
hash, schema or version risks, and overwrite status.

### `restore_to_new_location_executed`

Records inspection restore to a new location.
Typical metadata includes backup ID, accepted preview ID, target paths,
restored file count, verification references, and remaining risks.

## Suggested Event Fields

Future events should use stable fields that let ProofFlow correlate received
agent material with actions and evidence:

- `event_id`
- `case_id`
- `run_id`
- `action_id`, `decision_id`, `artifact_id`, and `evidence_id` when applicable
- `timestamp`
- `event_type`
- provider, router, or base URL trust label
- request metadata hash
- response body hash where safe
- tool-call envelope hash
- normalized action plan hash
- preview result hash
- policy gate result
- operator decision
- execution result
- diff and test Evidence references
- redaction status
- remaining risks

## Hashing And Redaction

Raw payload capture can expose secrets. The transparency log should prefer
hashes for raw payloads when storing the raw text would create unnecessary
risk.

Redacted snippets can be stored as Evidence when they help explain a decision.
The log should record when redaction occurred and what kind of material was
withheld. ProofFlow should not silently drop secret-risk material without
recording that redaction happened.

Hashes help compare received payloads, tool-call envelopes, normalized action
plans, previews, and exported Proof Packets. They do not prove upstream model
provenance or prove that a router did not modify the response before ProofFlow
received it.

## Policy Gate Integration

Future AgentGuard or ActionGuard gates can use transparency events to explain
why an action was blocked, warned, or routed to explicit decision. Defensive
gate examples include:

- Remote installer command patterns.
- Package manager installs.
- Credential path access.
- Writes outside allowed roots.
- Network calls.
- Restore or backup target path changes.
- Natural-language explanation and executable action-plan mismatch.
- Unattended, autonomous, or YOLO-like mode warnings.

This document describes defensive review categories only. It does not provide
exploit payloads or step-by-step offensive instructions.

## Proof Packet Integration

Proof Packets should be able to include transparency log excerpts as audit
material without turning the log into a replacement for Proof Packet evidence.
Useful exported material includes:

- Summarized timeline.
- Selected event hashes.
- Policy gate outcomes.
- Preview and Decision references.
- Execution and test Evidence.
- Remaining risks.

Proof Packet exports should continue to distinguish evidence-backed claims from
assumptions, AI output, and heuristic signals.

## Failure Modes

- Log write failure before dangerous execution should fail closed.
- Log write failure for a low-risk preview may return a warning or block based
  on policy.
- Redaction failure should fail closed when secrets may be present.
- Clock skew and duplicate events should be detectable or at least visible.
- Evidence logs preserve what ProofFlow received, not necessarily what the
  upstream model originally produced.

## Future Implementation Sketch

A future implementation could include:

- A SQLite table such as `agent_transparency_events`.
- A service such as `transparency_log_service.py`.
- An append helper used by AgentGuard, ActionGuard, and managed restore flows.
- Tests for append-only semantics, redaction markers, policy-gate references,
  and Proof Packet export selection.
- A UI timeline that shows received payload, normalized plan, preview,
  decision, execution, and verification events.

This PR does not implement these pieces.

## References

- `docs/threat_models/AGENT_INTERMEDIARY_TAMPERING.md`.
- `docs/action_safety.md`.
- `docs/managed_backup_restore.md`.
- `docs/proof_packet.md`.
- `AGENTS.md`.
