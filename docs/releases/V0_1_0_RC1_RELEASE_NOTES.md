# ProofFlow v0.1.0-rc1 Release Notes Draft

Status: GitHub pre-release published

ProofFlow v0.1.0-rc1 is a localhost-first release candidate for evidence-backed
local workflows. It keeps the v0.1 boundary on FastAPI, SQLite, React, local
files, deterministic checks, and human-reviewed actions.

## Release Identity

- Release name: `ProofFlow v0.1.0-rc1`
- Version: `0.1.0-rc1`
- Stage: `rc`
- Runtime check: `GET /health`
- Local release check: `.\scripts\release_check.ps1`

Post-release dogfood notes are tracked separately in
[V0_1_0_RC1_BUG_BASH.md](V0_1_0_RC1_BUG_BASH.md).

## Highlights

- Core evidence graph for cases, artifacts, evidence, claims, actions,
  decisions, runs, reports, and proof packets.
- LocalProof folder scanning, file metadata capture, text chunk indexing,
  previewable cleanup actions, and hash-guarded undo.
- AgentGuard local git review with evidence-backed claims and optional test
  command capture.
- Action safety gate for scoped filesystem actions, protected ProofFlow data
  paths, legacy safety migration, and recoverable undo failures.
- Backend and frontend CI release gates plus a public-safe dogfood Proof Packet
  example.

## Publish Checklist

- Confirm backend CI passes on Python 3.11 and 3.12.
- Confirm frontend CI passes on Node 22.x.
- Run `.\scripts\release_check.ps1` locally from the repository root.
- Confirm Dashboard shows `ProofFlow v0.1.0-rc1`.
- Confirm `GET /health` returns `version`, `release_stage`, and `release_name`.
- Review the public dogfood packet example for sensitive content.

## Known Limitations

- No auth.
- No multi-user workflow.
- No cloud sync.
- No vector RAG.
- No ComfyUI execution.
- No automatic AI code edits.
- Localhost remains the v0.1 trust boundary.
