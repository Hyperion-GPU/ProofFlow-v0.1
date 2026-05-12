import assert from "node:assert/strict";
import test from "node:test";

import { Poller } from "../src/polling";
import type { ActionResponse, CaseResponse } from "../src/types";
import {
  executedCommands,
  infoMessageItems,
  infoMessages,
  resetVscodeMock,
  setInformationMessageSelection,
} from "vscode";

function caseResponse(id: string): CaseResponse {
  return {
    id,
    title: id,
    kind: "file_cleanup",
    status: "open",
    created_at: "2026-05-12T00:00:00Z",
    updated_at: "2026-05-12T00:00:00Z",
  };
}

function action(id: string, status: string): ActionResponse {
  return {
    id,
    case_id: "case-1",
    title: id,
    status,
    kind: "move_file",
    reason: "Needs owner approval",
    created_at: "2026-05-12T00:00:00Z",
  };
}

function clientFor(actionBatches: ActionResponse[][]) {
  let pollIndex = 0;
  return {
    async checkHealth(): Promise<unknown> {
      return { status: "ok", version: "0.1.4" };
    },
    async listCases(): Promise<CaseResponse[]> {
      return [caseResponse("case-1")];
    },
    async listCaseActions(): Promise<ActionResponse[]> {
      const batch = actionBatches[Math.min(pollIndex, actionBatches.length - 1)];
      pollIndex += 1;
      return batch;
    },
  };
}

function statusBar() {
  return {
    online: false,
    pendingCount: -1,
    setOnline(value: boolean): void {
      this.online = value;
    },
    setPendingCount(value: number): void {
      this.pendingCount = value;
    },
  };
}

function treeProvider() {
  return {
    refreshCount: 0,
    refresh(): void {
      this.refreshCount += 1;
    },
  };
}

test("Poller summarizes pending actions and notifies once per new action set", async () => {
  resetVscodeMock();
  const bar = statusBar();
  const tree = treeProvider();
  const poller = new Poller(
    clientFor([
      [action("action-1", "pending_decision"), action("action-2", "executed")],
      [action("action-1", "pending_decision")],
    ]) as never,
    bar as never,
    tree as never
  );

  await poller.pollNow();
  await poller.pollNow();

  assert.equal(bar.online, true);
  assert.equal(bar.pendingCount, 1);
  assert.equal(tree.refreshCount, 2);
  assert.deepEqual(infoMessages, [
    "ProofFlow: 1 action(s) pending decision.",
  ]);
  assert.deepEqual(infoMessageItems, [["Approve Gate & Execute"]]);
  assert.deepEqual(executedCommands, []);
});

test("Poller clears notification state when pending actions clear", async () => {
  resetVscodeMock();
  const bar = statusBar();
  const tree = treeProvider();
  const poller = new Poller(
    clientFor([
      [action("action-1", "pending_decision")],
      [],
      [action("action-1", "pending_decision")],
    ]) as never,
    bar as never,
    tree as never
  );

  await poller.pollNow();
  await poller.pollNow();
  await poller.pollNow();

  assert.equal(bar.pendingCount, 1);
  assert.deepEqual(infoMessages, [
    "ProofFlow: 1 action(s) pending decision.",
    "ProofFlow: 1 action(s) pending decision.",
  ]);
});

test("Poller notification button opens the approve flow", async () => {
  resetVscodeMock();
  setInformationMessageSelection("Approve Gate & Execute");
  const bar = statusBar();
  const tree = treeProvider();
  const poller = new Poller(
    clientFor([[action("action-1", "pending_decision")]]) as never,
    bar as never,
    tree as never
  );

  await poller.pollNow();

  assert.deepEqual(executedCommands, ["proofflow.approveAction"]);
});
