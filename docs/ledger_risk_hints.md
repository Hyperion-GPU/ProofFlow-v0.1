# Ledger Risk Hints

Risk Hints are non-blocking review prompts emitted by Agent Work Ledger
evaluation. They do not replace maintainer judgment and they do not change
`ready_for_review`. Their job is narrower: make the evidence flow say, in plain
terms, when the work may have taken a route that deserves human attention.

ProofFlow still does not decide which algorithm is correct. It can, however,
notice that the recorded contract, algorithm decision, cost budget, events, and
evidence appear to disagree.

## Where They Appear

- REST: `POST /ledger/cases/{case_id}/evaluate` returns `risk_hints`.
- MCP: `proofflow_evaluate_contract` prints the hint count and the first hints.
- Proof Packet: `## Done Criteria Evaluation` includes `Risk Hints`.
- Storage: hints are stored in `runs.metadata_json.risk_hints`.

For a cross-domain dogfood matrix, see
[`examples/ledger_risk_hints_dogfood_matrix.md`](examples/ledger_risk_hints_dogfood_matrix.md).

## Current Deterministic Rules

| Code | Meaning |
| --- | --- |
| `forbidden_algorithm_mentioned` | An Algorithm Decision or Evidence record mentions a forbidden approach. |
| `regeneration_over_mapping` | The contract asks to preserve source mapping or lineage, but recorded work mentions regeneration or reruns. |
| `expensive_action_without_budget` | Evidence or events mention API, GPU, ASR, LLM batch, video generation, or external service work without a Cost Budget. |
| `cost_budget_possible_overrun` | Recorded usage metadata exceeds structured budget limits such as `max_api_calls` or `max_gpu_jobs`. |
| `test_proves_output_not_method` | Test output exists, but a method-sensitive contract lacks lineage, mapping, algorithm trace, or cost report evidence. |

## Expected False Positives

Hints are deterministic keyword and metadata checks. They can fire when a
forbidden route is discussed as a rejected idea, when a term appears in a file
name, or when usage metadata is approximate. Treat them as review prompts, not
automatic failures.

When a hint is expected, record a Decision or Evidence explaining why. For
example, a maintainer may accept a cost overrun after seeing a cost report, or
confirm that a forbidden approach was only listed as a rejected alternative.

## General Scenarios

- Data conversion: a contract requires source lineage, but the implementation
  regenerates derived rows instead of preserving a mapping.
- Expensive calls: an agent records API, GPU, ASR, LLM batch, or external
  service usage without a budget.
- External service tests: tests pass because a generated output looks valid,
  but no evidence proves the method stayed within the intended route.
- State sync: a workflow recreates remote/local state instead of applying an
  expected diff or mapping.
- Refactor: output-level tests pass, but no algorithm trace proves behavior was
  preserved through a risky rewrite.

## Dogfood Command

Run the full local matrix with:

```bash
python scripts/ledger_risk_hints_dogfood_matrix.py --cleanup
```
