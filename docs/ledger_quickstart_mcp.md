# Agent Work Ledger MCP Quickstart

This quickstart shows how a Codex or Claude user can record a complete Agent
Work Ledger through ProofFlow MCP tools in about five minutes.

Prerequisites:

- ProofFlow backend running on `http://127.0.0.1:8787`
- `proofflow-mcp` installed and configured for your agent
- A local git repository path, such as `D:\ProofFlow v0.1`

For a one-command release smoke test, run:

```bash
python scripts/ledger_mcp_smoke.py --cleanup
```

## 1. Start The Contract

Tool: `proofflow_start_work_contract`

```json
{
  "objective": "Fix issue triage label handling",
  "repo_path": "D:\\ProofFlow v0.1",
  "allowed_scope": [
    "backend/proofflow/services/issue_triage_service.py",
    "backend/tests"
  ],
  "forbidden_actions": [
    "delete user data",
    "remote sync",
    "cloud telemetry"
  ],
  "required_tests": [
    "python -m pytest backend/tests/test_issue_triage.py"
  ],
  "done_criteria": [
    "Issue labels are preserved",
    "Tests pass",
    "Proof Packet exports"
  ],
  "evidence_requirements": [
    "git_diff",
    "test_output"
  ]
}
```

Expected result:

- A new `agent_work_ledger` Case ID.
- Case metadata contains the work contract.

## 2. Capture The Start Snapshot

Tool: `proofflow_capture_snapshot`

```json
{
  "case_id": "<case-id>",
  "repo_path": "D:\\ProofFlow v0.1",
  "phase": "start",
  "base_ref": "HEAD",
  "include_untracked": true
}
```

Expected result:

- A `git_diff` Artifact.
- Snapshot metadata includes changed files, HEAD SHA, base ref, git status, and
  diff SHA-256.

## 3. Record Work Events

Tool: `proofflow_record_event`

```json
{
  "case_id": "<case-id>",
  "event_type": "implementation",
  "summary": "Updated label preservation logic",
  "content": "Adjusted issue triage parsing and added focused tests.",
  "metadata": {
    "files": [
      "backend/proofflow/services/issue_triage_service.py",
      "backend/tests/test_issue_triage.py"
    ]
  }
}
```

Expected result:

- A `log` Artifact appears in the Ledger Timeline.

## 4. Record Test Evidence

Run your required test locally, then record the output.

Tool: `proofflow_record_evidence`

```json
{
  "case_id": "<case-id>",
  "evidence_type": "test_output",
  "content": "COMMAND: python -m pytest backend/tests/test_issue_triage.py\nRETURN_CODE: 0\n...\n",
  "source_ref": "backend issue triage tests",
  "metadata": {
    "command": "python -m pytest backend/tests/test_issue_triage.py",
    "returncode": 0
  }
}
```

Expected result:

- A `test_output` Artifact.
- An Evidence ID you can bind to a Claim.

## 5. Record An Evidence-Backed Claim

Tool: `proofflow_record_claim`

```json
{
  "case_id": "<case-id>",
  "claim_text": "Issue triage tests passed after the label handling fix.",
  "severity": "info",
  "evidence_ids": [
    "<evidence-id>"
  ]
}
```

Expected result:

- A Claim ID.
- The Evidence row is linked to the Claim.

Hard rule:

- Empty `evidence_ids` returns HTTP 422. ProofFlow will not accept an unbacked
  Claim.

## 6. Capture The Final Snapshot

Tool: `proofflow_capture_snapshot`

```json
{
  "case_id": "<case-id>",
  "repo_path": "D:\\ProofFlow v0.1",
  "phase": "final",
  "base_ref": "HEAD",
  "include_untracked": true
}
```

Expected result:

- A final `git_diff` Artifact.
- The Proof Packet can show exactly which repo state was reviewed.

Hard rule:

- Finishing without a final snapshot returns HTTP 400.

## 7. Evaluate Done Criteria

Tool: `proofflow_evaluate_contract`

```json
{
  "case_id": "<case-id>"
}
```

Expected `ready_for_review` result:

```json
{
  "status": "ready_for_review",
  "passed": [
    "required_tests",
    "evidence_requirements",
    "allowed_scope",
    "open_risks"
  ],
  "failed": [],
  "missing_evidence": [],
  "scope_violations": []
}
```

Common non-ready statuses:

| Status | Trigger |
| --- | --- |
| `needs_tests` | Required test command is missing from Evidence or Artifacts. |
| `scope_violation` | Final snapshot changed files outside `allowed_scope`. |
| `incomplete_evidence` | Required evidence type such as `test_output` is missing. |
| `risk_acceptance_required` | Open medium/high Claim has no accepted Decision. |

## 8. Finish The Ledger

Tool: `proofflow_finish_work_ledger`

```json
{
  "case_id": "<case-id>",
  "summary": "Issue triage label handling fix is ready for review."
}
```

Expected result:

- `finished` when no non-ready evaluation is present.
- `finished_with_risks` when the latest evaluation is not `ready_for_review`.

## 9. Export The Proof Packet

Tool: `proofflow_export_packet`

```json
{
  "case_id": "<case-id>"
}
```

Expected packet sections:

- Work Contract
- Ledger Timeline
- Snapshots
- Claims & Evidence
- Done Criteria Evaluation
- Remaining Risks

## Minimal Agent Prompt

Use this prompt with Codex or Claude after ProofFlow MCP is available:

```text
Use ProofFlow Agent Work Ledger for this task. Start a work contract, capture a
start snapshot, record important events, record test output as Evidence, bind
Claims to Evidence, capture a final snapshot, evaluate the contract, finish the
ledger, and export a Proof Packet. If evaluation is not ready_for_review, report
the failed criteria instead of claiming success.
```
