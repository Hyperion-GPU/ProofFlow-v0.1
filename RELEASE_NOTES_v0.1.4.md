## ProofFlow v0.1.4 - VS Code Policy Gate Patch

This patch release fixes an externally reported VS Code extension issue in the
policy gate approval flow.

### Fixed

- Fixed #78: `ProofFlow: Approve Gate & Execute` now creates the accepted
  policy gate owner decision expected by the backend before executing
  `pending_decision` actions.

### Verification

- `npm run build` in `vscode-proofflow`
- `npm test` in `vscode-proofflow`
- `npx @vscode/vsce ls` in `vscode-proofflow`
- `pytest backend/tests/test_policy_gate_enforcement.py`
