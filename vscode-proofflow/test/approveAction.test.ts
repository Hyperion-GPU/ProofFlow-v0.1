import assert from "node:assert/strict";
import test from "node:test";

import { approveAction } from "../src/commands/approveAction";
import type { ActionResponse, CaseResponse, DecisionCreatePayload } from "../src/types";
import {
  errorMessages,
  executedCommands,
  infoMessages,
  resetVscodeMock,
  setQuickPickResult,
} from "vscode";

function pendingDecisionAction(overrides: Partial<ActionResponse> = {}): ActionResponse {
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
      },
    },
    created_at: "2026-05-10T00:00:00Z",
    ...overrides,
  };
}

function caseResponse(): CaseResponse {
  return {
    id: "case-1",
    title: "Case one",
    kind: "file_cleanup",
    status: "open",
    created_at: "2026-05-10T00:00:00Z",
    updated_at: "2026-05-10T00:00:00Z",
  };
}

function clientFor(action: ActionResponse) {
  const calls: string[] = [];
  const decisions: DecisionCreatePayload[] = [];
  return {
    calls,
    decisions,
    async listCases(): Promise<CaseResponse[]> {
      return [caseResponse()];
    },
    async listCaseActions(): Promise<ActionResponse[]> {
      return [action];
    },
    async createDecision(
      _caseId: string,
      payload: DecisionCreatePayload
    ): Promise<unknown> {
      calls.push("createDecision");
      decisions.push(payload);
      return {};
    },
    async executeAction(): Promise<unknown> {
      calls.push("executeAction");
      return {};
    },
  };
}

test("approveAction creates policy gate decision before executing action", async () => {
  resetVscodeMock();
  const action = pendingDecisionAction();
  const client = clientFor(action);
  setQuickPickResult({ label: "Case one -> Move file" });

  await approveAction(client as never);

  assert.deepEqual(client.calls, ["createDecision", "executeAction"]);
  assert.equal(client.decisions[0].metadata.action_id, "action-1");
  assert.equal(client.decisions[0].metadata.policy_evaluation_id, "policy-eval-1");
  assert.equal(client.decisions[0].metadata.preview_hash, "preview-hash-1");
  assert.deepEqual(infoMessages, [
    "ProofFlow: Policy gate approved and action executed.",
  ]);
  assert.deepEqual(executedCommands, ["proofflow.refresh"]);
  assert.deepEqual(errorMessages, []);
});

test("approveAction refuses malformed policy gate metadata", async () => {
  resetVscodeMock();
  const action = pendingDecisionAction({ metadata: {} });
  const client = clientFor(action);
  setQuickPickResult({ label: "Case one -> Move file" });

  await approveAction(client as never);

  assert.deepEqual(client.calls, []);
  assert.deepEqual(infoMessages, []);
  assert.deepEqual(executedCommands, []);
  assert.equal(
    errorMessages[0],
    "ProofFlow: selected action is missing policy gate metadata"
  );
});
