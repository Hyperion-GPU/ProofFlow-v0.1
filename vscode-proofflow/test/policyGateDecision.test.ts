import assert from "node:assert/strict";
import test from "node:test";

import { buildPolicyGateDecisionPayload } from "../src/commands/policyGateDecision";
import type { ActionResponse } from "../src/types";

function action(overrides: Partial<ActionResponse> = {}): ActionResponse {
  return {
    id: "action-1",
    case_id: "case-1",
    title: "Move file",
    status: "pending_decision",
    kind: "move_file",
    reason: "Needs owner approval",
    metadata: {
      policy_gate: {
        pipeline_id: "policy-eval-1",
        preview_hash: "preview-hash-1",
        reason: "high-risk action requires owner decision",
      },
    },
    created_at: "2026-05-10T00:00:00Z",
    ...overrides,
  };
}

test("builds an accepted policy gate owner decision payload", () => {
  const payload = buildPolicyGateDecisionPayload(action());

  assert.equal(payload.status, "accepted");
  assert.equal(payload.result, "approved");
  assert.equal(payload.metadata.decision_kind, "policy_gate_owner_decision");
  assert.equal(payload.metadata.action_id, "action-1");
  assert.equal(payload.metadata.policy_evaluation_id, "policy-eval-1");
  assert.equal(payload.metadata.preview_hash, "preview-hash-1");
  assert.equal(payload.metadata.source, "vscode-proofflow");
});

test("rejects actions without policy gate metadata", () => {
  assert.throws(
    () => buildPolicyGateDecisionPayload(action({ metadata: {} })),
    /missing policy gate metadata/
  );
});

test("rejects actions without policy gate pipeline_id", () => {
  assert.throws(
    () =>
      buildPolicyGateDecisionPayload(
        action({
          metadata: {
            policy_gate: {
              preview_hash: "preview-hash-1",
            },
          },
        })
      ),
    /missing policy gate pipeline_id/
  );
});

test("rejects actions without policy gate preview_hash", () => {
  assert.throws(
    () =>
      buildPolicyGateDecisionPayload(
        action({
          metadata: {
            policy_gate: {
              pipeline_id: "policy-eval-1",
            },
          },
        })
      ),
    /missing policy gate preview_hash/
  );
});
