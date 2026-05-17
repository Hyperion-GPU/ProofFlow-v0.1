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
2. Decide whether the user means uncommitted work or a committed PR/branch:
   - For uncommitted local work, the ProofFlow default base is acceptable.
   - For a PR, branch review, or clean committed checkout, require a PR base ref
     and pass it to ProofFlow. Do not rely on the MCP/backend default, because
     the default is `HEAD` and a clean PR checkout would produce an empty diff.
3. Choose the base ref conservatively:
   - Use the user's requested base when provided.
   - Otherwise infer the base branch name from PR context when available, such as
     `gh pr view --json baseRefName`, `GITHUB_BASE_REF`, or the repository's
     tracked default branch.
   - Treat short names like `main` as branch names, not backend-ready refs.
4. Resolve the PR base before calling ProofFlow:
   - Prefer an existing local ref such as `refs/remotes/origin/<base>` or a
     verified user-provided commit SHA.
   - If only a short branch name is available and no matching local ref exists,
     fetch the base branch from `origin` first, for example
     `git fetch --no-tags origin +refs/heads/<base>:refs/remotes/origin/<base>`.
   - Compute `git merge-base HEAD <resolved-base-ref>` and pass that merge-base
     SHA as `base_ref`.
   - If the base cannot be resolved or fetched, ask for a usable base ref before
     calling ProofFlow.
5. Call `proofflow_review` with `repo_path`. Include the resolved merge-base
   `base_ref` whenever the workflow is reviewing committed PR or branch changes.
6. Do not pass a `test_command` unless the user asked for ProofFlow to run one.
7. Export the resulting Case with `proofflow_export_packet`.
8. Read the returned Claims before describing review depth. If the only Claim is
   a broad provenance claim such as changed file count, say that the packet
   captures review provenance but does not yet contain a deep semantic review.
9. Summarize:
   - Case ID,
   - base branch inferred or requested,
   - resolved base ref or merge-base SHA used, or that the workflow reviewed
     uncommitted work against the default base,
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
2. If no Case ID exists, run a PR-base review before exporting:
   - Use the user's requested base when provided.
   - Otherwise infer the PR base branch name from
     `gh pr view --json baseRefName`, `GITHUB_BASE_REF`, or the tracked default
     branch.
   - Resolve the base to an existing local ref or commit. If only a short branch
     name is available, fetch `origin/<base>` before reviewing.
   - Compute `git merge-base HEAD <resolved-base-ref>` and pass that SHA as
     `base_ref`.
   - If the base cannot be inferred, resolved, or fetched, ask for it instead of
     falling back to a default `HEAD` diff.
3. Call `proofflow_review` with `repo_path` and the resolved merge-base
   `base_ref`. This is required for clean PR checkouts, where an unqualified
   current-diff review would omit committed PR changes or fail when a short
   branch name is not available locally.
4. Call `proofflow_export_packet`.
5. Return the packet path, base branch, resolved base ref or merge-base SHA, and
   a concise PR-ready summary.
6. Do not post to GitHub unless the user explicitly asks.

## Triage Issue Text Into A Case

Use this path when the user provides issue text, logs, reproduction steps, or a
bug report and wants it captured in ProofFlow.

1. Extract the issue `title`, `body`, optional `source_url`, and labels from the
   user's text or the current issue context.
2. Call `proofflow_triage_issue` with that data.
3. Read the returned component, suggested labels, risk level, and completeness
   signals for reproduction steps, expected behavior, and environment details.
4. Call `proofflow_status` when you need the full Claims and Evidence.
5. Export the Case with `proofflow_export_packet` if the user asks for a
   shareable triage record.
6. Summarize:
   - Case ID,
   - captured source issue URL if available,
   - inferred component,
   - suggested labels,
   - missing triage evidence,
   - evidence-backed Claims,
   - recommended next step.
7. Do not create temporary issue markdown files unless the direct triage tool is
   unavailable and the user agrees to the fallback path.

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
