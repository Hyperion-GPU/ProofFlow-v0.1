# ProofFlow MVP Plan

## Milestone 0: Repository skeleton

- [x] Create root docs and local run instructions.
- [x] Add FastAPI backend skeleton with health check.
- [x] Add Vite React TypeScript frontend skeleton.
- [x] Document the local-first workflow model.
- [x] Add automated tests after the first real service contract exists.

## Milestone 1: LocalProof

- [x] Define SQLite schema for cases, artifacts, evidence, actions, decisions.
- [x] Add local file registration without copying or deleting originals by
  default.
- [x] Store hashes, file metadata, and evidence notes.
- [x] Show case timeline and artifact list in the frontend.
- [x] Export a minimal proof packet.

## Milestone 2: AgentGuard

- [x] Add code review case type.
- [x] Record review claims as evidence-backed findings.
- [x] Track proposed actions and human decisions.
- [x] Link findings to files, commands, test output, or diffs.
- [x] Reject unsupported AI or heuristic claims in review summaries.

## Milestone 3: Proof packet

- [x] Generate a local packet containing inputs, evidence, actions, decisions,
  reproduction steps, and known limits.
- [x] Keep exports deterministic enough to compare across runs.
- [x] Add a verification checklist for packet completeness.

## Milestone: Harden v0.1

- [x] Harden AgentGuard untracked file ingestion with sensitive-file omission and
  a 256 KiB synthetic diff cap.
- [x] Preserve evidence-backed metadata and claims for omitted or capped
  untracked files without storing sensitive content.
- [x] Add previewable `mkdir_dir` actions so LocalProof suggested moves are
  executable when category directories are missing.
- [x] Keep `move_file` strict: it still requires an existing destination parent
  and does not create directories implicitly.
- [x] Make `scripts/demo_seed.py` compatible with Python 3.11 readonly reset
  handling.
- [x] Align CaseDetail run metadata display with backend `test_returncode`.
- [x] Refresh README and agent invariants for the current v0.1 trust baseline.

## Milestone: Dogfood v0.1

- [x] Align `make dev-backend` with the documented backend port `8787`.
- [x] Add full LocalProof action lifecycle controls in the page: approve,
  execute, undo, and reject.
- [x] Show LocalProof action preview, result, undo, metadata, and dependency
  context for dogfood review.
- [x] Add focused frontend smoke checks for Dashboard, AgentGuard, LocalProof,
  and CaseDetail.
- [x] Add a backend v0.1 action lifecycle and packet invariant acceptance test.
- [x] Add a local dogfood guide for demo seed, backend/frontend startup, smoke
  checks, LocalProof, AgentGuard, and Proof Packet export.

## Milestone: v0.1 RC Action Safety Gate

- [x] Add scoped filesystem action validation.
- [x] Add LocalProof `source_root` / `target_root` / `allowed_roots` metadata.
- [x] Add hash-guarded undo for `move_file` and `rename_file`.
- [x] Block ProofFlow DB/data/proof_packets paths from filesystem actions.
- [x] Add legacy action safety upgrade coverage.
- [x] Document action safety, reset, backup, and restore behavior.

## Milestone: v0.1 RC Release Gate

- [x] Add backend CI matrix.
- [x] Add frontend CI for tests and build.
- [x] Add RC checklist.
- [x] Add changelog.
- [x] Add dogfood Proof Packet example.

## Milestone: v0.1.0-rc1 Version Stamp & Publish Prep

- [x] Centralize backend release metadata.
- [x] Expose version, stage, and release name from `/health`.
- [x] Show the RC release stamp on the Dashboard.
- [x] Add release notes draft.
- [x] Add local release check helper.

## Milestone: v0.1.0-rc1 Dogfood Bug Bash

- [x] Log the post-release RC1 dogfood bug bash path.
- [x] Archive post-RC1 smoke helper changes in the Unreleased changelog.
- [x] Keep the `v0.1.0-rc1` tag fixed while documenting post-RC1 `main`
  changes separately.
- [x] Link the RC API smoke helper from dogfood and release checklist docs.

## Milestone: Managed Backup / Restore Foundation

- [x] Define the managed backup / restore design, invariants, manifest shape,
  API contract, and contract tests.
- [ ] Implement backend backup preview, create, list, detail, and verify.
- [ ] Implement restore preview and restore to a new location.
- [ ] Add a thin UI only after backend contracts are proven.
- [ ] Defer live DB restore until stricter pre-restore backup and confirmation
  gates exist.

## Future scope

- [ ] Add richer destructive action types only after a new preview/undo review.
- [ ] Explore vector RAG after v0.1 local trust boundaries are accepted.
- [ ] Explore ComfyUI execution after v0.1 local trust boundaries are accepted.
- [ ] Explore multi-user workflows after localhost v0.1 is stable.
- [ ] Explore cloud sync after local-first recovery paths are stable.
- [ ] Explore AI-assisted code edits only after evidence and action review gates
  are stricter than the current v0.1 baseline.
