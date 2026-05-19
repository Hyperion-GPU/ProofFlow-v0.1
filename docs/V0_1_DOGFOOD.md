# ProofFlow v0.1 Dogfood Guide

This guide keeps the v0.1 demo path local and repeatable. It does not require
cloud services, Docker, vector RAG, ComfyUI, or automatic AI code edits.

## Goal

Run the local MVP from seeded demo data through UI workflows and a Proof Packet
export:

- seed demo data,
- start the backend on `127.0.0.1:8787`,
- start the frontend on `127.0.0.1:5173`,
- run a LocalProof scan,
- run LocalProof suggest-actions,
- approve, execute, and undo actions,
- run AgentGuard against a local git repo,
- export a Proof Packet.

For release-candidate verification, also use
[V0_1_RC_CHECKLIST.md](V0_1_RC_CHECKLIST.md). A public-safe packet example is
available at [examples/V0_1_DOGFOOD_PROOF_PACKET.md](examples/V0_1_DOGFOOD_PROOF_PACKET.md).
The post-release RC1 bug bash log is tracked in
[releases/V0_1_0_RC1_BUG_BASH.md](releases/V0_1_0_RC1_BUG_BASH.md).

## Commands

All commands below run in a single PowerShell session. Each block uses
`Push-Location` / `Pop-Location` so the working directory is restored after
the block, which lets you paste the next block without manually adjusting
`cd`. Substitute `"<repo root>"` with the absolute path of your local clone
(double quotes are required because the path may contain spaces, for example
`"D:\ProofFlow v0.1"`). The backend port is fixed to `8787` to match the
`make dev-backend` baseline.

Seed demo data:

```powershell
Push-Location "<repo root>"
python .\scripts\demo_seed.py
Pop-Location
```

Run the API smoke helper with temporary DB/data paths:

```powershell
Push-Location "<repo root>"
python .\scripts\rc_api_smoke.py
Pop-Location
```

The helper keeps its temp packet for inspection unless you pass `--cleanup`.

Run backend checks:

```powershell
Push-Location "<repo root>\backend"
python -m pytest
Pop-Location
```

Start the backend (long-running uvicorn process):

```powershell
Push-Location "<repo root>\backend"
python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787 --reload
Pop-Location
```

Start and verify the frontend (long-running `npm run dev`; recommended in a
second PowerShell session):

```powershell
Push-Location "<repo root>\frontend"
npm ci
npm run test
npm run build
npm run dev
Pop-Location
```

Open `http://127.0.0.1:5173`.

## Dogfood Flow

1. Confirm backend health from the Dashboard.
2. Open LocalProof and scan a local folder.
3. Run suggest-actions with a local target root.
4. Review the suggested action preview before approving anything.
5. Approve and execute any required `mkdir_dir` action.
6. Approve and execute the dependent `move_file` action.
7. Undo the `move_file` action.
8. Undo the `mkdir_dir` action if the created directory is empty.
9. Open AgentGuard and run a review against a local git repository.
10. Open the generated CaseDetail page and inspect artifacts, claims, evidence,
    actions, decisions, and runs.
11. Export the Proof Packet markdown.

## Acceptance Checklist

- Backend health is ok.
- Dashboard shows `ProofFlow v0.1.0-rc1` from backend health metadata.
- Dashboard loads cases.
- LocalProof scan creates or updates artifacts and text chunks.
- LocalProof suggested actions show preview before execution.
- `mkdir_dir` and `move_file` can be approved, executed, and undone.
- AgentGuard creates a Case with changed files, run metadata, claims, and
  evidence.
- CaseDetail displays Claims & Evidence, Actions, Decisions, and Runs & Test
  Results.
- Proof Packet markdown exports successfully.
- No sensitive untracked file content appears in the AgentGuard packet.

## Known Demo Limitations

- No auth.
- No multi-user workflow.
- No cloud sync.
- No vector RAG.
- No ComfyUI execution.
- No automatic AI code edits.
