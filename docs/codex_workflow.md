# ProofFlow + AI Coding Agent Workflow

> All examples in this document are verified against real ProofFlow v0.1.0 output.
> Reproduce with: `python scripts/generate_real_docs_output.py`

## Overview

ProofFlow acts as an audit layer between AI coding agents (Claude Code, Codex, etc.)
and your filesystem. Every action the agent takes is recorded, gated, and exportable
as a Proof Packet.

## Setup

All commands below assume the working directory is the parent directory that
contains the freshly cloned `ProofFlow-v0.1` repository, and that you are using
a single PowerShell session. Each block uses `Push-Location` / `Pop-Location`
to enter the right subdirectory and restore cwd afterwards, so subsequent
blocks can be pasted in the same session without manual `cd` adjustments. The
backend port is fixed to `8787` to match the `README.md` and `make dev-backend`
baseline.

### 1. Start ProofFlow backend

```powershell
Push-Location ProofFlow-v0.1\backend
pip install -r requirements.txt
python -m uvicorn proofflow.main:app --port 8787
Pop-Location
```

### 2. Connect via MCP

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "proofflow": {
      "command": "proofflow-mcp",
      "env": { "PROOFFLOW_BASE_URL": "http://127.0.0.1:8787" }
    }
  }
}
```

### 3. Install MCP server

The `mcp-server\` path is repo-root relative; the `Push-Location` block enters
the cloned repository root from the parent directory used in step 1.

```powershell
Push-Location ProofFlow-v0.1
pip install -e mcp-server\
Pop-Location
```

## Available MCP Tools (13 total)

| Tool | Purpose | Verified |
|------|---------|----------|
| `proofflow_health` | Check backend connectivity | Yes |
| `proofflow_scan` | Scan folder, create Case + Artifacts with SHA-256 | Yes |
| `proofflow_suggest` | Generate file organization actions | Yes |
| `proofflow_review` | AgentGuard code review on git repo | Yes |
| `proofflow_triage_issue` | Triage issue text into a Case | Yes |
| `proofflow_approve_execute` | Approve and execute a pending action | Yes |
| `proofflow_decide` | Resolve a policy gate (approve/reject) | Yes |
| `proofflow_export_packet` | Export Case as Proof Packet (Markdown) | Yes |
| `proofflow_status` | Get Case status with all details | Yes |
| `proofflow_search` | Full-text search across indexed artifacts | Yes |
| `proofflow_list_cases` | List all Cases | Yes |
| `proofflow_list_actions` | List actions for a Case | Yes |
| `proofflow_undo` | Undo an executed action (hash-verified) | Yes |

All tools verified via `scripts/mcp_smoke.py` (end-to-end test).

## Real Workflow Example

The following is actual output from ProofFlow v0.1.0:

### Step 1: Scan a project directory

```
> proofflow_scan(folder_path="./my_project")

Scan complete. Case ID: 6ac9c19d-f11a-4de0-abb6-1516d7fa57a7
Files seen: 4
Artifacts created: 4
Text chunks indexed: 2
Skipped: 0
```

What happened:
- Created a Case (audit container)
- Captured 4 Artifacts with SHA-256 hashes
- Indexed text content for full-text search

### Step 2: Generate organization suggestions

```
> proofflow_suggest(case_id="6ac9c19d-...", target_root="./organized")

Suggestions generated for Case: 6ac9c19d-f11a-4de0-abb6-1516d7fa57a7
Actions created: 3
Skipped: 2

Suggested actions:
  [1b3677b6-...] mkdir: ./organized/Notes
  [2622e78d-...] move_file: notes.txt -> ./organized/Notes/notes.txt
  [76222b68-...] move_file: README.md -> ./organized/Notes/README.md
```

### Step 3: Execute an action (policy gate triggers)

```
> proofflow_approve_execute(action_id="76222b68-...")

Action 76222b68-... is blocked by a policy gate (pending_decision).
Owner approval is required before this action can execute.
```

The `move_file` action is classified as high-risk. ProofFlow automatically pauses
execution and requires explicit owner approval.

### Step 4: Resolve the policy gate

```
> proofflow_decide(case_id="6ac9c19d-...", action_id="76222b68-...",
                   decision="accepted",
                   rationale="Approved after reviewing the move target")

Decision created.
ID: b0d88d9b-357f-46a1-a3b6-a0b6ab2e6c70
Status: accepted
Rationale: Approved after reviewing the move target
```

After the decision, re-executing the action will complete the file move.

### Step 5: Code review (AgentGuard)

```
> proofflow_review(repo_path="./code_repo")

Code review complete. Case ID: d7bd3a18-7e1b-4854-8372-51a594b0f6b8
Risk level: info
Changed files: 1
Claims created: 1
Evidence created: 1

Changed files:
  - auth.py
```

### Step 6: Export Proof Packet

```
> proofflow_export_packet(case_id="6ac9c19d-...")

Proof Packet exported for Case: 6ac9c19d-f11a-4de0-abb6-1516d7fa57a7
File: 6ac9c19d-f11a-4de0-abb6-1516d7fa57a7.md
```

The Proof Packet is a Markdown file containing the full audit trail:
artifacts, actions, decisions, evidence, and policy gate observations.

See [docs/examples/proof_packet_codex_review.md](examples/proof_packet_codex_review.md)
for the complete exported packet.

## Policy Gate Behavior

When an AI agent tries to execute a high-risk action:

1. Agent calls `proofflow_approve_execute` → action approved + execute attempted
2. ProofFlow classifier identifies `move_file` as high-risk
3. Action status becomes `pending_decision` — file is NOT moved
4. Agent receives message: "blocked by policy gate"
5. Owner (or agent) calls `proofflow_decide` with `decision="accepted"`
6. Agent re-executes → file moves successfully

If rejected: file stays put, action marked `rejected`, evidence recorded.

Safety semantics:
- **Fail-open**: If the classifier crashes, action executes normally (no false blocks)
- **Fail-closed**: Once gated, only a valid Decision can unblock

## Security Model

- All data stays local (SQLite + filesystem)
- No cloud sync, no telemetry
- Actions scoped to `allowed_roots` (cannot escape project directory)
- Sensitive files (.env, .pem, .key, .db) automatically excluded
- Policy gates enforce human-in-the-loop for destructive operations
- SHA-256 hash verification on undo operations

## Verification

Run the end-to-end smoke test from the cloned repository root in PowerShell.
The `Push-Location` block makes cwd explicit so the `scripts\` path resolves
without relying on an implicit `cd` from the Setup section above.

```powershell
Push-Location ProofFlow-v0.1
python .\scripts\mcp_smoke.py --cleanup
Pop-Location
```

Expected output:
```
  [PASS] proofflow_health
  [PASS] proofflow_scan + suggest + list_actions + status + export_packet
  [PASS] proofflow_review
  [PASS] proofflow_search
  [PASS] proofflow_list_cases

All MCP smoke checks passed.
```
