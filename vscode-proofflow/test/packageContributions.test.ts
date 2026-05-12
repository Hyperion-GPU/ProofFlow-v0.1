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
  const viewItemCommands = manifest.contributes.menus["view/item/context"].map(
    (entry: { command: string }) => entry.command
  );

  assert.ok(commands.has("proofflow.scanFolder"));
  assert.ok(commands.has("proofflow.reviewLastChanges"));
  assert.ok(commands.has("proofflow.approveAction"));
  assert.deepEqual(explorerCommands, [
    "proofflow.scanFolder",
    "proofflow.reviewLastChanges",
  ]);
  assert.deepEqual(viewItemCommands, ["proofflow.approveAction"]);
});
