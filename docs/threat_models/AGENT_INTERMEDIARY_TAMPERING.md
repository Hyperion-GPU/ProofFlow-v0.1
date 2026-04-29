# Agent Intermediary Tampering Threat Model

## Summary

This document describes a defensive threat model for malicious or compromised
agent intermediaries. In ProofFlow terms, model, router, MCP, and tool
middleware output is a proposal, not a trusted action.

The design principle is simple: never trust a tool call because it appears to
come from the model. Trust starts only after local validation, evidence capture,
preview, and an explicit operator decision.

This threat model reinforces the existing ProofFlow invariants:

- No Preview, no Action.
- No Evidence, no trusted Claim.
- No Test, no accepted code workflow.
- No Undo, no destructive Action.

## Assets At Risk

Intermediary tampering can affect any local asset that an agent can observe,
describe, or operate on:

- Local filesystem contents.
- Source repositories.
- ProofFlow SQLite database and data directory.
- Proof Packets.
- Secrets accidentally present in prompts, tool payloads, environment
  variables, diffs, logs, or generated reports.
- Backup archives and restore targets.
- Operator trust in generated action plans.

## Threat Actors And Intermediaries

The relevant actors are any system between the operator, the local client, the
model, and tools that can observe or rewrite requests, responses, or tool-call
payloads:

- Malicious or compromised LLM API router.
- Malicious or compromised MCP server.
- Tool-call middleware or proxy.
- Dependency or package source substituted by a tampered command.
- Benign-but-compromised intermediary that leaks or rewrites traffic.

## Attack Surfaces

ProofFlow treats the following surfaces as high risk when agent output is
translated into local action:

- Tool-call JSON rewrite.
- Shell command argument rewrite.
- Filesystem action rewrite.
- Dependency or package substitution.
- Secret observation or exfiltration.
- Conditional payload delivery when autonomous or YOLO-like mode is detected.
- Model explanation and executable action-plan mismatch.
- Restore or backup target path tampering.

## Current ProofFlow Mitigations

ProofFlow already mitigates part of this threat class through local-first
workflow gates and evidence preservation:

- Model or router output becomes a proposed Action, not direct execution.
- Preview gates expose planned writes before action execution.
- A human-visible Decision layer records approval, rejection, and operator
  outcome.
- Case, Claim, Evidence, Action, and Decision records preserve the reviewable
  workflow trail.
- Allowed roots and filesystem safety boundaries restrict local file actions.
- SHA-256 guarded undo protects reversible filesystem actions where available.
- Managed backup and restore require manifest, verify, preview, and hash gates.
- Restore-to-new-location is inspection evidence, not proof that live restore is
  safe.
- Code workflows require test evidence before acceptance.
- Proof Packet export supports post-hoc audit.
- Local-first design keeps the default trust boundary on localhost instead of a
  remote service.

## Gaps / Non-Mitigations

ProofFlow must be explicit about what it does not solve:

- ProofFlow cannot cryptographically prove that an upstream model response was
  not modified by a router unless upstream providers or protocols support
  response signing or similar provenance.
- A router can passively observe plaintext secrets before the local client sees
  the payload.
- A malicious intermediary that stays within allowed local policy may still
  influence low-risk plans.
- Existing evidence logs can preserve what ProofFlow received, not necessarily
  what the upstream model originally produced.
- Autonomous or auto-approve modes remain high risk unless fail-closed local
  gates are enabled.

## Design Requirements For Future AgentGuard / ActionGuard Hardening

Future hardening should stay client-side, local-first, and fail-closed for
dangerous operations:

- Append-only local agent/tool-call transparency log.
- Raw response hash and normalized action-plan hash.
- Router or base URL trust labels.
- High-risk command policy gate.
- Fail-closed option for dangerous tools.
- Response-side anomaly screening for returned tool calls and action plans.
- Diff between natural-language explanation and executable action plan.
- Detection for network calls, secret access, install scripts, package manager
  commands, credential paths, and writes outside allowed roots.
- Mode warnings for unattended, autonomous, or YOLO-like workflows.
- Backup and restore preflight if destructive actions are ever introduced.

These requirements are design gates. They do not authorize Phase 5 live restore
or any destructive restore implementation.

## Proposed Policy Gates

Policy gates should produce Evidence and require a Decision instead of silently
executing risky operations. Defensive examples include:

- Block or require explicit decision for remote installer command patterns.
- Block or require explicit decision for package installation from untrusted
  registries.
- Block writes outside `source_root`, `target_root`, or `allowed_roots`.
- Block attempts to read common secret filenames or credential paths unless the
  operator explicitly approves the need.
- Require tests before accepting a code workflow.
- Require backup and restore evidence before any future destructive restore
  design can be considered.

## Evidence Model

A future transparency log should record enough metadata to compare what the
agent claimed, what it proposed, what the operator approved, and what actually
ran:

- Case ID.
- Run ID.
- Provider, router, or configured base URL label.
- Request metadata hash.
- Response body hash where safe.
- Returned tool-call envelope hash.
- Normalized action plan hash.
- Preview result hash.
- Decision ID and operator outcome.
- Execution result.
- Diff and test evidence.
- Remaining risks.

The log should avoid storing secrets in plaintext. When raw payload capture is
unsafe, ProofFlow should prefer hashes, redacted snippets, and explicit
redaction Evidence.

## Recovery Model

ProofFlow recovery should remain previewed, verified, and evidence-backed:

- Use undo for reversible filesystem actions.
- Verify managed backups before trusting them.
- Use restore preview before any restore action.
- Use restore-to-new-location as inspection evidence only.
- Any future live restore must require separate design review, pre-restore
  backup, offline or maintenance mode, an exact operator decision gate, and
  rollback evidence.

## Non-Goals

This document does not:

- Implement Phase 5 live restore.
- Add cryptographic model-response provenance.
- Endorse autonomous execution.
- Add cloud sync or router integration.
- Replace provider-side signing or secure transport guarantees.
- Add backend or frontend product behavior.

## References

- "Your Agent Is Mine: Measuring Malicious Intermediary Attacks on the LLM
  Supply Chain", arXiv:2604.08407, https://arxiv.org/abs/2604.08407.
- `AGENTS.md`.
- `docs/mvp_scope.md`.
- `docs/proof_packet.md`.
- `docs/code_review.md`.
- `docs/managed_backup_restore.md`.
- `docs/action_safety.md`.
