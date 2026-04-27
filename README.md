# ProofFlow v0.1

ProofFlow is a local-first workflow dashboard for evidence-backed work. It keeps
cases, artifacts, claims, evidence, actions, decisions, runs, and reports on
localhost so a human can inspect what happened before trusting an AI or
heuristic result.

## MVP branches

- LocalProof: file evidence manager for local cases and artifacts.
- AgentGuard: code review workflow that links every claim to evidence.

## Current status

- Core Case / Artifact / Evidence / Action / Decision / Report workflows have
  an MVP service and API skeleton.
- LocalProof supports folder scans, file hash and metadata capture, text chunks,
  FTS search, and previewable suggested actions.
- AgentGuard supports local git diff review, changed-file tracking, optional
  test commands, and evidence-backed claims.

## Stack

- Backend: Python, FastAPI, SQLite
- Frontend: React, TypeScript, Vite
- Runtime: local machine only

No cloud services and no Docker are part of v0.1.

## Quickstart backend

PowerShell:

```powershell
cd "D:\ProofFlow v0.1\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
```

Run backend tests:

```powershell
cd "D:\ProofFlow v0.1\backend"
python -m pytest
```

## Quickstart frontend

PowerShell:

```powershell
cd "D:\ProofFlow v0.1\frontend"
npm install
npm run dev
```

Open `http://127.0.0.1:5173` unless Vite reports a different local port.

## Demo seed

PowerShell:

```powershell
cd "D:\ProofFlow v0.1"
python .\scripts\demo_seed.py
```

The demo seed creates local sample data under the repository demo roots and
prints backend/frontend commands for that seeded database.

## Dogfood v0.1

Use [docs/V0_1_DOGFOOD.md](docs/V0_1_DOGFOOD.md) for the local demo and smoke
gate path from demo seed through LocalProof, AgentGuard, and Proof Packet export.

For the RC safety baseline, use [docs/action_safety.md](docs/action_safety.md)
for filesystem action scope rules and [docs/reset_backup.md](docs/reset_backup.md)
for local reset and backup commands.

## Make targets

This repository includes placeholder targets for common workflows:

```powershell
make setup
make test
make dev-backend
make dev-frontend
```

`make` was not detected on this Windows machine during initial planning, so the
PowerShell commands above are the primary run path for now.

## Safety model

- No Case, no workflow.
- No Evidence, no trusted Claim.
- No Preview, no Action.
- No Undo, no destructive Action.
- No Test, no accepted code workflow.
- No Source, no Artifact.
- Destructive file actions must be previewed, approved, and paired with an undo
  path before execution.
- ProofFlow stores local workflow data in SQLite by default.
- The backend database defaults to `backend\data\proofflow.db`; set
  `PROOFFLOW_DB_PATH` to override it.
- Filesystem actions require explicit local `allowed_roots` metadata and cannot
  operate on ProofFlow's own database, data directory, or proof packet directory.

## Known limitations

- No multi-user workflow.
- No cloud sync.
- No vector RAG.
- No ComfyUI execution.
- Deterministic heuristics first; no automatic AI code edits.
