# Architecture

ProofFlow v0.1 is a localhost web app. The backend exposes FastAPI routes, the
frontend runs in Vite, and workflow state is planned for SQLite on the local
machine.

## Workflow model

- Case: the top-level work container. A case can represent a file audit, a code
  review, or another local proof workflow.
- Artifact: a local file, diff, note, command transcript, or other object being
  inspected.
- Evidence: a verifiable observation about an artifact. Evidence can include
  hashes, excerpts, command results, screenshots, or human notes.
- Action: a proposed or completed step, such as inspect, classify, review, fix,
  export, or ask for approval.
- Decision: the human or policy outcome that accepts, rejects, defers, or changes
  an action.

The intended chain is:

```text
Case -> Artifact -> Evidence -> Action -> Decision
```

An action should not rely on unsupported AI output. It should point to evidence
or be marked as an assumption.

## Backend shape

- `proofflow/main.py` creates the FastAPI application and initializes SQLite on startup.
- `proofflow/routers/` owns HTTP routes.
- `proofflow/services/` owns workflow behavior.
- `proofflow/db.py` owns SQLite connection helpers.
- `proofflow/migrations.py` owns first-run database initialization.

The current v0.1 backend exposes health, cases, artifacts, search, actions,
decisions, reports, LocalProof, and AgentGuard routes.

## Frontend shape

The frontend starts as a single Vite React TypeScript app. It should grow around
MVP workflows, not around a generic dashboard shell.

## Local boundary

ProofFlow v0.1 does not require cloud services, remote storage, Docker, or
background sync. Local files and local SQLite state are the default boundary.
