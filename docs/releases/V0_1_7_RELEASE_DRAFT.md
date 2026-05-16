# ProofFlow v0.1.7 Release Draft

Status: draft

ProofFlow v0.1.7 continues the CI Proof Packet line: AI code review should be
evidence-backed, reproducible, and inspectable offline. This release draft is
based on the post-dependency dogfood pass after refreshing the frontend,
backend, VS Code, and GitHub Actions toolchain.

## Highlights

- CI AgentGuard reviews now produce a schema v2 `summary.json` with run
  provenance, base/head SHA, artifact-relative paths, and explicit
  `not_run_by_ci_design` test command policy.
- Workflow artifacts include the raw tracked diff, a SHA-256 manifest, and the
  Proof Packet markdown, so reviewers can verify the audit bundle offline.
- Deterministic review claims distinguish docs-only changes, workflow changes,
  CI permission changes, script/command surface changes, and missing test
  coverage risk.
- The dependency refresh kept the current toolchain healthy: TypeScript 6,
  Vite 8, Vitest 4, React Router 7, Uvicorn 0.47, and
  `actions/upload-artifact@v7`.

## Dogfood Evidence

Post-dependency dogfood PR:
[#97 Document post-dependency dogfood check](https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/97)

ProofFlow reviewed the documentation-only dogfood PR with the upgraded
toolchain and produced a low-risk, reproducible CI audit bundle:

- PR comment:
  [ProofFlow AgentGuard review for #97](https://github.com/Hyperion-GPU/ProofFlow-v0.1/pull/97#issuecomment-4466133252)
- Workflow run:
  [ProofFlow PR Review #25955860785](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/25955860785)
- Workflow artifact:
  [`proofflow-agentguard-review` artifact #7031485870](https://github.com/Hyperion-GPU/ProofFlow-v0.1/actions/runs/25955860785/artifacts/7031485870)
- Proof Packet inside artifact:
  `data/proof_packets/407e959f-c900-428b-a493-eddaf579f8e0.md`
- Summary:
  `schema_version=2`, `risk_level=info`, `changed_files=1`,
  `claims_created=2`, `evidence_created=2`,
  `test_command_policy=not_run_by_ci_design`
- Offline verification:
  downloaded artifact manifest SHA-256 values matched both
  `artifacts/git-diff.patch` and the exported Proof Packet.

## Validation

- `cd backend && python -m pytest` -> 296 passed, 3 skipped.
- `cd frontend && npm ci && npm run test && npm run build` -> Vitest 25 passed,
  Vite build succeeded.
- `cd backend && python -m pytest tests/test_release_docs.py` -> 4 passed.
- `git diff --check` -> clean.
- PR #97 CI -> Backend, Frontend, Lint, TypeScript, and AgentGuard Proof Packet
  all passed.

## Intentionally Not Included

- No merge blocking.
- No hosted service or cloud review backend.
- No external LLM second-pass review.
- No Docker action migration.
- No CI `test_command` execution.
