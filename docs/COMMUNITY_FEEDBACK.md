# Community Feedback

ProofFlow tracks external feedback that leads to concrete fixes, especially
when the report comes from real local use rather than planned internal work.

## 2026-05-10 - VS Code policy gate approval

- Source: GitHub issue #78, reported by an external user testing the VS Code
  extension.
- Component: VS Code extension and policy gate action flow.
- Problem: `ProofFlow: Approve Pending Action` listed `pending_decision`
  actions, but then called the normal action approve endpoint. The backend
  requires these actions to be resolved by an accepted policy gate owner
  decision before execution.
- Response: v0.1.4 reworks the command as `ProofFlow: Approve Gate & Execute`,
  adds decision payload validation, and covers the command flow with extension
  tests.
- Evidence: issue #78, the fixing PR, and release notes for v0.1.4.
