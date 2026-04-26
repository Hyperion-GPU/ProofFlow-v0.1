# MVP Scope

ProofFlow v0.1 is a local-first workflow dashboard for evidence-backed AI work.

## In scope

- Local FastAPI backend.
- Local SQLite storage.
- React + TypeScript + Vite frontend.
- Case, Artifact, Evidence, Action, Decision model.
- LocalProof file evidence manager.
- AgentGuard code review workflow.
- Proof packet export.
- Windows-friendly local development.

## Out of scope

- Cloud storage or hosted services.
- Docker or container orchestration.
- Remote sync.
- Multi-user accounts and permissions.
- Full plugin marketplace.
- Background agents that change files without human approval.
- Destructive file operations without dry-run, approval, and undo.

## MVP quality bar

- A user can understand what happened from recorded evidence.
- A human can approve or reject AI-supported actions.
- Local files are not deleted or rewritten silently.
- The app can be run and inspected on a Windows localhost setup.

