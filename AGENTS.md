# ProofFlow Agent Rules

These rules apply to coding agents working in this repository.

## Workflow

- Communicate and deliver in Simplified Chinese unless the user asks otherwise.
- Start with a quick audit of the current files and constraints before changing
  code or docs.
- Keep changes small, complete, and directly tied to the requested milestone.
- Prefer root-cause fixes over broad rewrites.
- Do not add cloud services, remote sync, telemetry, or Docker unless the user
  explicitly changes the v0.1 scope.

## Evidence

- AI or heuristic claims must cite evidence: file paths, command output, test
  results, screenshots, or user-provided source material.
- Code review findings must explain the impact and point to the relevant file or
  symbol.
- If evidence is missing, label the statement as an assumption.

## Safety

- Destructive file actions require three parts before execution:
  1. dry-run command or preview,
  2. explicit user approval,
  3. undo or recovery path.
- Do not delete user data, local databases, generated proof packets, or uploaded
  artifacts without approval.
- Use Windows-friendly commands and quote paths that may contain spaces.

## Architecture

- Backend code should stay modular: routers handle HTTP shape, services handle
  workflow logic, and database helpers own SQLite access.
- Frontend code should stay simple until the MVP workflows are proven.
- Keep localhost as the default trust boundary.
- Do not implement business features in scaffolding commits unless the milestone
  specifically calls for them.

## Delivery

Final reports should include:

1. what changed,
2. why it changed,
3. how to verify or reproduce,
4. what was intentionally not done,
5. the recommended next step.

