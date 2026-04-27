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

## Future scope

- [ ] Document reset and backup workflows beyond the demo seed.
- [ ] Review destructive-action safeguards before expanding file operations.
- [ ] Explore multi-user, cloud sync, vector RAG, ComfyUI, or AI-assisted code
  edits only after v0.1 local trust boundaries are accepted.
