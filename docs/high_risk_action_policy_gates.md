# High-Risk Action Policy Gates

This document defines a future local-first policy gate design for high-risk
agent, script, and tool actions in ProofFlow.

This is a design foundation only. It does not implement policy gates, change
runtime behavior, add API endpoints, or add storage migrations.

## Summary

Agent, model, router, MCP, middleware, and tool output is proposal material, not
trusted execution input. A proposed command or filesystem operation should not
be trusted merely because it appears to come from a model.

High-risk actions should produce Evidence and require an explicit Decision
before execution. Some dangerous actions should fail closed unless the operator
has deliberately enabled and approved that class of action.

This PR does not implement policy gates. It defines the future design surface
that can connect AgentGuard, ActionGuard, LocalProof, managed backup/restore,
the Agent Transparency Log, and Proof Packet export.

## Design Goals

- Evaluate policy locally, inside ProofFlow's trust boundary.
- Provide a clear preview before execution.
- Show a human-visible risk explanation before approval.
- Convert risky proposed actions into Evidence-backed allow, block, warn, or
  decision outcomes.
- Fail closed for dangerous actions when configured.
- Preserve compatibility with Proof Packet export.
- Minimize secret exposure in logs and evidence.
- Align with AgentGuard command review, ActionGuard safety checks, LocalProof
  filesystem workflows, and managed backup/restore flows.
- Keep backend safety checks authoritative; policy gates add review context and
  fail-closed behavior, but do not replace invariant enforcement.

## Non-Goals

- No backend or frontend behavior change in this PR.
- No DB migration.
- No API endpoints.
- No autonomous execution endorsement.
- No malware or exploit detection guarantee.
- No cloud policy service.
- No Phase 5 live restore.
- No destructive restore enablement.
- No overwrite restore enablement.

## Relationship To ProofFlow Invariants

Policy gates are an extension of existing ProofFlow principles:

- No Case, no workflow.
- No Evidence, no trusted Claim.
- No Preview, no Action.
- No Undo, no destructive Action.
- No Test, no accepted code workflow.
- No Source, no Artifact.

Managed backup/restore policy must also preserve the existing restore
invariants:

- No Manifest, no Backup.
- No Verify, no trusted Backup.
- No Preview, no Restore.
- No Pre-restore Backup, no destructive Restore.
- No Hash Match, no Restore.
- No Source Version, no Restore Trust.
- No Restore to live DB in foundation phase.

A future "No Policy Gate, no high-risk Action" rule is a candidate design
principle. It is not implemented by this PR.

## Policy Outcomes

Future policy evaluation should produce one of these outcomes:

- `allow`: The proposal does not match known high-risk conditions. The action
  may continue through normal preview and decision gates.
- `warn`: The proposal has reviewable risk, but policy does not require a hard
  block. The warning should still become Evidence.
- `require_decision`: The proposal needs explicit operator approval for the
  exact previewed action before execution can proceed.
- `block`: The proposal violates a local policy and must not execute.
- `fail_closed`: Policy evaluation could not complete safely, or a dangerous
  class is configured to require a successful gate before execution.

Every outcome should be linked to a Case, proposed Action, relevant Evidence,
operator Decision when applicable, and a future transparency log event when
available.

## Risk Categories

The following categories describe future defensive policy checks. They are not
offensive recipes and should not be implemented as a complete security product
claim.

### 1. Filesystem Escape

Policy should detect and block or escalate proposed writes outside
`source_root`, `target_root`, or `allowed_roots`.

It should also detect attempts to touch ProofFlow's SQLite DB, data directory,
or proof packet output paths, plus suspicious path traversal or
symlink-sensitive operations.

### 2. Secret Access

Policy should require explicit review for attempts to read or expose common
credential filenames, environment variables, SSH/GPG/API key material, and
token-bearing configuration files.

Evidence should prefer hashes, redacted snippets, and redaction markers rather
than raw secret-bearing payloads.

### 3. Network Execution

Policy should block or require explicit decisions for remote installer
patterns, piping network content into shells, and background network processes.

The gate should record the matched surface and operator-facing reason without
embedding executable payloads in the policy documentation.

### 4. Package/Dependency Mutation

Policy should flag package manager install or update commands, unknown
registries, lockfile mutation, and lifecycle script risk.

Dependency mutation can change future execution behavior, so the decision
should record the package surface, affected files, and remaining risks.

### 5. Process And Persistence

Policy should flag background daemons, startup file mutation, scheduled task
changes, and shell profile mutation.

Persistence-sensitive changes should require a clear preview and operator
decision because they can survive the immediate workflow.

### 6. Destructive Local Operations

Policy should block or require explicit decisions for delete, overwrite,
recursive move, broad permission changes, and irreversible transformations.

Destructive actions must preserve the existing requirement that there is an
undo or recovery path before execution.

### 7. Backup / Restore Target Risk

Policy should treat backup and restore target changes as high risk. This
includes restore target path changes, overwrite attempts, overlap with the live
DB/data/proof packet roots, missing hash match, and missing source version
trust.

Restore-to-new-location remains inspection evidence only. It must not be
presented as proof that live restore is safe.

### 8. Explanation/Action Mismatch

Policy should compare the natural-language explanation with the executable
plan. It should flag cases where the explanation claims one target or purpose
while the action plan changes another path, adds unexpected network activity, or
mutates dependencies.

The mismatch should become Evidence so the operator can approve or reject the
actual plan, not only the model's explanation.

### 9. Autonomous / Unattended Mode

Auto-approve, unattended, or YOLO-like workflows increase conditional delivery
risk. Policy should apply stricter fail-closed defaults in those modes.

Mode warnings should be visible to the operator and included in Evidence when a
workflow relies on automation.

## Suggested Policy Metadata

Future policy gate evidence should use structured metadata such as:

- `policy_id`
- `policy_name`
- `category`
- `severity`
- `outcome`
- `reason`
- `matched_surface`
- `redaction_status`
- `affected_paths`
- `affected_commands`
- `allowed_roots_snapshot`
- `related_case_id`
- `related_action_id`
- `related_decision_id`
- `related_evidence_id`
- `transparency_event_id` when available
- `remaining_risks`

The metadata should be stable enough for Proof Packet export and narrow enough
to avoid storing unnecessary secret-bearing material.

## Operator Decision Requirements

`require_decision` outcomes need explicit operator approval. Approval should
name the exact preview or action it applies to.

Changing target paths, command arguments, backup IDs, restore preview IDs, or
allowed roots invalidates the approval. The operator decision should record the
rationale and remaining risks.

Backend safety rejection text should remain visible to the operator. A policy
gate must not hide or replace a backend refusal.

## Logging And Evidence

Future policy gate results should become Evidence. The Agent Transparency Log
should record a `policy_gate_triggered` event that links the proposal, preview,
policy result, operator decision, and execution result when execution happens.

Proof Packet export should include selected policy outcomes, preview and
decision references, execution evidence, test evidence, and remaining risks.

Logs should prefer hashes or redacted snippets when raw payloads may expose
secrets. Redaction must be recorded; secret-risk material should not be silently
omitted.

## Failure Modes

- Policy evaluation unavailable before a dangerous action should fail closed.
- Redaction failure when secrets may be present should fail closed.
- Policy mismatch between preview and execution should invalidate approval.
- Policy results must not replace backend safety checks.
- `allow` and `warn` outcomes do not prove that an action is safe.
- Evidence logs preserve what ProofFlow received and processed, not necessarily
  what an upstream model originally produced.

## Future Implementation Sketch

Possible future implementation pieces include:

- `policy_gate_service.py`
- a local policy configuration file
- ActionGuard integration for filesystem and restore actions
- AgentGuard command review integration
- a UI risk panel for operator decisions
- tests for `block`, `warn`, `require_decision`, and `fail_closed` outcomes
- Proof Packet export selection for policy gate evidence

This PR does not implement these pieces.

## References

- [Agent Intermediary Tampering Threat Model](threat_models/AGENT_INTERMEDIARY_TAMPERING.md)
- [Agent Transparency Log Foundation](agent_transparency_log.md)
- [Action Safety](action_safety.md)
- [Managed Backup / Restore](managed_backup_restore.md)
- [Proof Packet](proof_packet.md)
- [Repository Agent Rules](../AGENTS.md)
