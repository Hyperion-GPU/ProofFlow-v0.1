# Ledger Risk Hints Dogfood Matrix

Generated from:

```bash
python scripts/ledger_risk_hints_dogfood_matrix.py --cleanup
```

The matrix uses local synthetic repositories and the real MCP tool handlers. No
external API, GPU, cloud service, or user data is required.

## Results

| Scenario | Purpose | Expected hints | Actual hints | Result |
| --- | --- | --- | --- | --- |
| Data conversion lineage | Preserve mapping/lineage contract records a regenerate route and cost overrun. | `forbidden_algorithm_mentioned`, `regeneration_over_mapping`, `cost_budget_possible_overrun`, `test_proves_output_not_method` | Same as expected | PASS |
| State sync | Preserve source mapping contract records recreate-from-cache route, with method evidence present. | `regeneration_over_mapping` | Same as expected | PASS |
| Expensive external call | API/GPU/LLM usage is recorded while the ledger has no structured budget. | `expensive_action_without_budget` | Same as expected | PASS |
| Refactor behavior preservation | Output tests pass but a method-sensitive refactor lacks trace evidence. | `test_proves_output_not_method` | Same as expected | PASS |
| Clean method-evidence baseline | Mapping, algorithm trace, cost report, and in-budget usage are present. | None | None | PASS |

## Dogfood Notes

- Risk Hints are useful across data conversion, state sync, external service,
  and refactor workflows without adding domain-specific code.
- The clean baseline shows that method evidence such as `mapping`,
  `algorithm_trace`, and `cost_report` can keep a method-sensitive contract
  quiet when usage stays in budget.
- A route mentioned only as a rejected or forbidden approach is still review
  context. Future accepted Decision explanations should distinguish "the agent
  used this route" from "the ledger recorded this route as forbidden."

## Recommendation

Do not add global hint suppression. Add an evidence-backed Accepted Decision
explanation chain so maintainers can explain expected hints, false positives, or
accepted tradeoffs without deleting the audit signal.
