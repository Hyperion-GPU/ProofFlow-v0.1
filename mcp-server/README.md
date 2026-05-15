# ProofFlow MCP Server

<!-- mcp-name: io.github.Hyperion-GPU/proofflow -->

MCP (Model Context Protocol) server that exposes ProofFlow's audit capabilities as tools for Claude Code and Codex.

## What it does

Lets AI coding assistants trigger ProofFlow workflows directly:

- **Scan folders** — index files with SHA-256 hashes, create audit Cases
- **Code review** — analyze git diffs, generate evidence-backed risk claims
- **Suggest actions** — generate file organization suggestions
- **Approve & execute** — run pending actions (with policy gate awareness)
- **Export Proof Packets** — generate shareable markdown audit reports
- **Search** — full-text search across indexed artifacts
- **Undo** — reverse executed actions

## Prerequisites

- Python 3.11+
- ProofFlow backend running on `http://127.0.0.1:8787`

## Installation

```bash
cd mcp-server
pip install -e .
```

For development (includes test dependencies):

```bash
pip install -e ".[dev]"
```

> Note: Install in a separate virtualenv from the backend to avoid starlette version conflicts between FastAPI and the MCP SDK.

## Configuration

### Claude Code

Add to your project's `.mcp.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "proofflow": {
      "command": "python",
      "args": ["-m", "proofflow_mcp"],
      "env": {
        "PROOFFLOW_BASE_URL": "http://127.0.0.1:8787"
      }
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

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

### Codex

Add to your Codex MCP configuration with the same command/args pattern.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROOFFLOW_BASE_URL` | `http://127.0.0.1:8787` | ProofFlow backend URL |
| `PROOFFLOW_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `PROOFFLOW_API_KEY` | *(unset)* | API key for backend auth (optional) |
| `PROOFFLOW_MCP_MAX_CONCURRENT` | `5` | Max concurrent MCP tool calls |

AgentGuard `test_command` requests are disabled by default in the backend. Set
`PROOFFLOW_ENABLE_TEST_COMMANDS=true` on the ProofFlow backend only when you want
MCP clients to run local test commands during review.

## Available Tools

| Tool | Description |
|------|-------------|
| `proofflow_health` | Check backend connectivity |
| `proofflow_scan` | Scan a folder, create Case + Artifacts |
| `proofflow_suggest` | Generate cleanup suggestions for a scanned Case |
| `proofflow_review` | AgentGuard code review on a git repo |
| `proofflow_status` | Get full Case status (artifacts, claims, actions) |
| `proofflow_approve_execute` | Approve and execute a pending action |
| `proofflow_export_packet` | Export Case as Proof Packet (markdown) |
| `proofflow_search` | Full-text search across artifacts |
| `proofflow_list_cases` | List all Cases |
| `proofflow_list_actions` | List actions for a Case |
| `proofflow_undo` | Undo an executed action |
| `proofflow_decide` | Create a decision to approve/reject a policy gate |

## Usage Example

In Claude Code, once configured:

```
> Review the code changes in this repo for safety

Claude will call proofflow_review with the current repo path,
creating an AgentGuard Case with evidence-backed claims.
```

## Running Tests

```bash
cd mcp-server
python -m pytest tests/ -v
```

## Running the Server Directly

```bash
python -m proofflow_mcp
```

The server communicates via stdio (stdin/stdout) per the MCP protocol.

## Architecture

```
Claude Code / Codex
    ↓ (MCP stdio)
ProofFlow MCP Server
    ↓ (HTTP)
ProofFlow Backend (localhost:8787)
    ↓
SQLite DB + Local Files
```

The MCP server is a thin adapter — all business logic lives in the ProofFlow backend.
