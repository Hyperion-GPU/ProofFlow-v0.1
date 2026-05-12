import assert from "node:assert/strict";
import test from "node:test";

import { reviewChanges } from "../src/commands/reviewChanges";
import {
  errorMessages,
  executedCommands,
  infoMessages,
  resetVscodeMock,
  setWorkspaceFolderPickResult,
  setWorkspaceFolders,
  uri,
  workspaceFolder,
} from "vscode";

function client() {
  const reviewedPaths: string[] = [];
  return {
    reviewedPaths,
    async review(repoPath: string): Promise<unknown> {
      reviewedPaths.push(repoPath);
      return {
        case_id: "case-1",
        run_id: "run-1",
        risk_level: "medium",
        claims_created: 4,
        evidence_created: 5,
        changed_files: ["a.ts", "b.ts"],
      };
    },
  };
}

test("reviewChanges resolves explicit explorer URI to workspace root", async () => {
  resetVscodeMock();
  const root = workspaceFolder("C:\\repo");
  setWorkspaceFolders([root]);
  const proofFlowClient = client();

  await reviewChanges(
    proofFlowClient as never,
    uri("C:\\repo\\src\\file.ts") as never
  );

  assert.deepEqual(proofFlowClient.reviewedPaths, ["C:\\repo"]);
  assert.deepEqual(infoMessages, [
    "ProofFlow: Review complete - medium risk, 4 claim(s), 2 file(s)",
  ]);
  assert.deepEqual(executedCommands, ["proofflow.refresh"]);
  assert.deepEqual(errorMessages, []);
});

test("reviewChanges keeps workspace picker behavior without explicit URI", async () => {
  resetVscodeMock();
  const first = workspaceFolder("C:\\repo\\one");
  const second = workspaceFolder("C:\\repo\\two");
  setWorkspaceFolders([first, second]);
  setWorkspaceFolderPickResult(first);
  const proofFlowClient = client();

  await reviewChanges(proofFlowClient as never);

  assert.deepEqual(proofFlowClient.reviewedPaths, ["C:\\repo\\one"]);
  assert.deepEqual(executedCommands, ["proofflow.refresh"]);
  assert.deepEqual(errorMessages, []);
});

test("reviewChanges rejects explicit URI outside the workspace", async () => {
  resetVscodeMock();
  setWorkspaceFolders([workspaceFolder("C:\\repo")]);
  const proofFlowClient = client();

  await reviewChanges(
    proofFlowClient as never,
    uri("D:\\outside\\file.ts") as never
  );

  assert.deepEqual(proofFlowClient.reviewedPaths, []);
  assert.deepEqual(errorMessages, [
    "ProofFlow: Selected item is not inside a workspace folder.",
  ]);
});
