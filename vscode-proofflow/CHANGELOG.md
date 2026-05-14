# Changelog

## 0.1.5 - 2026-05-14

### Added

- Added inline audit decorations for ProofFlow claims with reliable source
  locations.
- Added Explorer context menu entries for `Scan with ProofFlow` and
  `Review with AgentGuard`.
- Added a pending policy gate notification that opens the existing approve flow.

### Fixed

- Fixed multiline inline decoration ranges so packet inclusive end lines remain
  highlighted in VS Code's exclusive range model.

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
