# ProofFlow v0.1

ProofFlow is a local-first AI workflow dashboard MVP for evidence-backed work.
It keeps cases, files, review notes, actions, and decisions on localhost so a
human can inspect what happened before trusting an AI or heuristic result.

## MVP branches

- LocalProof: file evidence manager for local cases and artifacts.
- AgentGuard: code review workflow that links every claim to evidence.

This step only creates the initial runnable skeleton. It does not implement the
full Case / Artifact / Evidence / Action / Decision workflow yet.

## Stack

- Backend: Python, FastAPI, SQLite
- Frontend: React, TypeScript, Vite
- Runtime: local machine only

No cloud services and no Docker are part of v0.1.

## Run backend

PowerShell:

```powershell
cd "D:\ProofFlow v0.1\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn proofflow.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Run backend tests:

```powershell
cd "D:\ProofFlow v0.1\backend"
python -m pytest
```

## Run frontend

PowerShell:

```powershell
cd "D:\ProofFlow v0.1\frontend"
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://127.0.0.1:5173`.

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

## Safety rules

- Destructive file actions must be planned as dry-run first, then approved, then
  paired with an undo path.
- AI or heuristic claims are not accepted without evidence.
- ProofFlow stores local workflow data in SQLite by default.
- The backend database defaults to `backend\data\proofflow.db`; set
  `PROOFFLOW_DB_PATH` to override it.
