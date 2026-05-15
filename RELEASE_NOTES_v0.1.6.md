## ProofFlow v0.1.6 - CI Proof Packets for AI Code Review

This release turns ProofFlow from a local audit dashboard into something that
can meet an AI-generated pull request at the exact moment it matters: in CI,
before review context evaporates.

The headline is the new GitHub Actions PR review workflow. When a pull request
opens or updates, ProofFlow can run AgentGuard against the diff, create a Case,
export a Proof Packet, upload the packet and a machine-readable summary as
workflow artifacts, and leave a concise PR comment with the review status,
risk level, changed-file count, claims, evidence, and any failure reason.

It is deliberately small and local-first. There is no hosted service, no cloud
model, no webhook platform, no merge blocking, and no hidden RAG layer. The
workflow exists to prove the core ProofFlow idea in public: an AI code review is
more trustworthy when every claim has evidence and the resulting audit trail can
be downloaded as a Proof Packet.

### Why this matters

AI coding agents are fast enough that review context becomes the bottleneck.
This release gives maintainers a compact answer to three questions:

- What changed?
- What did the review claim about it?
- Where is the evidence?

The PR comment is the surface area; the Proof Packet is the durable record.

### Added

- GitHub Actions workflow for pull-request AgentGuard reviews:
  `.github/workflows/proofflow-pr-review.yml`.
- CI review runner:
  `scripts/ci_agentguard_review.py`.
- Isolated CI storage using output-local `PROOFFLOW_DB_PATH` and
  `PROOFFLOW_DATA_DIR`, so CI review data does not pollute repository state.
- Workflow artifacts for both the exported Proof Packet markdown and the
  minimal `summary.json`.
- Stable PR comment marker (`<!-- proofflow-agentguard-review -->`) so updates
  edit the existing comment instead of spamming the thread.
- Documentation for enabling, disabling, permissions, artifacts, and the
  explicit choice not to pass `test_command` in CI.

### Improved

- LocalProof and Case Detail now explain action state in plain language and show
  the next available action.
- Raw Preview / Result / Undo / Metadata JSON is folded behind compact summaries
  instead of dominating the page.
- Long filesystem paths now default to readable compact forms with the full path
  available on expansion.
- Backup / Restore path-heavy views use the same compact path treatment.
- Fresh `npm ci` now works in both `frontend` and `vscode-proofflow` from a
  clean clone.
- Repository-local generated backend data and dogfood temp output are ignored by
  default.
- Docker and AgentGuard local test-command defaults remain explicit and
  opt-in, preserving the local trust boundary.

### Boundaries

- No merge blocking.
- No Docker action.
- No hosted ProofFlow service.
- No cloud model integration.
- No webhook platform.
- No RAG or multi-agent schema rewrite.
- No implicit CI `test_command` execution.

### Verification

- Clean-clone install path:
  - backend `.venv` dependency install passed
  - `npm ci` passed in `frontend`
  - `npm ci` passed in `vscode-proofflow`
- LocalProof beginner path:
  - scanned 1 file
  - created 1 artifact
  - created 1 text chunk
  - generated 2 suggested actions
- AgentGuard CI path:
  - reviewed 2 changed files
  - created 1 claim
  - created 1 evidence record
  - exported a Proof Packet
  - wrote `summary.json` with `status=completed`
- Backup / Restore smoke:
  - previewed backup
  - created backup
  - verified backup
  - previewed restore
  - restored to a new location
- Test/build checks:
  - `cd backend && python -m pytest` -> 292 passed, 3 skipped
  - `cd frontend && npm run test` -> 25 passed
  - `cd frontend && npm run build` -> passed
  - `cd mcp-server && python -m pytest` -> 24 passed
  - `cd vscode-proofflow && npm test` -> 19 passed
  - `cd frontend && npm run test -- LocalProof ManagedBackupRestore` in a clean
    clone -> 14 passed
