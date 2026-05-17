---
name: proofflow-maintainer
description: Use ProofFlow from Codex for maintainer workflows: review the current git diff, export Proof Packets, triage issue text into a Case, and keep claims evidence-backed.
---

# ProofFlow Maintainer

Use this skill when the user asks to use ProofFlow from Codex for repository
maintenance, including:

- review the current diff with ProofFlow,
- create or export a Proof Packet for a PR,
- triage issue text into a ProofFlow Case,
- inspect or continue an existing ProofFlow Case,
- preserve evidence, decisions, actions, and policy gates while maintaining a
  repository.

## Operating Principles

- Keep the workflow local-first. The default ProofFlow backend is
  `http://127.0.0.1:8787`.
- Prefer ProofFlow MCP tools over ad hoc notes when recording Cases, Artifacts,
  Claims, Actions, Decisions, or Proof Packets.
- Treat the current AgentGuard review as provenance-first unless the returned
  Claims contain specific semantic findings. It proves what diff was reviewed
  and what evidence was captured; it does not by itself guarantee a complete
  semantic code review.
- Do not treat AI output as trusted unless it points to evidence. If evidence
  is missing, label the statement as an assumption.
- Do not run tests through ProofFlow unless the user explicitly asks and the
  backend is configured to allow test command execution.
- Do not merge PRs, close issues, or bypass policy gates unless the user
  explicitly asks and the repository workflow allows it.

## Startup Check

Before running a ProofFlow workflow:

1. Call `proofflow_health`.
2. If the MCP server or backend is unavailable, tell the user to start the
   backend and install `proofflow-mcp` if needed:

```bash
pip install proofflow-mcp
cd backend
python -m uvicorn proofflow.main:app --port 8787
```

## Review The Current Diff

Use this path for prompts like "review current diff with ProofFlow".

1. Identify the repository root from the current workspace.
2. Choose the base ref conservatively. Use the user's requested base when
   provided; otherwise let ProofFlow use its default behavior.
3. Call `proofflow_review` with `repo_path`.
4. Do not pass a `test_command` unless the user asked for ProofFlow to run one.
5. Export the resulting Case with `proofflow_export_packet`.
6. Read the returned Claims before describing review depth. If the only Claim is
   a broad provenance claim such as changed file count, say that the packet
   captures review provenance but does not yet contain a deep semantic review.
7. Summarize:
   - Case ID,
   - risk level or review status,
   - changed file count,
   - claim and evidence counts,
   - Proof Packet path,
   - findings that have evidence,
   - assumptions or missing evidence.

## Create A Proof Packet For A PR

Use this path when a review Case already exists or when the user wants a packet
for the current PR.

1. If the user gives a Case ID, call `proofflow_status` for that Case.
2. If no Case ID exists, run the current-diff review workflow first.
3. Call `proofflow_export_packet`.
4. Return the packet path and a concise PR-ready summary.
5. Do not post to GitHub unless the user explicitly asks.

## Triage Issue Text Into A Case

Use this path when the user provides issue text, logs, reproduction steps, or a
bug report and wants it captured in ProofFlow.

1. If ProofFlow exposes a direct issue-triage tool, use it.
2. Otherwise, create a temporary local text file only after explaining the path
   and purpose, then call `proofflow_scan` on the containing folder to create a
   Case and Artifact.
3. State clearly that this fallback captures the issue as source evidence and
   makes it searchable, but does not create first-class triage Claims or Actions
   unless another ProofFlow tool records them.
4. Record follow-up actions only when the available ProofFlow tools support the
   action type. Otherwise summarize recommended next actions in the response.
5. Export a Proof Packet if the user asks for a shareable triage record.

Future improvement: a dedicated `issue_triage` backend and MCP tool could
create an issue Case directly, preserve issue metadata, extract reproduction
steps, and record follow-up Actions without the temporary-file fallback.

## Policy Gates

When an action is blocked with `pending_decision`:

1. Explain that ProofFlow requires an owner Decision before execution.
2. Use `proofflow_decide` only when the user has clearly accepted or rejected
   the gate.
3. After acceptance, call `proofflow_approve_execute` again only when the user
   wants the action executed.
4. Preserve the two-step semantics: decision first, execution second.

## Response Shape

For completed ProofFlow workflows, report:

- what Case was created or used,
- what evidence was captured,
- whether the packet is provenance-only or contains semantic Claims,
- what packet or action was produced,
- what was intentionally not done,
- the recommended next step.
