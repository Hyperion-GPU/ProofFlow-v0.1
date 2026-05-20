# Changelog

## 0.2.0-dev — Unreleased (2026-05-19)

### Added

- **Active Ledger sidebar view** — second tree view that lists every open
  Agent Work Ledger Case with sections for Contract, Algorithm Decisions,
  Cost Budgets, Snapshots, Evidence, Claims, and Evaluations.
- **Ledger commands** — eight new commands cover the full workflow:
  `Start Work Contract`, `Record Event`, `Record Algorithm Decision`,
  `Record Cost Budget`, `Capture Snapshot`, `Record Evidence`, `Record Claim`,
  `Evaluate Contract`, `Finish`.
- **Case Detail webview** — opens from any case in the tree. Four tabs:
  Overview (contract / budgets / decisions), Evidence & Claims (with hover
  highlighting linked items), Actions, and Risk Hints (with one-click
  `Explain` to bind disposition + rationale + evidence).
- **Approve Gate webview** — replaces the QuickPick approval flow with a
  diff/preview pane on the left and risk claims on the right. Approve &
  Execute, Reject, or open the inline source for any flagged claim.
- **Export Proof Packet** — the Case Detail header now exports the markdown
  packet to `${workspace}/.proofflow/exports/<case>-<timestamp>.md` and
  opens the markdown preview.

### Changed

- `ProofFlowClient` is now a thin facade over a typed REST client that covers
  the whole backend surface (cases, ledger, decisions, exports, search).
  The public surface (`listCases`, `getCasePacket`, `approveAction`, …) is
  unchanged so existing commands and tests continue to compose.
- `ProofFlow: Approve Gate & Execute` opens the rich webview when invoked
  from the extension; the legacy QuickPick path stays for tests and headless
  callers without the webview context.
- Status bar now exposes the backend connection lifecycle
  (`starting`, `ready`, `restarting`, `failed`) plus the existing pending
  action count.

### Notes

- An earlier draft of this milestone routed traffic through the ProofFlow
  MCP server over stdio so humans and agents would share a single tool
  protocol. The MCP server formats responses as agent-readable text rather
  than structured JSON, which made it unsuitable for a UI client. v0.2
  reverts to direct REST against the backend; the MCP server remains the
  surface AI clients use.

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
