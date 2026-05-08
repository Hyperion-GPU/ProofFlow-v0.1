import * as vscode from "vscode";
import { ProofFlowClient } from "../api/client";

export async function approveAction(client: ProofFlowClient): Promise<void> {
  const cases = await client.listCases().catch(() => []);
  if (cases.length === 0) {
    vscode.window.showInformationMessage("ProofFlow: No cases found.");
    return;
  }

  const pendingActions: { label: string; actionId: string }[] = [];
  for (const c of cases) {
    const actions = await client.listCaseActions(c.id).catch(() => []);
    for (const a of actions) {
      if (a.status === "pending_decision") {
        pendingActions.push({
          label: `${c.title} → ${a.title}`,
          actionId: a.id,
        });
      }
    }
  }

  if (pendingActions.length === 0) {
    vscode.window.showInformationMessage(
      "ProofFlow: No pending actions to approve."
    );
    return;
  }

  const picked = await vscode.window.showQuickPick(pendingActions, {
    placeHolder: "Select action to approve",
  });
  if (!picked) {
    return;
  }

  try {
    await client.approveAction(picked.actionId);
    await client.executeAction(picked.actionId);
    vscode.window.showInformationMessage(
      `ProofFlow: Action approved and executed.`
    );
    vscode.commands.executeCommand("proofflow.refresh");
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
  }
}
