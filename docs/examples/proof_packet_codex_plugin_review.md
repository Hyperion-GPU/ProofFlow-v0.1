# Proof Packet Example: Codex Plugin Semantic Review

> This sample was generated from a temporary fixture repository with
> `proofflow_review` and `proofflow_export_packet`.
> Local temporary paths are intentionally shortened to `<fixture>` for
> readability; the Claims and Evidence are otherwise representative of real
> ProofFlow output.

---

# Proof Packet: Code review: plugin-review-repo

Generated: `2026-05-17T11:48:43.140732Z`

## Case Summary

- Case ID: `6c661326-eb4e-42bf-927b-26d2132a4f32`
- Title: Code review: plugin-review-repo
- Workflow type: `code_review`
- Status: `open`
- Created: `2026-05-17T11:48:29.826102Z`
- Updated: `2026-05-17T11:48:29.826102Z`
- Summary: AgentGuard review for `<fixture>/plugin-review-repo`

## AgentGuard Provenance

- Repository path: `<fixture>/plugin-review-repo`
- Base ref: `826ecaecb70e546526ab68152e173109ffd38a30`
- Include untracked: `True`
- Changed file count: `5`
- Risk level: `medium`

## Artifacts

- `9c2a6ced-a06c-42ba-8a62-9343b0790c81` git-diff.patch
  - Kind: `git_diff`; Role: `primary`
  - Path: `agentguard://6c661326-eb4e-42bf-927b-26d2132a4f32/git-diff.patch`
  - SHA-256: `5c885a39700e101df7ce577ea413420e35555cf6f60dd228a1483449b9c539e7`

## Claims & Evidence

### Claim: Codex plugin manifest declares required metadata and prompts: plugins/proofflow-maintainer/.codex-plugin/plugin.json

- Claim ID: `23971026-a599-4bfe-adb9-d314e3182a20`
- Type: `agentguard_risk`
- Status: `open`
- Severity: `info`

- Evidence `967c3026-a387-408b-8acd-93d31b01f79f` (git_diff)
  - Artifact: `9c2a6ced-a06c-42ba-8a62-9343b0790c81` git-diff.patch
  - Path: `agentguard://6c661326-eb4e-42bf-927b-26d2132a4f32/git-diff.patch`
  - Artifact relative path: `not recorded`
  - Source ref: `plugins/proofflow-maintainer/.codex-plugin/plugin.json`

> Manifest: plugins/proofflow-maintainer/.codex-plugin/plugin.json
> name=proofflow-maintainer
> version=0.1.0
> skills=./skills/
> mcpServers=./.mcp.json
> defaultPrompt:
> - Review the current diff with ProofFlow.
> - Create a Proof Packet for this PR.
> - Triage this issue into a ProofFlow Case.

### Claim: ProofFlow MCP config keeps the localhost trust boundary: plugins/proofflow-maintainer/.mcp.json

- Claim ID: `059c4819-7712-4967-bec1-28b3a9926d1d`
- Type: `agentguard_risk`
- Status: `open`
- Severity: `info`

- Evidence `305550df-785c-4b11-9c17-bbc7a555bd60` (git_diff)
  - Artifact: `9c2a6ced-a06c-42ba-8a62-9343b0790c81` git-diff.patch
  - Path: `agentguard://6c661326-eb4e-42bf-927b-26d2132a4f32/git-diff.patch`
  - Artifact relative path: `not recorded`
  - Source ref: `plugins/proofflow-maintainer/.mcp.json`

> command=proofflow-mcp
> PROOFFLOW_BASE_URL=http://127.0.0.1:8787
> The plugin points Codex at the local ProofFlow MCP server.

### Claim: Markdown changed-file count statement appears inconsistent: plugins/proofflow-maintainer/README.md

- Claim ID: `094296eb-71c3-44a6-9ed6-947f889a9dcb`
- Type: `agentguard_risk`
- Status: `open`
- Severity: `medium`

- Evidence `66bf7731-5b22-43d5-95dd-bc9a6924a173` (git_diff)
  - Artifact: `9c2a6ced-a06c-42ba-8a62-9343b0790c81` git-diff.patch
  - Path: `agentguard://6c661326-eb4e-42bf-927b-26d2132a4f32/git-diff.patch`
  - Artifact relative path: `not recorded`
  - Source ref: `plugins/proofflow-maintainer/README.md`

> Statement: five plugin files changed
> Stated count: 5
> Actual plugin changed file count: 4
> Changed files:
> - .agents/plugins/marketplace.json
> - plugins/proofflow-maintainer/.codex-plugin/plugin.json
> - plugins/proofflow-maintainer/.mcp.json
> - plugins/proofflow-maintainer/README.md
> - plugins/proofflow-maintainer/skills/proofflow-maintainer/SKILL.md

### Claim: Codex skill documents PR-base review and Proof Packet export guardrails: plugins/proofflow-maintainer/skills/proofflow-maintainer/SKILL.md

- Claim ID: `3db53d08-e517-4c4b-ac5f-1819865183fa`
- Type: `agentguard_risk`
- Status: `open`
- Severity: `info`

- Evidence `ad800422-cc98-4d23-a612-dadbc50ced47` (git_diff)
  - Artifact: `9c2a6ced-a06c-42ba-8a62-9343b0790c81` git-diff.patch
  - Path: `agentguard://6c661326-eb4e-42bf-927b-26d2132a4f32/git-diff.patch`
  - Artifact relative path: `not recorded`
  - Source ref: `plugins/proofflow-maintainer/skills/proofflow-maintainer/SKILL.md`

> Skill includes ProofFlow health, review, issue triage, export, PR base, GITHUB_BASE_REF, and merge-base guidance.

### Claim: Changed file count: 5.

- Claim ID: `5304c490-ce82-45af-96c5-88e9eaa16726`
- Type: `agentguard_risk`
- Status: `open`
- Severity: `info`

- Evidence `22da721b-52d4-44ee-b70f-f69152dca4a8` (git_diff)
  - Artifact: `9c2a6ced-a06c-42ba-8a62-9343b0790c81` git-diff.patch
  - Path: `agentguard://6c661326-eb4e-42bf-927b-26d2132a4f32/git-diff.patch`
  - Artifact relative path: `not recorded`
  - Source ref: `9c2a6ced-a06c-42ba-8a62-9343b0790c81`

> A?	.agents/plugins/marketplace.json	untracked
> A?	plugins/proofflow-maintainer/.codex-plugin/plugin.json	untracked
> A?	plugins/proofflow-maintainer/.mcp.json	untracked
> A?	plugins/proofflow-maintainer/README.md	untracked
> A?	plugins/proofflow-maintainer/skills/proofflow-maintainer/SKILL.md	untracked

### Claim: Codex marketplace exposes the repo-local ProofFlow plugin: .agents/plugins/marketplace.json

- Claim ID: `810a9c2c-94a6-4cd3-852f-76dce276b5b2`
- Type: `agentguard_risk`
- Status: `open`
- Severity: `info`

- Evidence `de2dfb91-c258-4a6e-832e-61c91c3adeb3` (git_diff)
  - Artifact: `9c2a6ced-a06c-42ba-8a62-9343b0790c81` git-diff.patch
  - Path: `agentguard://6c661326-eb4e-42bf-927b-26d2132a4f32/git-diff.patch`
  - Artifact relative path: `not recorded`
  - Source ref: `.agents/plugins/marketplace.json`

> Marketplace entry:
> name=proofflow-maintainer
> source.path=./plugins/proofflow-maintainer
> installation=AVAILABLE
> authentication=ON_INSTALL

## Actions

No actions recorded.

## Decisions

No decisions recorded.

## Runs & Test Results

- Run `59b6eaf4-7eda-4f40-b1ad-293ef89f6a51`
  - Type: `agentguard_review`
  - Status: `completed`
  - Started: `2026-05-17T11:48:29.495028Z`
  - Finished: `2026-05-17T11:48:29.827161Z`
  - Test status: `not_run`
  - Test command: `None`
  - Risk level: `medium`

## Remaining Risks

- `medium` Markdown changed-file count statement appears inconsistent: plugins/proofflow-maintainer/README.md
