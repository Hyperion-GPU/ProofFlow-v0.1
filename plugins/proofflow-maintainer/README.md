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
- It does not execute tests unless the user explicitly asks for that workflow
  and the backend allows test command execution.
- It does not merge PRs, close issues, or bypass policy gates.
- It should report missing evidence as an assumption rather than a final claim.
