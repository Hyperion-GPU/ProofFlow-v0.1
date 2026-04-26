# ProofFlow MVP Plan

## Milestone 0: Repository skeleton

- [x] Create root docs and local run instructions.
- [x] Add FastAPI backend skeleton with health check.
- [x] Add Vite React TypeScript frontend skeleton.
- [x] Document the local-first workflow model.
- [ ] Add automated tests after the first real service contract exists.

## Milestone 1: LocalProof

- [ ] Define SQLite schema for cases, artifacts, evidence, actions, decisions.
- [ ] Add local file registration without copying or deleting originals by
  default.
- [ ] Store hashes, file metadata, and evidence notes.
- [ ] Show case timeline and artifact list in the frontend.
- [ ] Export a minimal proof packet.

## Milestone 2: AgentGuard

- [ ] Add code review case type.
- [ ] Record review claims as evidence-backed findings.
- [ ] Track proposed actions and human decisions.
- [ ] Link findings to files, commands, test output, or diffs.
- [ ] Reject unsupported AI or heuristic claims in review summaries.

## Milestone 3: Proof packet

- [ ] Generate a local packet containing inputs, evidence, actions, decisions,
  reproduction steps, and known limits.
- [ ] Keep exports deterministic enough to compare across runs.
- [ ] Add a verification checklist for packet completeness.

## Milestone 4: Closeout

- [ ] Add focused backend tests for services and routers.
- [ ] Add frontend smoke checks for key MVP screens.
- [ ] Document reset and backup workflows.
- [ ] Review destructive-action safeguards before any file operation feature.

