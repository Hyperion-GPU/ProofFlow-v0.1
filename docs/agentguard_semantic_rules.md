# AgentGuard Semantic Rules

AgentGuard started as a provenance-first review workflow: it captured the git
diff, changed file list, optional test output, and a Proof Packet that could be
shared with maintainers. That remains the baseline. Semantic rules add a small
deterministic layer on top: when AgentGuard can inspect a changed file with a
structured parser or a narrow text rule, it records evidence-backed Claims about
the maintenance contract being reviewed.

These rules are intentionally deterministic. They do not use an LLM, and they
do not claim to be a complete semantic code review.

## Provenance Claims

Every AgentGuard review records:

- the repository path,
- the base ref supplied to the review,
- whether untracked files were included,
- the changed file count,
- the risk level,
- the captured git diff artifact.

Proof Packet exports render this as an `AgentGuard Provenance` section so a
maintainer can see which diff was actually reviewed. This matters for clean PR
checkouts, where reviewing against the wrong base can produce an empty packet.

## Semantic Claims v1

The current deterministic semantic rules cover Codex plugin maintenance:

| Rule | Severity | Evidence |
|------|----------|----------|
| Codex plugin manifest parses as JSON and declares required metadata, skills, MCP server path, and default prompts | info or medium | `plugin.json` |
| ProofFlow plugin MCP config points to `proofflow-mcp` and `http://127.0.0.1:8787` | info or medium | `.mcp.json` |
| Repo-local Codex marketplace exposes `proofflow-maintainer` with the expected local path and install policy | info or medium | `.agents/plugins/marketplace.json` |
| Codex skill includes ProofFlow health, review, export, PR base, `GITHUB_BASE_REF`, `merge-base`, and `base_ref` guardrails | info or medium | `SKILL.md` |
| Markdown changed-file count statements match the actual reviewed diff | medium when inconsistent | changed file list and markdown text |

The rules are narrow on purpose. A passing info Claim means the rule checked a
specific contract, not that the whole PR is semantically correct.

## Example Finding

During dogfood on the ProofFlow Maintainer plugin, AgentGuard caught a real
documentation inconsistency:

```text
Claim: Markdown changed-file count statement appears inconsistent
Statement: five plugin files changed
Stated count: 5
Actual plugin changed file count: 4
```

That finding was useful because it was tied to the reviewed diff and showed the
exact statement that had drifted.

See
[`docs/examples/proof_packet_codex_plugin_review.md`](examples/proof_packet_codex_plugin_review.md)
for a sample Proof Packet that includes the semantic Claims.

## Current Boundaries

AgentGuard semantic rules do not:

- replace maintainer judgment,
- guarantee a complete code review,
- infer intent beyond the checked contract,
- run tests unless explicitly configured,
- close issues, merge PRs, or bypass policy gates.

When no semantic rule applies, the review is still useful as provenance, but the
response should say that the packet is provenance-only.

## Next Rule Candidates

Useful next rules should stay deterministic and evidence-backed:

- validate plugin path references against actual files,
- record base branch and resolved merge-base separately when the caller provides
  both,
- add first-class issue triage Claims once an `issue_triage` backend/MCP tool
  exists,
- add structured checks for GitHub Actions workflow permissions and artifact
  paths,
- add schema-aware checks for Proof Packet summary JSON.
