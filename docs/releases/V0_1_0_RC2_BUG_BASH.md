# ProofFlow v0.1.0-rc2 Bug Bash

## Goal

Validate the policy gate enforcement feature added in RC2 before cutting the
final v0.1.0 release.

## Current release

- Backend: `0.1.0-rc2`
- Frontend: `0.1.0-rc2`
- Branch: `frontend/policy-gate-decision-ui` (merged to main)

## Automated smoke commands

```bash
# Existing RC API smoke (LocalProof + AgentGuard + Packet)
python scripts/rc_api_smoke.py

# Policy gate enforcement smoke (NEW)
python scripts/rc2_policy_gate_smoke.py

# Backend tests
cd backend && python -m pytest -q

# Frontend tests + build
cd frontend && npm test && npm run build
```

## Results

| Check | Result | Notes |
|-------|--------|-------|
| `rc_api_smoke.py` | PASS | LocalProof, AgentGuard, Packet all green |
| `rc2_policy_gate_smoke.py` | PASS | 14/14 checks pass |
| Backend tests | PASS | 267 passed, 3 skipped |
| Frontend tests | PASS | 24 passed |
| Frontend build | PASS | Clean production build |

## Policy gate enforcement checklist

| Step | Expected | Actual | Status |
|------|----------|--------|--------|
| Health reports 0.1.0-rc2 | version=0.1.0-rc2 | version=0.1.0-rc2 | PASS |
| Create case | case_id returned | case_id returned | PASS |
| Create move_file action | status=previewed | status=previewed | PASS |
| Approve action | status=approved | status=approved | PASS |
| Execute → gate triggers | status=pending_decision | status=pending_decision | PASS |
| File NOT moved while gated | src exists, dst absent | src exists, dst absent | PASS |
| Enforcement observation in packet | label=enforced | label=enforced | PASS |
| Gate metadata has pipeline_id | non-empty | non-empty | PASS |
| Create accepted Decision | decision created | decision created | PASS |
| Re-execute after decision | status=executed | status=executed | PASS |
| File moved after resolution | dst exists, src absent | dst exists, src absent | PASS |
| Second action gated | status=pending_decision | status=pending_decision | PASS |
| Reject from pending_decision | status=rejected | status=rejected | PASS |
| File NOT moved after reject | src exists, dst absent | src exists, dst absent | PASS |

## Manual UI checklist

| Step | Status |
|------|--------|
| CaseDetail shows orange "pending_decision" pill | Verified in component tests |
| Gate banner shows reason and categories | Verified in component tests |
| "Approve & Resolve Gate" button creates decision | Verified in component tests |
| Execute after approval completes action | Verified in component tests |

## Bug triage rules

- P0 (blocker): data loss, security bypass, gate fails closed incorrectly
- P1 (release-blocking): gate fails open when it should block, evidence not recorded
- P2 (defer): cosmetic UI issues, non-critical error messages

## v0.1.0 decision criteria

All automated checks pass. No P0 or P1 bugs found. RC2 is ready for final
release as v0.1.0.

## Out of scope / Known limitations

- No auth (localhost trust boundary)
- No multi-user workflow
- No cloud sync
- No vector RAG
- No automatic AI code edits
