## ProofFlow v0.1.5 - VS Code Inline Audit Visualization

This release completes the VS Code inline audit visualization slice for #57.
It builds on the previous policy gate patch by making trustworthy ProofFlow
claims visible inside the editor when the packet contains an explicit source
location.

### Added

- Added structured `source_location` output to Case Packet evidence when an
  existing `source_ref` or artifact path includes a path plus line or line
  range.
- Added VS Code inline audit decorations for claims with reliable source
  locations.
- Added Explorer context menu entries for `Scan with ProofFlow` and
  `Review with AgentGuard`.
- Added a pending policy gate notification that opens the existing approve flow.

### Fixed

- Fixed VS Code decoration range conversion so inclusive packet `end_line`
  values map to VS Code's exclusive range end position.
- Preserved Windows-style `C:\repo` source path handling in non-Windows test
  environments.

### Boundaries

- No line numbers are inferred from free-form claim or evidence text.
- No DB migration, RAG, webhook, GitHub Actions, or MCP changes are included.

### Verification

- `python -m pytest backend/tests/test_case_packet_api.py backend/tests/test_agentguard_review.py`
- `npm test` in `vscode-proofflow`
- `npm run build` in `vscode-proofflow`
- `npx tsc --noEmit` in `vscode-proofflow`
- `git diff --check`
