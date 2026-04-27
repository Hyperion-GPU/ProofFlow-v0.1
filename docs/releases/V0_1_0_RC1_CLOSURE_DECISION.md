# ProofFlow v0.1.0-rc1 Closure Decision

Date: 2026-04-27
Branch: chore/rc1-dogfood-closure
Validated ref: 96854fdbf2f5ef572fd989647423084f3787e7ef
Scope: post-RC1 dogfood bug bash closure

## Decision

No P0/P1 blocker found in automated checks that were run. Keep v0.1.0-rc1
immutable. Do not cut v0.1.0-rc2 for this closure alone. Proceed next to
Managed Backup / Restore Foundation.

The validation ran on `chore/rc1-dogfood-closure`, branched from synced
post-RC1 `main` at `96854fdbf2f5ef572fd989647423084f3787e7ef`. No check in
this closure was run on, or changed, the immutable `v0.1.0-rc1` tag.

## Evidence

| Gate | Result | Evidence / notes |
| --- | --- | --- |
| Backend tests | PASS | `Push-Location backend; python -m pytest; Pop-Location` exited 0 with 66 passed. Warnings: pytest could not write `backend\.pytest_cache` and emitted an atexit temp cleanup `PermissionError`; test result still exited 0. |
| Frontend tests | PASS | `Push-Location frontend; npm ci; Pop-Location` exited 0, then `Push-Location frontend; npm run test; Pop-Location` exited 0 with 4 test files and 5 tests passed. `npm ci` reported 5 moderate audit findings and a `whatwg-encoding@3.1.1` deprecation warning. |
| Frontend build | PASS | `Push-Location frontend; npm run build; Pop-Location` exited 0; `tsc -b && vite build` completed and Vite transformed 51 modules. |
| Release helper | PASS | `.\scripts\release_check.ps1` exited 0 and printed `ProofFlow v0.1.0-rc1 release check passed.` It reran backend pytest, frontend install, frontend tests, and frontend build. |
| API smoke | PASS | `python .\scripts\rc_api_smoke.py` exited 0. Temp output was preserved at `%TEMP%\proofflow-rc-api-smoke-co6aozlq`; DB `proofflow-smoke.db`, data dir `data`, LocalProof case `5b09259d-8f76-4ad0-bb8f-08ef3c3446e5`, AgentGuard case `e3050c4f-098a-47d5-927b-afff3a025f65`, and Proof Packet under the temp data dir were created. |
| API smoke cleanup | PASS | `python .\scripts\rc_api_smoke.py --cleanup` exited 0. It used temp root `%TEMP%\proofflow-rc-api-smoke-l9b6g_xj`; follow-up `Test-Path` returned `False`, confirming cleanup after success. |
| Demo seed | PASS | `python .\scripts\demo_seed.py` exited 0. It generated DB `D:\ProofFlow v0.1\backend\data\demo\proofflow.db`, data dir `D:\ProofFlow v0.1\backend\data\demo`, manual case `fe948fc4-abab-4b85-87b2-61ba58d972c2`, LocalProof case `e5a24d7c-a60f-455e-92b0-f98e5dbe8084`, AgentGuard case `717529ef-4b3e-4992-a1db-c4c72e97394d`, and Proof Packet `D:\ProofFlow v0.1\backend\data\demo\proof_packets\fe948fc4-abab-4b85-87b2-61ba58d972c2.md`. |
| Manual UI dogfood | PASS | Backend ran on `127.0.0.1:8787`, frontend ran on `127.0.0.1:5173`, and an isolated Playwright runner under `%TEMP%` executed the browser flow. It verified Dashboard release identity, Cases list, LocalProof scan/suggest, previewable `mkdir_dir` and `move_file`, approve/execute/undo for both action types, changed destination content blocking undo, visible `source_root`/`target_root`/`allowed_roots`, AgentGuard review on a temp git repo, claims/evidence, sensitive untracked content omission, CaseDetail sections including run return code, and Proof Packet markdown export. Exported packet: `D:\ProofFlow v0.1\backend\data\demo\proof_packets\8329aad3-86c7-423f-847b-cc0f4a65ae57.md`. |

## Release body cleanup

GitHub Release body was updated.

- The release title/body no longer uses draft wording.
- `ProofFlow v0.1.0-rc1 Release Notes Draft` was replaced with
  `ProofFlow v0.1.0-rc1`.
- `Status: release candidate draft` was replaced with
  `Status: release candidate / pre-release`.
- `Publish Checklist` was replaced with `Validated Release Gates`.
- `v0.1.0-rc1` tag was not moved.

Verification command:

```powershell
gh release view v0.1.0-rc1 --repo Hyperion-GPU/ProofFlow-v0.1 --json name,tagName,isPrerelease,body
```

Verified values:

- `name`: `ProofFlow v0.1.0-rc1`
- `tagName`: `v0.1.0-rc1`
- `isPrerelease`: `true`
- body contains `Validated Release Gates`
- body no longer contains `Release Notes Draft`
- body no longer contains `release candidate draft`

## RC2 recommendation

Do not cut v0.1.0-rc2 yet.

Cut v0.1.0-rc2 only if the project owner decides post-RC1 smoke helper commits
should become a published RC snapshot, or if later P0/P1 fixes need a new RC.

## Remaining risks

- No auth.
- No multi-user workflow.
- No cloud sync.
- No vector RAG.
- No ComfyUI execution.
- No automatic AI code edits.
- Localhost remains the v0.1 trust boundary.
- Pytest could not write `backend\.pytest_cache` in this Windows environment and
  emitted a temp cleanup `PermissionError` after passing tests.
- `npm ci` reported 5 moderate audit findings and a `whatwg-encoding@3.1.1`
  deprecation warning; frontend tests and build still exited 0.

## Next sprint

Managed Backup / Restore Foundation is the recommended next feature sprint
after RC1 closure, but it was intentionally not implemented in this task.
