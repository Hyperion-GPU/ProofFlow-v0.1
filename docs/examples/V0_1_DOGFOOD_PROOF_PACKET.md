# ProofFlow v0.1 Dogfood Proof Packet Example

This is a public-safe example packet for the v0.1 RC dogfood path. It uses demo
paths and summarized evidence only. It does not contain private untracked file
content, secrets, or user data.

## Case Summary

- Case ID: `demo-public-v0.1-rc`
- Title: `ProofFlow v0.1 RC Dogfood`
- Workflow type: `local_proof`, `file_cleanup`, and `code_review`
- Status: `accepted`
- Generated: `2026-04-27`
- Release: `ProofFlow v0.1.0-rc1`
- Trust boundary: localhost, local SQLite, local files

## Inputs

- Demo seed command: `python .\scripts\demo_seed.py`
- Backend command: `python -m pytest`
- Frontend commands: `npm run test`, `npm run build`
- LocalProof source root: `sample_data\work\files`
- LocalProof target root: `sample_data\work\sorted`
- AgentGuard repo: `sample_data\repos\demo-agentguard`

## Artifacts

| Artifact | Kind | Source | Public evidence |
| --- | --- | --- | --- |
| Demo note | note | `sample_data\work\manual\manual-review-note.md` | Content summarized; hash recorded in app state |
| LocalProof files | file set | `sample_data\work\files` | Paths and hashes only |
| AgentGuard diff | git diff | demo repo | No sensitive untracked content included |
| Backend test output | test_result | `python -m pytest` | Command status summarized |
| Frontend test output | test_result | `npm run test` | Command status summarized |
| Frontend build output | command_output | `npm run build` | Command status summarized |

## Claims And Evidence

### Claim: ProofFlow can run the v0.1 local evidence graph.

Evidence:

- Case, Artifact, Evidence, Action, Decision, Run, and Proof Packet records are
  visible in CaseDetail.
- Exported packet includes actions, decisions, runs, and remaining risks.

### Claim: LocalProof cleanup actions are previewed, scoped, and undoable.

Evidence:

- `mkdir_dir` action requires preview and approval before execution.
- `move_file` action depends on the prerequisite directory action.
- `move_file` undo restores the original file only when the hash guard matches.
- Action metadata includes `source_root`, `target_root`, and `allowed_roots`.

### Claim: AgentGuard does not trust unsupported review claims.

Evidence:

- Review findings are stored as claims with linked evidence.
- Oversized or sensitive untracked content is omitted rather than stored.
- Test command metadata is attached to the review run.

## Actions

| Action | Preview | Approval | Execution | Undo |
| --- | --- | --- | --- | --- |
| Create category directory | Present | Approved | Executed | Removed if empty |
| Move demo note | Present | Approved | Executed | Restored with hash guard |
| Manual evidence review | No file mutation | Approved | Recorded | No file undo operation |

## Decisions

- Decision: accept the demo evidence packet for v0.1 RC smoke review.
- Rationale: the packet contains source artifacts, evidence-backed claims,
  previewed actions, undo records, test evidence, and known limitations.
- Result: use this packet shape as the public dogfood example for release review.

## Reproduction

```powershell
cd "D:\ProofFlow v0.1"
python .\scripts\demo_seed.py

cd .\backend
python -m pytest
python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload
```

```powershell
cd "D:\ProofFlow v0.1\frontend"
npm ci
npm run test
npm run build
npm run dev
```

Then open `http://127.0.0.1:5173`, inspect the seeded cases, run the LocalProof
action lifecycle, run AgentGuard against the local demo repository, and export a
Proof Packet.

## Verification Checklist

- Backend pytest passes.
- Frontend tests pass.
- Frontend build passes.
- Health metadata and Dashboard release stamp show `ProofFlow v0.1.0-rc1`.
- LocalProof scan creates artifacts and text chunks.
- Suggested actions show preview before approval.
- Filesystem action metadata includes allowed roots.
- Undo records include hash guards for file moves.
- AgentGuard claims have linked evidence.
- Exported packet contains remaining risks and known limits.

## Remaining Risks

- No auth.
- No multi-user workflow.
- No cloud sync.
- No vector RAG.
- No ComfyUI execution.
- No automatic AI code edits.
- Localhost remains the v0.1 trust boundary.
