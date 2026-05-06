"""RC2 policy gate enforcement smoke test.

Validates the full pending_decision lifecycle in an isolated temp environment.
Run from repo root: python scripts/rc2_policy_gate_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

os.environ.setdefault("PROOFFLOW_DB_PATH", "")
os.environ.setdefault("PROOFFLOW_DATA_DIR", "")


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="rc2_gate_smoke_")
    os.environ["PROOFFLOW_DB_PATH"] = str(Path(tmp) / "smoke.db")
    os.environ["PROOFFLOW_DATA_DIR"] = str(Path(tmp) / "pfdata")

    from fastapi.testclient import TestClient
    from proofflow.db import connect
    from proofflow.main import app
    from proofflow.services.json_utils import loads_metadata

    passed = 0
    failed = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failed += 1
            print(f"  FAIL  {label} — {detail}")

    with TestClient(app) as client:
        # --- Health check ---
        print("\n[1/7] Health check")
        health = client.get("/health").json()
        check("version is 0.1.0", health.get("version") == "0.1.0", f"got {health.get('version')}")

        # --- Create case ---
        print("\n[2/7] Create case for gate test")
        case_resp = client.post("/cases", json={
            "title": "Gate smoke case",
            "kind": "local_proof",
            "summary": "Policy gate enforcement smoke test",
        }).json()
        case_id = case_resp["id"]
        check("case created", bool(case_id), case_id)

        # --- Create move_file action (high-risk) ---
        print("\n[3/7] Create and approve move_file action")
        data_dir = Path(tmp) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        src_file = data_dir / "source.txt"
        src_file.write_text("gate smoke content")
        dst_file = data_dir / "dest.txt"

        action_resp = client.post("/actions", json={
            "case_id": case_id,
            "kind": "move_file",
            "title": "Move source to dest",
            "reason": "Policy gate smoke test",
            "preview": {
                "from_path": str(src_file),
                "to_path": str(dst_file),
            },
            "metadata": {
                "source_root": str(data_dir),
                "target_root": str(data_dir),
                "allowed_roots": [str(data_dir)],
            },
        }).json()
        if "id" not in action_resp:
            print(f"  DEBUG action_resp: {json.dumps(action_resp, indent=2)}")
            sys.exit(1)
        action_id = action_resp["id"]
        check("action created", action_resp["status"] in ("pending", "previewed"), action_resp.get("status"))

        # Approve
        client.post(f"/actions/{action_id}/approve")
        actions_list = client.get(f"/cases/{case_id}/actions").json()
        action_after_approve = [a for a in actions_list if a["id"] == action_id][0]
        check("action approved", action_after_approve["status"] == "approved", action_after_approve.get("status"))

        # --- Execute → should pause at pending_decision ---
        print("\n[4/7] Execute → pending_decision gate")
        client.post(f"/actions/{action_id}/execute")
        actions_list = client.get(f"/cases/{case_id}/actions").json()
        action_gated = [a for a in actions_list if a["id"] == action_id][0]
        check("status is pending_decision", action_gated["status"] == "pending_decision",
              action_gated.get("status"))
        check("file NOT moved yet", src_file.exists() and not dst_file.exists(),
              f"src={src_file.exists()} dst={dst_file.exists()}")

        # --- Read gate metadata from action ---
        print("\n[5/7] Verify enforcement evidence")
        packet_resp = client.get(f"/cases/{case_id}/packet").json()
        observations = packet_resp.get("observations", [])
        enforcement_obs = [o for o in observations
                           if o.get("label") == "enforced"]
        check("enforcement observation recorded", len(enforcement_obs) >= 1,
              f"count={len(enforcement_obs)}")

        # Gate metadata is in the action's metadata.policy_gate
        gate_meta = action_gated.get("metadata", {}).get("policy_gate", {})
        check("gate has pipeline_id",
              bool(gate_meta.get("pipeline_id")),
              f"gate_meta keys: {list(gate_meta.keys())}")

        # --- Create Decision to resolve gate ---
        print("\n[6/7] Create decision and re-execute")
        decision_resp = client.post(f"/cases/{case_id}/decisions", json={
            "title": "Approve gate",
            "status": "accepted",
            "rationale": "Smoke test approval",
            "result": "approved by owner",
            "metadata": {
                "decision_kind": "policy_gate_owner_decision",
                "action_id": action_id,
                "policy_evaluation_id": gate_meta.get("pipeline_id", ""),
                "preview_hash": gate_meta.get("preview_hash", ""),
            },
        }).json()
        check("decision created", "id" in decision_resp, str(decision_resp))

        # Re-execute
        client.post(f"/actions/{action_id}/execute")
        actions_list = client.get(f"/cases/{case_id}/actions").json()
        action_final = [a for a in actions_list if a["id"] == action_id][0]
        check("status is executed", action_final["status"] == "executed",
              action_final.get("status"))
        check("file moved", dst_file.exists() and not src_file.exists(),
              f"src={src_file.exists()} dst={dst_file.exists()}")

        # --- Test reject from pending_decision ---
        print("\n[7/7] Reject from pending_decision")
        src2 = Path(tmp) / "data" / "src2.txt"
        src2.write_text("reject test")
        dst2 = Path(tmp) / "data" / "dst2.txt"

        a2_resp = client.post("/actions", json={
            "case_id": case_id,
            "kind": "move_file",
            "title": "Move src2 to dst2",
            "reason": "Reject test",
            "preview": {
                "from_path": str(src2),
                "to_path": str(dst2),
            },
            "metadata": {
                "source_root": str(data_dir),
                "target_root": str(data_dir),
                "allowed_roots": [str(data_dir)],
            },
        }).json()
        a2_id = a2_resp["id"]
        client.post(f"/actions/{a2_id}/approve")
        client.post(f"/actions/{a2_id}/execute")
        actions_list = client.get(f"/cases/{case_id}/actions").json()
        a2_gated = [a for a in actions_list if a["id"] == a2_id][0]
        check("second action gated", a2_gated["status"] == "pending_decision",
              a2_gated.get("status"))

        # Reject
        client.post(f"/actions/{a2_id}/reject")
        actions_list = client.get(f"/cases/{case_id}/actions").json()
        a2_rejected = [a for a in actions_list if a["id"] == a2_id][0]
        check("rejected from pending_decision", a2_rejected["status"] == "rejected",
              a2_rejected.get("status"))
        check("file NOT moved after reject", src2.exists() and not dst2.exists(),
              f"src2={src2.exists()} dst2={dst2.exists()}")

    # --- Summary ---
    print(f"\n{'='*50}")
    print(f"RC2 Policy Gate Smoke: {passed} passed, {failed} failed")
    print(f"Temp dir: {tmp}")
    if failed:
        print("SMOKE FAILED — temp dir preserved for debugging")
        sys.exit(1)
    else:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        print("All clear — temp cleaned up")


if __name__ == "__main__":
    main()
