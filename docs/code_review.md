# AgentGuard Code Review Workflow

AgentGuard is the ProofFlow branch for evidence-backed code review.

## Goal

Help a human review code with AI assistance while keeping every claim tied to
evidence.

## Minimum workflow

1. Create a review case.
2. Register artifacts such as files, diffs, command output, or test results.
3. Record findings as evidence-backed claims.
4. Propose actions such as fix, test, defer, or reject.
5. Record the human decision and final rationale.

## Review finding rule

A finding is valid only when it includes:

- claim,
- affected file or symbol,
- supporting evidence,
- impact,
- recommended action.

If the evidence is missing, the claim must be labeled as an assumption and should
not be treated as a final review result.

## Destructive actions

Any action that deletes, overwrites, moves, or rewrites user files must be
handled as:

```text
dry-run -> user approval -> execution -> undo path
```

This applies to cleanup scripts, formatters that rewrite many files, generated
patches, and database reset commands.

## GitHub Actions PR Review

ProofFlow can run a minimal AgentGuard review automatically for pull requests
with `.github/workflows/proofflow-pr-review.yml`.

To enable it, keep that workflow file in the repository and allow GitHub Actions
to run on pull requests. To disable it, delete the workflow file or disable the
workflow in the repository Actions settings.

The workflow:

- runs on `pull_request`,
- checks out the repository with full history,
- installs `backend/requirements.txt`,
- runs `scripts/ci_agentguard_review.py` against the PR base SHA,
- stores the Proof Packet markdown, raw `artifacts/git-diff.patch`,
  `artifacts/manifest.json`, and schema v2 `summary.json` as the
  `proofflow-agentguard-review` workflow artifact,
- publishes or updates one PR comment marked with
  `<!-- proofflow-agentguard-review -->`.

The PR comment reports status, risk level, changed file count, claim count,
evidence count, artifact name, workflow run, base/head SHA, test command policy,
diff artifact path, Proof Packet path, and any failure or skipped reason. This
is audit-only visibility; it does not block merges.

The artifact is intended to be usable offline:

- `summary.json` uses `schema_version: "2"` and includes PR/run/base/head
  provenance plus legacy fields for compatibility.
- `artifacts/git-diff.patch` is the raw review evidence for tracked changes.
- `artifacts/manifest.json` records relative paths, SHA-256 hashes, and sizes
  for exported artifacts.
- `data/proof_packets/*.md` includes CI provenance and points evidence back to
  artifact-relative paths such as `artifacts/git-diff.patch`.

The workflow needs `contents: read` to inspect the repository,
`pull-requests: write` to read PR metadata, and `issues: write` because GitHub
stores PR comments as issue comments.

The CI script sets isolated `PROOFFLOW_DB_PATH` and `PROOFFLOW_DATA_DIR` values
under the workflow output directory, so it does not write to local development
data. It also intentionally does not pass `test_command` to AgentGuard. If a
future workflow needs test command execution, enable it explicitly and review
that command execution boundary separately.

After dependency refreshes, keep one small documentation-only dogfood PR in the
loop. It verifies that the current backend, frontend, and GitHub Actions toolchain
still produce a low-risk Proof Packet with reproducible CI provenance.

