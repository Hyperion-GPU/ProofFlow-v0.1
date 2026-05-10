# Changelog

## 0.1.4 - 2026-05-10

### Fixed

- Fixed #78: `ProofFlow: Approve Gate & Execute` now resolves
  `pending_decision` actions through the backend policy gate owner-decision
  flow before executing the action.

## 0.1.0 - 2026-05-08

Initial release.

- One-click `Review Last AI Changes` command (calls `/agentguard/review`).
- `Scan Current Folder` command (calls `/localproof/scan`).
- `Approve Gate & Execute` command for gated actions.
- Sidebar tree view: Cases -> Actions / Claims, with severity-coded icons.
- Status bar with online/offline indicator and pending-action counter.
- Auto-polling every 10 seconds (configurable).
- `ProofFlow: Show Logs` command + dedicated output channel for diagnostics.
- Configuration: `proofflow.backendUrl`, `proofflow.apiKey`, `proofflow.autoRefresh`.
