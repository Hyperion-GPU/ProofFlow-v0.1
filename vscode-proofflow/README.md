# ProofFlow for VS Code

> Audit, gate, and trace every change your AI coding agent makes — without leaving the editor.

ProofFlow is a local-first audit layer for AI coding agents (Codex, Claude Code, Copilot Workspace, Cursor). This extension is the lightweight VS Code companion: a one-click "Review Last AI Changes" command, a sidebar that shows audit cases, and a status bar that surfaces actions awaiting your decision.

The extension talks to a local ProofFlow backend (`http://127.0.0.1:8787` by default). All data stays on your machine.

## Features

- **🛡 One-click AI change review** — `ProofFlow: Review Last AI Changes` runs AgentGuard on the current workspace's git diff and creates an evidence-backed Case.
- **📂 Folder scan** — `ProofFlow: Scan Current Folder` indexes every file with SHA-256 hashes for cleanup or audit.
- **🌳 Sidebar tree** — Browse all Cases. Expand to see Actions and Claims with severity-coded icons.
- **🚦 Status bar** — Online/Offline indicator plus a counter for actions pending decision.
- **✅ Gate approve** — `ProofFlow: Approve Gate & Execute` lets you pick a gated action, record the owner decision, and execute it in one step.
- **🔄 Auto-refresh** — Polls the backend every 10 seconds; configurable.

## Quick Start

### 1. Install the ProofFlow backend

```bash
git clone https://github.com/Hyperion-GPU/ProofFlow-v0.1.git
cd ProofFlow-v0.1
docker compose up
```

Or run it locally:

```bash
cd ProofFlow-v0.1/backend
pip install -r requirements.txt
python -m uvicorn proofflow.main:app --port 8787
```

### 2. Install the extension

Search **ProofFlow** in the VS Code marketplace, or install from a `.vsix`:

```bash
code --install-extension proofflow-0.1.0.vsix
```

### 3. Use it

1. Open any git project in VS Code.
2. The status bar should show `🛡 ProofFlow` (green = online).
3. Open the command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) → run **ProofFlow: Review Last AI Changes**.
4. Open the ProofFlow sidebar (shield icon in the activity bar) to see the new Case with its Claims.

## Commands

| Command | What it does |
|---|---|
| `ProofFlow: Review Last AI Changes` | Runs AgentGuard on the current workspace and creates a code-review Case. |
| `ProofFlow: Scan Current Folder` | Indexes every file in the workspace as artifacts. |
| `ProofFlow: Approve Gate & Execute` | Quick-pick a gated action, record the owner decision, and execute it. |
| `ProofFlow: Show Logs` | Open the ProofFlow output channel for debugging. |
| `Refresh` (sidebar title bar) | Force a tree refresh. |

## Configuration

| Setting | Default | Description |
|---|---|---|
| `proofflow.backendUrl` | `http://127.0.0.1:8787` | URL of the ProofFlow backend server. |
| `proofflow.apiKey` | `""` | Optional `X-ProofFlow-Token` for authenticated backends. |
| `proofflow.autoRefresh` | `true` | Poll the backend every 10 seconds for status and pending actions. |

## How it fits with the rest of ProofFlow

```
┌──────────────┐   POST /agentguard/review    ┌──────────────────┐
│   VS Code    │ ───────────────────────────▶ │ ProofFlow backend│
│  extension   │ ◀─────── case_id, claims ─── │   (localhost)    │
└──────────────┘                              └──────────────────┘
                                                       │
                                                       ▼
                                              SQLite + content store
                                              (everything stays local)
```

The backend exposes a REST API. The same backend powers:
- A web frontend
- An MCP server (so agents can self-audit through tool calls)
- A CLI

This extension is a thin client; you can run multiple clients against the same backend.

## Troubleshooting

**Status bar shows `ProofFlow: Offline`**
The backend isn't reachable. Start it (see Quick Start) or check `proofflow.backendUrl`.

**`No workspace folder open`**
Open a folder via `File → Open Folder...` first. The Review command needs a git repo to diff.

**Sidebar shows "No cases found" after a successful review**
Click the 🔄 refresh button in the sidebar header, or wait for the next 10-second poll.

**See what's happening under the hood**
Run `ProofFlow: Show Logs` to open the output channel — every API call is logged with status and response shape.

## Repository

Source, issues, roadmap: https://github.com/Hyperion-GPU/ProofFlow-v0.1

## License

MIT — see [LICENSE](LICENSE).
