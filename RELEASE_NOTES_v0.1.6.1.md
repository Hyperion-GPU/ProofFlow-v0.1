## ProofFlow v0.1.6.1 - Dogfood Polish for CI Review Comments

This patch comes directly from dogfooding the v0.1.6 GitHub Actions review
workflow on ProofFlow itself.

The workflow worked: it ran on a real pull request, published a stable summary
comment, uploaded `summary.json`, and exported a downloadable Proof Packet.
The first real review also exposed a small usability issue: the PR comment
showed the runner-local Proof Packet path, which is technically accurate but
not helpful to a maintainer reading GitHub.

### Fixed

- The PR review comment now tells maintainers that the Proof Packet is included
  in the `proofflow-agentguard-review` workflow artifact instead of displaying
  a `/home/runner/...` path.
- The stable marker update behavior was verified: a second push edited the
  existing ProofFlow comment instead of adding a duplicate comment.

### Docs

- The README first-screen story now leads with CI Proof Packets for AI code
  review and links to the v0.1.6 release.

### Verification

- Opened a real dogfood PR: `#94`.
- First ProofFlow PR Review run succeeded and produced:
  - `status=completed`
  - `risk_level=info`
  - `changed_files=1`
  - `claims_created=1`
  - `evidence_created=1`
  - downloadable `summary.json`
  - downloadable Proof Packet markdown
- After the comment polish, the second ProofFlow PR Review run succeeded and
  updated the same comment:
  - `changed_files=2`
  - `claims_created=1`
  - `evidence_created=1`
  - Proof Packet row: `Included in workflow artifact proofflow-agentguard-review`
- All PR checks passed:
  - AgentGuard Proof Packet
  - Python 3.11
  - Python 3.12
  - Frontend test/build
  - Ruff
  - TypeScript
- Local checks:
  - `cd backend && python -m pytest tests/test_release_docs.py`
  - `git diff --check`

