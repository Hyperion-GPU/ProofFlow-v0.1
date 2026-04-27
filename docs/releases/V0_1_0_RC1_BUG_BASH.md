# ProofFlow v0.1.0-rc1 Dogfood Bug Bash

## Goal

Validate ProofFlow v0.1.0-rc1 from a clean local checkout and collect
release-candidate bugs before starting the next feature sprint. This is a
post-release dogfood log, not a new product module or feature expansion.

This document separates the immutable published RC1 tag from the current
post-RC1 `main` dogfood path. Use the tag only when validating the exact
published snapshot. Use `main` when validating smoke-helper commits that landed
after RC1.

## Current release

- Release tag: `v0.1.0-rc1`
- Stage: pre-release / rc
- Note: `main` may contain post-RC1 smoke-helper commits; do not move the
  existing tag.

Exact published tag snapshot:

```powershell
git checkout v0.1.0-rc1
```

The commands below use current `main` for post-RC1 dogfood verification unless
a result row explicitly says it was captured on the tag.

## Local command checklist

Run these commands from PowerShell.

Start from the current `main` branch:

```powershell
git checkout main
git pull --ff-only origin main
git status --short
```

Run the release gate:

```powershell
.\scripts\release_check.ps1
```

Run the post-RC1 API dogfood smoke helper:

```powershell
python .\scripts\rc_api_smoke.py
```

The helper uses temp DB/data paths and keeps its temp output for inspection. Use
cleanup only after you no longer need the generated DB or Proof Packet:

```powershell
python .\scripts\rc_api_smoke.py --cleanup
```

Seed the local demo data when you want the browser-facing dogfood path:

```powershell
python .\scripts\demo_seed.py
```

Backend:

```powershell
cd .\backend
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

With the backend running, check release identity from another PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health | ConvertTo-Json -Depth 3
```

Open `http://127.0.0.1:5173` unless Vite reports another local port.

## Manual UI checklist

- Dashboard loads and shows backend release identity.
- Cases list loads.
- LocalProof scan works on demo folder.
- LocalProof suggest-actions creates previewable `mkdir_dir` and `move_file`.
- `mkdir_dir` approve / execute works.
- `move_file` approve / execute / undo works.
- Changed destination content blocks undo.
- Action metadata shows `source_root`, `target_root`, and `allowed_roots`.
- AgentGuard review works on a local git repo.
- AgentGuard packet has claims and evidence.
- Sensitive untracked file content is omitted.
- CaseDetail displays artifacts, claims, evidence, actions, decisions, runs,
  and test return code.
- Proof Packet markdown export works.

## Dogfood checklist

- Clean clone or fast-forward local `main`.
- Run backend tests.
- Run frontend tests and build.
- Run `scripts/release_check.ps1`.
- Run `scripts/rc_api_smoke.py`.
- Run `scripts/demo_seed.py`.
- Start backend on `127.0.0.1:8787`.
- Start frontend on `127.0.0.1:5173`.
- Confirm Dashboard shows `ProofFlow v0.1.0-rc1`.
- Run LocalProof scan.
- Run LocalProof suggest-actions.
- Approve, execute, and undo `mkdir_dir` and `move_file`.
- Confirm undo refuses changed file content.
- Run AgentGuard against a local git repo.
- Confirm changed files, claims, evidence, and test metadata appear.
- Export Proof Packet Markdown.
- Confirm no sensitive untracked file content appears.
- Confirm action scope metadata is visible.
- File each bug as a separate issue.

## Bug triage rules

- P0: data loss, secret leak, action escapes allowed roots, app cannot start.
- P1: core dogfood path broken, Proof Packet export broken, CI red.
- P2: confusing UI, docs drift, missing smoke coverage.
- P3: polish.

## RC2 decision

Cut `v0.1.0-rc2` only if there are P0/P1 fixes or if post-RC1 smoke helper
commits should be included in a published RC snapshot.

Do not move `v0.1.0-rc1`.

## Results

This table is for post-RC1 `main` validation unless a row explicitly states it
was run on the immutable `v0.1.0-rc1` tag.

| Check | Command / flow | Result | Notes |
| --- | --- | --- | --- |
| Backend tests | `cd backend; python -m pytest` | TODO | TODO |
| Frontend tests | `cd frontend; npm run test` | TODO | TODO |
| Frontend build | `cd frontend; npm run build` | TODO | TODO |
| Release helper | `.\scripts\release_check.ps1` | TODO | TODO |
| API smoke | `python .\scripts\rc_api_smoke.py` | TODO | TODO |
| API smoke cleanup | `python .\scripts\rc_api_smoke.py --cleanup` | TODO | TODO |
| Demo seed | `python .\scripts\demo_seed.py` | TODO | TODO |
| Manual UI dogfood | Dashboard / LocalProof / AgentGuard / export | TODO | TODO |

## Recorded post-RC1 findings

- `scripts/demo_seed.py` did not honor isolated DB/data output paths from the
  CLI. This was fixed after the RC1 tag by honoring `PROOFFLOW_DB_PATH`,
  `PROOFFLOW_DATA_DIR`, `--db-path`, and `--data-dir`.
- `scripts/rc_api_smoke.py` was added after the RC1 tag to make the API dogfood
  path repeatable with temp DB/data paths.
- RC smoke temp artifacts are preserved on failure so the DB, packet, and local
  evidence remain available for debugging.

## Out of scope

- RAG.
- ComfyUI.
- Cloud sync.
- Multi-user workflow.
- Docker.
- Managed backup implementation.
- Delete actions.
- Plugin system.
- Automatic AI code edits.

## Known limitations

- No auth.
- No multi-user workflow.
- No cloud sync.
- No vector RAG.
- No ComfyUI execution.
- No automatic AI code edits.
- Localhost remains the v0.1 trust boundary.
