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

To exercise non-blocking Risk Hints with a synthetic local scenario, run:

```bash
python scripts/ledger_risk_hints_smoke.py --cleanup
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
  ],
  "algorithm_requirements": [
    "Choose the label preservation algorithm before editing code"
  ],
  "cost_budget": {
    "max_api_calls": 0,
    "max_gpu_jobs": 0
  }
}
```

Expected result:

- A new `agent_work_ledger` Case ID.
- Case metadata contains the work contract, algorithm requirements, and cost
  budget constraints.

## 2. Record The Algorithm Decision

Tool: `proofflow_record_algorithm_decision`

```json
{
  "case_id": "<case-id>",
  "summary": "Preserve labels during deterministic parsing",
  "chosen_approach": "Normalize incoming labels and preserve the original list when component inference runs.",
  "rationale": "This keeps source issue labels as provenance instead of regenerating them later.",
  "alternatives_considered": [
    "Recompute labels from issue body only"
  ],
  "invariants": [
    "User-provided labels remain in the triage output"
  ],
  "forbidden_approaches": [
    "Drop original labels before inference"
  ]
}
```

Expected result:

- An `algorithm_decision` Artifact.
- The Proof Packet can show the selected approach, rationale, alternatives,
  invariants, and forbidden approaches.

## 3. Record The Cost Budget

Tool: `proofflow_record_cost_budget`

```json
{
  "case_id": "<case-id>",
  "summary": "No remote calls or GPU work for deterministic issue triage",
  "budget": {
    "max_api_calls": 0,
    "max_gpu_jobs": 0,
    "max_runtime_seconds": 60
  },
  "expected_operations": [
    "local parser update",
    "targeted pytest run"
  ],
  "limits": [
    "Do not call external labeling services",
    "Do not run model inference for this deterministic fix"
  ]
}
```

Expected result:

- A `cost_budget` Artifact.
- Evaluation can confirm the contract's declared budget was recorded before
  work proceeds.

## 4. Capture The Start Snapshot

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

## 5. Record Work Events

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

## 6. Record Test Evidence

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

## 7. Record An Evidence-Backed Claim

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

## 8. Capture The Final Snapshot

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

## 9. Evaluate Done Criteria

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
    "algorithm_decision",
    "cost_budget",
    "evidence_requirements",
    "allowed_scope",
    "open_risks"
  ],
  "failed": [],
  "missing_evidence": [],
  "scope_violations": [],
  "risk_hints": []
}
```

Common non-ready statuses:

| Status | Trigger |
| --- | --- |
| `needs_tests` | Required test command is missing from Evidence or Artifacts. |
| `scope_violation` | Final snapshot changed files outside `allowed_scope`. |
| `missing_algorithm_decision` | Contract requires an algorithm decision but none is recorded. |
| `missing_cost_budget` | Contract declares a cost budget but none is recorded. |
| `incomplete_evidence` | Required evidence type such as `test_output` is missing. |
| `risk_acceptance_required` | Open medium/high Claim has no accepted Decision. |

Risk Hints may appear even when `status` is `ready_for_review`. Treat them as
review prompts for routes that may be wrong or too expensive, such as
regeneration where the contract required mapping, budget overrun metadata, or
test output that proves the result but not the method.

## 10. Finish The Ledger

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

## 11. Export The Proof Packet

Tool: `proofflow_export_packet`

```json
{
  "case_id": "<case-id>"
}
```

Expected packet sections:

- Work Contract
- Algorithm Decisions
- Cost Budget
- Ledger Timeline
- Snapshots
- Claims & Evidence
- Done Criteria Evaluation
- Risk Hints when evaluation records them
- Remaining Risks

## Minimal Agent Prompt

Use this prompt with Codex or Claude after ProofFlow MCP is available:

```text
Use ProofFlow Agent Work Ledger for this task. Start a work contract, record the
algorithm decision, record the cost budget, capture a start snapshot, record
important events, record test output as Evidence, bind Claims to Evidence,
capture a final snapshot, evaluate the contract, finish the ledger, and export a
Proof Packet. If evaluation is not ready_for_review, report the failed criteria
instead of claiming success. If risk_hints is non-empty, report those hints as
items for human review even when the status is ready_for_review.
```
