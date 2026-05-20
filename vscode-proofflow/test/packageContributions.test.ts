import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const manifest = JSON.parse(readFileSync("package.json", "utf8"));

test("manifest wires ProofFlow thin UX menus to existing commands", () => {
  const commands = new Set(
    manifest.contributes.commands.map(
      (command: { command: string }) => command.command
    )
  );
  const explorerCommands = manifest.contributes.menus["explorer/context"].map(
    (entry: { command: string }) => entry.command
  );
  const viewItemCommands = new Set(
    manifest.contributes.menus["view/item/context"].map(
      (entry: { command: string }) => entry.command
    )
  );

  assert.ok(commands.has("proofflow.scanFolder"));
  assert.ok(commands.has("proofflow.reviewLastChanges"));
  assert.ok(commands.has("proofflow.approveAction"));
  assert.deepEqual(explorerCommands, [
    "proofflow.scanFolder",
    "proofflow.reviewLastChanges",
  ]);
  assert.ok(viewItemCommands.has("proofflow.approveAction"));
});

test("manifest exposes the ledger workflow commands and view", () => {
  const commands = new Set(
    manifest.contributes.commands.map(
      (command: { command: string }) => command.command
    )
  );
  for (const cmd of [
    "proofflow.startWorkContract",
    "proofflow.recordEvent",
    "proofflow.recordAlgorithmDecision",
    "proofflow.recordCostBudget",
    "proofflow.captureSnapshot",
    "proofflow.recordEvidence",
    "proofflow.recordClaim",
    "proofflow.evaluateContract",
    "proofflow.finishWorkLedger",
    "proofflow.openCaseDetail",
    "proofflow.exportPacket",
  ]) {
    assert.ok(commands.has(cmd), `missing command ${cmd}`);
  }

  const ledgerView = manifest.contributes.views["proofflow-sidebar"].find(
    (v: { id: string }) => v.id === "proofflow.ledgerView"
  );
  assert.ok(ledgerView, "ledger view registered");
});

test("manifest declares core configuration options", () => {
  const props = manifest.contributes.configuration.properties;
  assert.ok(props["proofflow.backendUrl"]);
  assert.ok(props["proofflow.apiKey"]);
  assert.ok(props["proofflow.autoRefresh"]);
});
