# ProofFlow

[![Backend](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/workflows/backend.yml/badge.svg)](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/workflows/backend.yml)
[![Frontend](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/workflows/frontend.yml/badge.svg)](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/workflows/frontend.yml)
[![MCP Server](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/workflows/mcp-server.yml/badge.svg)](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/workflows/mcp-server.yml)

**Local-first audit infrastructure for AI coding agents.**

ProofFlow gives developers a verifiable evidence trail for every action an AI agent takes on their codebase. It enforces safety invariants — no file moves without preview, no claims without evidence, no destructive actions without undo — and produces exportable Proof Packets for compliance and review.

## Problem

AI coding agents (Claude Code, Codex, Copilot Workspace) can modify files, run commands, and make decisions autonomously. But there's no standard way to:

- **Audit** what an agent did and why
- **Gate** high-risk actions before they execute
- **Prove** that a code review actually checked what it claims
- **Undo** agent-initiated changes with confidence

ProofFlow solves this by sitting between the agent and the filesystem, creating an evidence graph that links every action to its justification.

## Quickstart

### Docker (recommended)

```bash
git clone https://github.com/Hyperion-GPU/ProofFlow-v0.1.git
cd ProofFlow-v0.1
docker compose up
```

Backend: http://localhost:8787 | Frontend: http://localhost:5173

### Manual

```bash
# Backend
cd backend && pip install -r requirements.txt
python -m uvicorn proofflow.main:app --port 8787

# Frontend
cd frontend && npm ci && npm run dev
```

### MCP Integration (Claude Code / Codex)

```bash
pip install proofflow-mcp
```

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

Now your AI agent can scan files, review code, suggest actions, and export audit reports — all with enforced safety gates.

## Architecture

```
AI Agent (Claude Code / Codex / Custom)
    |
    | MCP Protocol (stdio)
    v
ProofFlow MCP Server (12 tools)
    |
    | HTTP REST API
    v
ProofFlow Backend (FastAPI + SQLite)
    |
    |--- Evidence Graph: Cases > Artifacts > Claims > Evidence
    |--- Action Pipeline: Preview > Approve > Execute > Undo
    |--- Policy Gates: Risk classification > Owner decision
    |--- Proof Packets: Exportable markdown audit reports
    v
Local Filesystem (scanned files, git repos)
```

## Core Capabilities

### Evidence-Backed Code Review (AgentGuard)
Analyzes git diffs, generates risk-scored claims, and links each claim to specific evidence (changed lines, test results). No claim exists without supporting evidence.

### File Audit & Organization (LocalProof)
Scans directories, indexes files with SHA-256 hashes, extracts text for full-text search, and suggests organization actions — all tracked in an auditable Case.

### Policy Gate Enforcement
High-risk filesystem actions (moves to system paths, bulk operations) are automatically paused at `pending_decision` status. Requires explicit owner approval before execution.

### Safety Invariants
- **No Preview, no Action** — destructive operations require two-phase confirmation
- **No Evidence, no Claim** — every assertion links to verifiable data
- **No Undo, no Destructive Action** — executed actions carry rollback metadata
- **No Case, no Workflow** — all work is tracked in auditable containers

### MCP Tool Suite (12 tools)
`health` · `scan` · `suggest` · `review` · `status` · `approve_execute` · `export_packet` · `search` · `list_cases` · `list_actions` · `undo` · `decide`

## Technical Stack

| Layer | Technology | Tests |
|-------|-----------|-------|
| Backend | Python 3.12, FastAPI, SQLite | 274 |
| Frontend | React 19, TypeScript, Vite | 24 |
| MCP Server | Python, MCP SDK, httpx | 24 |
| CI | GitHub Actions (3 workflows) | — |

## Security Features

- Optional API key authentication (`PROOFFLOW_API_KEY`)
- Rate limiting (`PROOFFLOW_RATE_LIMIT`)
- MCP concurrency guards (`PROOFFLOW_MCP_MAX_CONCURRENT`)
- Filesystem action scope restrictions (allowed_roots)
- CORS locked to localhost origins

## Project Status

**v0.1.0 — Stable release.** All core workflows functional, tested, and documented.

| Milestone | Status |
|-----------|--------|
| Core evidence graph (Case/Artifact/Claim/Evidence) | Done |
| LocalProof file audit workflow | Done |
| AgentGuard code review workflow | Done |
| Policy gate enforcement | Done |
| MCP server for Claude Code/Codex | Done |
| Backup/restore with safety preview | Done |
| Docker deployment | Done |
| PyPI package (`proofflow-mcp`) | Done |

## Roadmap

- [ ] Multi-agent coordination (shared Cases across agents)
- [ ] Vector RAG for semantic evidence retrieval
- [ ] GitHub Actions integration (CI-triggered reviews)
- [ ] VS Code extension for inline audit visualization
- [ ] Cloud sync option for team workflows
- [ ] Webhook notifications for policy gate decisions

## Development

```bash
# Run all tests
cd backend && python -m pytest          # 274 tests
cd frontend && npm run test             # 24 tests
cd mcp-server && pip install -e ".[dev]" && python -m pytest  # 24 tests

# End-to-end smoke test
python scripts/mcp_smoke.py --cleanup

# Demo workflow
python scripts/demo_workflow.py
```

## License

MIT

---

Built by [Hyperion-GPU](https://github.com/Hyperion-GPU) — making AI agent workflows auditable, safe, and provable.
