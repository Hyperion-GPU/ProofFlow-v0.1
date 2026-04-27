# ProofFlow v0.1 RC Checklist

This checklist keeps the release candidate local, repeatable, and evidence
backed. Run these checks before tagging or presenting v0.1 RC output.

## Local commands

Backend:

```powershell
cd .\backend
python -m pip install -r requirements.txt
python -m pytest
python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload
```

Frontend:

```powershell
cd .\frontend
npm ci
npm run test
npm run build
npm run dev
```

Combined local release check:

```powershell
.\scripts\release_check.ps1
```

API dogfood smoke with temp DB/data paths:

```powershell
python .\scripts\rc_api_smoke.py
```

Use `--cleanup` only when you do not need to inspect the generated temp packet.

Demo seed:

```powershell
cd "D:\ProofFlow v0.1"
python .\scripts\demo_seed.py
```

## CI gates

- Backend workflow runs on pull requests and pushes to `main`.
- Backend workflow runs `python -m pytest` on Python 3.11 and 3.12.
- Frontend workflow runs on pull requests and pushes to `main`.
- Frontend workflow runs `npm ci`, `npm run test`, and `npm run build` on Node
  22.x.

## Manual dogfood flow

- Start backend on `127.0.0.1:8787`.
- Start frontend on `127.0.0.1:5173`.
- Confirm Dashboard health and case listing.
- Run LocalProof scan against a local demo folder.
- Run LocalProof suggest-actions with a local target root.
- Review action preview before approval.
- Approve and execute the prerequisite `mkdir_dir` action.
- Approve and execute the dependent `move_file` action.
- Undo the `move_file` action.
- Undo the `mkdir_dir` action if the created directory is empty.
- Run AgentGuard against a local git repository.
- Export a Proof Packet and inspect artifacts, evidence, actions, decisions, and
  remaining risks.

## Action safety checks

- Filesystem actions include `allowed_roots`.
- LocalProof actions include `source_root`, `target_root`, and `allowed_roots`.
- Actions cannot touch ProofFlow DB, data, or proof packet paths.
- `move_file` and `rename_file` undo payloads include a trusted hash guard.
- Legacy action safety migration does not crash startup if legacy files are
  missing or unreadable; it records migration failure metadata instead.

## Release evidence

- Backend pytest result is recorded.
- Frontend test and build result is recorded.
- `GET /health` shows `version: 0.1.0-rc1`, `release_stage: rc`, and
  `release_name: ProofFlow v0.1.0-rc1`.
- Dashboard shows the same RC release stamp.
- Local release helper result is recorded.
- API dogfood smoke helper result is recorded.
- Public dogfood Proof Packet example is reviewed for sensitive content.
- CHANGELOG has a `v0.1.0-rc1` entry.
- Known limitations are present and honest.

## Out of scope for v0.1 RC

- Auth and multi-user permissions.
- Cloud sync or remote storage.
- Vector RAG.
- ComfyUI execution.
- Docker or container orchestration.
- Plugin system.
- Automatic AI code edits.
