import type { ActionResponse, DecisionCreatePayload } from "../types";

export function buildPolicyGateDecisionPayload(
  action: ActionResponse
): DecisionCreatePayload {
  if (action.status !== "pending_decision") {
    throw new Error("selected action is not pending_decision");
  }

  const gate = action.metadata?.policy_gate;
  if (!gate) {
    throw new Error("selected action is missing policy gate metadata");
  }

  const policyEvaluationId = gate.pipeline_id;
  if (typeof policyEvaluationId !== "string" || policyEvaluationId.length === 0) {
    throw new Error("selected action is missing policy gate pipeline_id");
  }

  const previewHash = gate.preview_hash;
  if (typeof previewHash !== "string" || previewHash.length === 0) {
    throw new Error("selected action is missing policy gate preview_hash");
  }

  return {
    title: `Approve policy gate for ${action.title}`,
    status: "accepted",
    rationale: "Owner approved this gated action from the VS Code extension.",
    result: "approved",
    metadata: {
      decision_kind: "policy_gate_owner_decision",
      action_id: action.id,
      policy_evaluation_id: policyEvaluationId,
      preview_hash: previewHash,
      source: "vscode-proofflow",
    },
  };
}
