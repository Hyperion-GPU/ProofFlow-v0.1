# Changelog

All notable changes for ProofFlow v0.1 are tracked here.

## Unreleased

- Keep v0.1 scoped to localhost, SQLite, deterministic checks, and human-reviewed
  actions.

## v0.1.0-rc1

### Core Evidence Graph

- Added local Case, Artifact, Evidence, Action, Decision, Run, and Proof Packet
  workflows on SQLite.
- Added evidence-backed packet export for local Markdown review.

### LocalProof

- Added local folder scanning, file metadata capture, SHA-256 hashes, text chunk
  indexing, and FTS search.
- Added previewable suggested cleanup actions for common local file types.
- Added full LocalProof action lifecycle controls for approve, execute, undo,
  and reject.

### AgentGuard

- Added local git diff review with evidence-backed claims.
- Added changed-file tracking, optional test command capture, and untracked file
  omission for sensitive or oversized content.

### Action Safety

- Added scoped filesystem action validation for `move_file`, `rename_file`, and
  `mkdir_dir`.
- Added LocalProof `source_root`, `target_root`, and `allowed_roots` action
  metadata.
- Added SHA-256 guarded undo for `move_file` and `rename_file`.
- Blocked filesystem actions from ProofFlow DB, data, and proof packet paths.
- Added legacy action safety upgrade handling, including relative path migration
  and failed hash guard migration markers.

### Dogfood / Smoke Checks

- Added v0.1 dogfood guide from demo seed through LocalProof, AgentGuard, and
  Proof Packet export.
- Added backend acceptance tests for action lifecycle and packet invariants.
- Added frontend smoke tests for Dashboard, AgentGuard, LocalProof, and
  CaseDetail.
- Added backend and frontend CI release gates.

### Docs

- Added action safety documentation.
- Added reset, backup, and restore documentation.
- Added RC checklist and public dogfood Proof Packet example.

### Known limitations

- No auth.
- No multi-user workflow.
- No cloud sync.
- No vector RAG.
- No ComfyUI execution.
- No automatic AI code edits.
- Localhost remains the v0.1 trust boundary.
