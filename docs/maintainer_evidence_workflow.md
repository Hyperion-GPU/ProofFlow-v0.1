# Maintainer Evidence Workflow

ProofFlow helps maintainers keep AI-assisted maintenance work reviewable. It
turns issue triage, pull request review, release checks, local file workflows,
and high-risk actions into auditable Cases with source Artifacts, supporting
Evidence, review Claims, proposed Actions, maintainer Decisions, and exportable
Proof Packets.

The goal is not to replace maintainer judgment. The goal is to make the path to
that judgment easier to inspect after the fact.

## Maintenance Problems

AI-assisted maintenance is useful, but it often leaves important context spread
across chat transcripts, terminal output, issue comments, and local files. That
makes it hard to answer practical questions later:

- Which source files, diffs, logs, or issue text were actually reviewed?
- Which review findings were backed by evidence, and which were assumptions?
- Which actions were previewed before execution?
- Which high-risk actions required an explicit maintainer decision?
- Which workflow outputs can be shared with another maintainer or attached to a
  pull request?

ProofFlow treats those questions as product requirements. A maintenance task
starts with a Case, records sources as Artifacts, links Claims to Evidence, and
keeps risky Actions behind preview, approval, policy gate, and undo boundaries.

## Workflow Model

ProofFlow's maintenance workflow is intentionally small:

| Concept | Maintainer meaning |
|---------|--------------------|
| Case | One review, triage task, release check, or local workflow |
| Artifact | Source material such as files, diffs, logs, packets, or issue text |
| Evidence | A verifiable fact extracted from an Artifact or command result |
| Claim | A review judgment that points back to Evidence |
| Action | A proposed filesystem or workflow change with preview and status |
| Decision | A maintainer approval, rejection, or policy gate resolution |
| Proof Packet | A Markdown audit report that can be shared or archived |

This model is deliberately local-first. ProofFlow keeps the default trust
boundary at localhost and does not require remote sync, telemetry, or cloud
execution for the v0.1 workflows.

## Example: PR Review

For a pull request review, a maintainer can run AgentGuard against the current
git diff. ProofFlow creates a Case, stores the diff and optional command output
as Artifacts, generates evidence-backed review Claims, and exports a Proof
Packet.

A useful PR review packet should show:

- the base and head context that was reviewed,
- the changed files used as evidence,
- the claims produced from that evidence,
- the risk level and any skipped checks,
- the commands that were intentionally run or intentionally not run,
- the final result a maintainer can paste into a PR discussion.

The repository includes a real exported example:
[`docs/examples/proof_packet_codex_review.md`](examples/proof_packet_codex_review.md).

The GitHub Actions workflow described in
[`docs/code_review.md`](code_review.md) publishes a stable PR comment and
uploads the Proof Packet plus raw review artifacts. This is audit-only
visibility; it does not block merges or make the final maintainer decision.

## Example: Local File Workflow

LocalProof applies the same evidence workflow to local files. A maintainer can
scan a folder, create Artifacts with SHA-256 hashes, generate organization
suggestions, preview the proposed Actions, approve and execute them, and keep
undo metadata for destructive operations.

Recent dogfood runs focused on practical usability:

- action cards keep a stable review order while their status changes,
- policy-gated actions explain the two-step owner decision flow,
- Execute is unavailable until the required owner decision is recorded,
- executed file moves retain undo metadata and can be reversed.

Those details matter because a local workflow is not just a backend API. During
review, a maintainer needs the active item to stay trackable and the next safe
step to be visible.

## Safety Invariants

ProofFlow's workflow is shaped by safety invariants rather than model trust:

- No Case, no workflow.
- No Source, no Artifact.
- No Evidence, no trusted Claim.
- No Preview, no Action.
- No Undo, no destructive Action.
- No Test, no accepted code workflow.

These invariants are implemented across backend services, frontend UI, MCP
tools, documentation, and dogfood checks. If an output lacks the required
source, evidence, preview, decision, or undo path, it should be treated as
incomplete instead of silently accepted.

## Dogfood Evidence

ProofFlow is maintained through its own workflows. Recent repository history
includes:

- PR #94: AgentGuard dogfood review story with a ProofFlow-generated PR comment
  and downloadable audit artifact.
- PR #95 and #96: CI dogfood evidence and audit artifact hardening.
- PR #97 and #98: post-dependency dogfood notes and release evidence drafts.
- PR #101: LocalProof UX fixes for stable action ordering, policy gate clarity,
  accessible action names, and a small brand icon.
- Issues #99 and #100: real usability reports that were fixed, merged, and
  retested through the LocalProof workflow.

This evidence is intentionally concrete. It shows the project using the same
Case, Artifact, Claim, Action, Decision, and Proof Packet vocabulary that it
offers to other maintainers.

## Current Boundaries

ProofFlow does not try to automate every maintainer responsibility:

- It does not make final merge decisions.
- It does not bypass policy gates.
- It does not treat AI output as trusted without evidence.
- It does not require cloud sync or remote execution for local workflows.
- It does not run AgentGuard test commands unless that boundary is explicitly
  enabled.

These boundaries keep the v0.1 scope focused on local evidence, reviewability,
and reversible action workflows.

## Next Improvements

The next useful improvements are the ones that reduce maintainer friction
without weakening the evidence model:

- clearer onboarding for first-time maintainers,
- more ergonomic Proof Packet export and sharing,
- optional editor and agent integrations,
- better retrieval for large repositories,
- shared Cases for multi-agent review,
- notification hooks for policy gate decisions.

Each improvement should preserve the same baseline: source material is captured,
claims point to evidence, risky actions are previewed, and maintainer decisions
remain explicit.

## How To Try It

Start the backend and frontend, then try one of the maintenance workflows:

```bash
# Backend
cd backend
python -m uvicorn proofflow.main:app --port 8787

# Frontend
cd frontend
npm run dev
```

For code review, run AgentGuard with the MCP server or backend workflow and
export the resulting Proof Packet. For local file review, open LocalProof,
scan a temporary folder, generate suggestions, review the previews, and execute
or reject each Action.

Keep test runs isolated by setting temporary `PROOFFLOW_DB_PATH` and
`PROOFFLOW_DATA_DIR` values when dogfooding against real repositories or local
folders.
