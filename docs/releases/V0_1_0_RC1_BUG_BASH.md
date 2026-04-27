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
Each completed block returns to the repository root. Run long-lived backend and
frontend dev servers in separate PowerShell windows opened at the repository
root.

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
Push-Location .\backend
python -m pytest
Pop-Location

Push-Location .\backend
python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload
Pop-Location
```

Frontend:

```powershell
Push-Location .\frontend
npm ci
npm run test
npm run build
npm run dev
Pop-Location
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
| Backend tests | `Push-Location backend; python -m pytest; Pop-Location` | PASS | Run on `chore/rc1-dogfood-closure` at `96854fdbf2f5ef572fd989647423084f3787e7ef`, branched from synced post-RC1 `main`; no immutable tag check was run. Exit 0; 66 passed. Warnings: pytest could not write `backend\.pytest_cache` and emitted an atexit temp cleanup `PermissionError`, but pytest still exited 0. |
| Frontend tests | `Push-Location frontend; npm run test; Pop-Location` | PASS | Run after `Push-Location frontend; npm ci; Pop-Location` exited 0. `npm ci` reported 5 moderate audit findings and `whatwg-encoding@3.1.1` deprecation warning. Vitest exit 0; 4 test files and 5 tests passed. |
| Frontend build | `Push-Location frontend; npm run build; Pop-Location` | PASS | Exit 0; `tsc -b && vite build` completed, Vite transformed 51 modules and built `dist/`. |
| Release helper | `.\scripts\release_check.ps1` | PASS | Exit 0; PowerShell helper ran backend pytest, frontend `npm ci`, frontend tests, and frontend build, then printed `ProofFlow v0.1.0-rc1 release check passed.` Same pytest cache/temp cleanup warnings and npm audit/deprecation warnings were observed. |
| API smoke | `python .\scripts\rc_api_smoke.py` | PASS | Exit 0; health release identity passed, LocalProof created 4 actions, AgentGuard case and Proof Packet were created. Temp output was preserved at `%TEMP%\proofflow-rc-api-smoke-co6aozlq` with DB `proofflow-smoke.db` and data dir `data`. |
| API smoke cleanup | `python .\scripts\rc_api_smoke.py --cleanup` | PASS | Exit 0; cleanup run passed and reported temp root `%TEMP%\proofflow-rc-api-smoke-l9b6g_xj`. Follow-up `Test-Path` returned `False`, confirming the temp root was removed after success. |
| Demo seed | `python .\scripts\demo_seed.py` | PASS | Exit 0; generated demo DB `D:\ProofFlow v0.1\backend\data\demo\proofflow.db`, data dir `D:\ProofFlow v0.1\backend\data\demo`, manual case `fe948fc4-abab-4b85-87b2-61ba58d972c2`, LocalProof case `e5a24d7c-a60f-455e-92b0-f98e5dbe8084`, AgentGuard case `717529ef-4b3e-4992-a1db-c4c72e97394d`, and Proof Packet `D:\ProofFlow v0.1\backend\data\demo\proof_packets\fe948fc4-abab-4b85-87b2-61ba58d972c2.md`. |
| Manual UI dogfood | Dashboard / LocalProof / AgentGuard / export | PASS | Ran with backend on `127.0.0.1:8787`, frontend on `127.0.0.1:5173`, demo DB/data from `scripts/demo_seed.py`, and an isolated Playwright runner under `%TEMP%`. Verified Dashboard release identity, Cases list, LocalProof scan/suggest, previewable `mkdir_dir` and `move_file`, approve/execute/undo for both action types, changed destination content blocking undo, visible `source_root`/`target_root`/`allowed_roots`, AgentGuard review on a temp git repo, claims/evidence, sensitive untracked content omission, CaseDetail sections including run return code, and Proof Packet markdown export. Exported packet: `D:\ProofFlow v0.1\backend\data\demo\proof_packets\8329aad3-86c7-423f-847b-cc0f4a65ae57.md`. |

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
