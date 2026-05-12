import assert from "node:assert/strict";
import test from "node:test";

import { scanFolder } from "../src/commands/scanFolder";
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
  const scannedPaths: string[] = [];
  return {
    scannedPaths,
    async scan(folderPath: string): Promise<unknown> {
      scannedPaths.push(folderPath);
      return { case_id: "case-1", files_seen: 3, artifacts_created: 2 };
    },
  };
}

test("scanFolder uses explicit explorer folder URI when provided", async () => {
  resetVscodeMock();
  const proofFlowClient = client();

  await scanFolder(proofFlowClient as never, uri("C:\\repo\\selected") as never);

  assert.deepEqual(proofFlowClient.scannedPaths, ["C:\\repo\\selected"]);
  assert.deepEqual(infoMessages, [
    "ProofFlow: Scan complete - 3 file(s), 2 artifact(s)",
  ]);
  assert.deepEqual(executedCommands, ["proofflow.refresh"]);
  assert.deepEqual(errorMessages, []);
});

test("scanFolder keeps workspace picker behavior without explicit URI", async () => {
  resetVscodeMock();
  const first = workspaceFolder("C:\\repo\\one");
  const second = workspaceFolder("C:\\repo\\two");
  setWorkspaceFolders([first, second]);
  setWorkspaceFolderPickResult(second);
  const proofFlowClient = client();

  await scanFolder(proofFlowClient as never);

  assert.deepEqual(proofFlowClient.scannedPaths, ["C:\\repo\\two"]);
  assert.deepEqual(executedCommands, ["proofflow.refresh"]);
  assert.deepEqual(errorMessages, []);
});
