# ProofFlow Maintainer Plugin

This Codex plugin gives maintainers a small set of ProofFlow-first workflows
inside a repository:

- review the current diff with ProofFlow,
- create or export a Proof Packet for a PR,
- triage issue text into a local ProofFlow Case.

It is intentionally thin. The plugin does not embed a backend, upload data, or
replace maintainer judgment. It connects Codex to the local ProofFlow MCP server
and adds a skill that keeps maintenance work evidence-backed.

## Requirements

- ProofFlow backend running on `http://127.0.0.1:8787`
- `proofflow-mcp` available on `PATH`

## Repo-Local Discovery

This repository includes a Codex marketplace entry at
[`../../.agents/plugins/marketplace.json`](../../.agents/plugins/marketplace.json).
It points to this plugin with `installation: AVAILABLE`, so Codex can discover
the repo-local plugin without a global install.

The plugin itself lives entirely under `plugins/proofflow-maintainer/`:

- `.codex-plugin/plugin.json` defines the plugin metadata and default prompts.
- `.mcp.json` declares the local ProofFlow MCP server.
- `skills/proofflow-maintainer/SKILL.md` defines the maintainer workflow
  behavior Codex should follow.

Install the MCP server from PyPI:

```bash
pip install proofflow-mcp
```

Start the backend from the repository root:

```bash
cd backend
python -m uvicorn proofflow.main:app --port 8787
```

## What The Plugin Adds

The plugin declares a `proofflow` MCP server:

```json
{
  "mcpServers": {
    "proofflow": {
      "command": "proofflow-mcp",
      "env": {
        "PROOFFLOW_BASE_URL": "http://127.0.0.1:8787"
      }
    }
  }
}
```

It also contributes a Codex skill with maintainer-oriented workflows. The
default prompts are:

- `Review the current diff with ProofFlow.`
- `Create a Proof Packet for this PR.`
- `Triage this issue into a ProofFlow Case.`

## Workflow Boundaries

- The plugin keeps ProofFlow's localhost trust boundary.
- The current review workflow is provenance-first: it captures the reviewed
  diff, changed files, risk status, and Proof Packet, but it should not be
  described as a complete semantic code review unless the claims and evidence
  actually support that.
- PR Proof Packets must be reviewed against the PR base ref. A clean committed
  PR checkout has no uncommitted diff, so relying on the ProofFlow default
  `HEAD` base would produce an empty packet instead of the PR changes.
- Short PR base names such as `main` must be resolved before review. In GitHub
  Actions, `GITHUB_BASE_REF` is a target branch name, and a clean checkout may
  not have a local branch with that name. Fetch or resolve the base to a local
  ref, compute `git merge-base HEAD <resolved-base-ref>`, and pass that SHA as
  `base_ref`.
- Issue triage uses `proofflow_triage_issue` to create a first-class
  `issue_triage` Case with source issue text, deterministic triage Claims,
  component inference, label suggestions, and Proof Packet export support.
- It does not execute tests unless the user explicitly asks for that workflow
  and the backend allows test command execution.
- It does not merge PRs, close issues, or bypass policy gates.
- It should report missing evidence as an assumption rather than a final claim.

## Dogfood Result

The first dogfood pass covered the three default prompts against this plugin
PR:

- `Review the current diff with ProofFlow.` created a code review Case and
  exported a Proof Packet for the plugin PR diff.
- `Create a Proof Packet for this PR.` worked when given the existing Case ID.
- `Triage this issue into a ProofFlow Case.` creates a first-class
  `issue_triage` Case with issue text as the primary Artifact and triage
  Claims for component, reproduction steps, expected behavior, and environment
  completeness.

The result was usable for maintainer provenance and packet creation. The main
remaining review boundary is that AgentGuard output is only as semantic as the
Claims and Evidence produced by deterministic rules.
