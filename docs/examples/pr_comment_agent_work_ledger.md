# Agent Work Ledger PR Comment Template

Use this template when a PR is backed by an Agent Work Ledger Proof Packet.

```markdown
## Agent Work Ledger

**Case:** `<case-id>`  
**Packet:** `<proof-packet-url-or-artifact-path>`  
**Evaluation:** `<ready_for_review | needs_tests | scope_violation | incomplete_evidence | risk_acceptance_required | finished_with_risks>`

### Work Contract

- Objective: `<what the agent was asked to do>`
- Allowed scope: `<paths/modules/workflows>`
- Forbidden actions: `<destructive or out-of-scope actions>`
- Required tests: `<commands>`
- Evidence requirements: `<git_diff, test_output, proof_packet, ...>`

### Snapshots

| Phase | Base ref | HEAD SHA | Changed files | Diff hash |
| --- | --- | --- | ---: | --- |
| start | `<base-ref>` | `<sha>` | `<count>` | `<sha256>` |
| final | `<base-ref>` | `<sha>` | `<count>` | `<sha256>` |

### Evidence

- `<artifact/evidence id>` - `<test output / command output / diff / note>`
- `<artifact/evidence id>` - `<test output / command output / diff / note>`

### Claims

- `[<severity>] <claim text>`  
  Evidence: `<evidence ids>`

### Done Criteria Evaluation

- Passed: `<criteria>`
- Failed: `<criteria>`
- Missing evidence: `<evidence types>`
- Scope violations: `<paths>`
- Warnings: `<warnings>`

### Remaining Risks

- `<open risk or 'none recorded'>`

### Maintainer Decision

- [ ] Ready to merge
- [ ] Needs more tests
- [ ] Scope needs adjustment
- [ ] Risk accepted by maintainer
- [ ] Blocked
```

## Example Filled Comment

```markdown
## Agent Work Ledger

**Case:** `df90faf6-98e3-4dcc-8d53-edcc85ba5e66`  
**Packet:** `proof_packets/df90faf6-98e3-4dcc-8d53-edcc85ba5e66.md`  
**Evaluation:** `ready_for_review`

### Work Contract

- Objective: End-to-end dogfood Agent Work Ledger after implementation.
- Allowed scope: `README.md`, `backend`, `mcp-server`, `plugins`, `docs`, `.codex`
- Forbidden actions: delete user data, remote sync, cloud telemetry, Docker scope expansion
- Required tests:
  - `python -m pytest backend/tests/test_agent_work_ledger.py backend/tests/test_reports_export.py backend/tests/test_case_packet_api.py`
  - `python -m pytest tests/ -v`
- Evidence requirements: `git_diff`, `test_output`

### Snapshots

| Phase | Base ref | HEAD SHA | Changed files | Diff hash |
| --- | --- | --- | ---: | --- |
| start | `HEAD` | `610548c...` | 17 | `340117ed719c594ef323b746445e3b67c5fa1c2fd64a139b4efb4e8ee782f5b1` |
| final | `HEAD` | `610548c...` | 17 | `340117ed719c594ef323b746445e3b67c5fa1c2fd64a139b4efb4e8ee782f5b1` |

### Evidence

- `test_output` - backend Ledger/report/packet tests returned code `0`
- `test_output` - MCP tool tests returned code `0`
- `git_diff` - start and final snapshots recorded matching diff hash

### Claims

- `[info] Required backend and MCP Ledger tests passed during real dogfood.`  
  Evidence: backend test output, MCP test output

### Done Criteria Evaluation

- Passed: required tests, evidence requirements, allowed scope, open risks
- Failed: none
- Missing evidence: none
- Scope violations: none
- Warnings: none

### Remaining Risks

- None recorded.

### Maintainer Decision

- [x] Ready to merge
- [ ] Needs more tests
- [ ] Scope needs adjustment
- [ ] Risk accepted by maintainer
- [ ] Blocked
```
