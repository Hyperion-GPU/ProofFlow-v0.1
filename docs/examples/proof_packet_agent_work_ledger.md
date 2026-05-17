# Proof Packet Example: Agent Work Ledger

> This public-safe example shows how a maintainer can summarize complex Codex
> work with a lightweight Agent Work Ledger. It uses shortened paths and
> representative evidence only.

## Case Summary

- Case ID: `demo-agent-work-ledger`
- Title: `Codex Plugin Dogfood Documentation Update`
- Workflow type: `agent_work_ledger`
- Status: `open`
- Generated: `2026-05-17`
- Trust boundary: localhost, local repository, local ProofFlow MCP server

## Agent Work Ledger

| Field | Entry |
| --- | --- |
| Goal | Update the ProofFlow maintainer plugin docs to guide complex code tasks through an Agent Work Ledger. |
| Scope | `plugins/proofflow-maintainer`, `docs/examples`, and root README entry points. |
| Evidence | Git diff, target markdown files, and final documentation review. |
| Decisions | Keep the change documentation-only and avoid backend or MCP server code. |
| Open risks | No runtime tests were needed for this docs-only example. |

## Artifacts

| Artifact | Kind | Source | Public evidence |
| --- | --- | --- | --- |
| Skill update | markdown | `plugins/proofflow-maintainer/skills/proofflow-maintainer/SKILL.md` | Ledger workflow steps added. |
| Example packet | markdown | `docs/examples/proof_packet_agent_work_ledger.md` | Public-safe handoff format. |
| README entry | markdown | `README.md` | Maintainer plugin and example packet links. |

## Claims And Evidence

### Claim: Complex Codex tasks should keep a concise ledger.

Evidence:

- The maintainer skill asks agents to record goal, scope, evidence, decisions,
  and open risks before final handoff.
- The ledger points durable evidence to ProofFlow Cases, Claims, Evidence, and
  exported Proof Packets when available.

### Claim: The documentation update stays inside the dogfood scope.

Evidence:

- The example scope is limited to plugin documentation, public examples, and
  README entry points.
- No backend, frontend, MCP server, or database behavior is changed.

## Verification Checklist

- Read the maintainer skill and confirm the Agent Work Ledger path is present.
- Open this example packet and confirm it contains goal, scope, evidence,
  decisions, and open risks.
- Check `README.md` for links to the new example and plugin workflow.

## Remaining Risks

- This is a documentation example, not a generated packet from a live backend
  run.
- Maintainers still need to run project-specific tests before accepting code
  workflow claims.
