import * as vscode from "vscode";
import { ProofFlowClient } from "../api/client";
import type { ActionResponse } from "../types";
import { ApproveGatePanel } from "../webviews/approveGate";
import { buildPolicyGateDecisionPayload } from "./policyGateDecision";
import type { McpClient } from "../mcp/client";
import type { LedgerStore } from "../store/ledgerStore";

export interface ApproveActionContext {
  client: McpClient;
  store: LedgerStore;
  extensionUri: vscode.Uri;
}

/**
 * Lets the user pick a pending policy-gate action and decide on it. Defaults
 * to opening the rich Approve Gate webview when context is available so the
 * reviewer sees diff + risk claims; falls back to the legacy QuickPick flow
 * when only the legacy ProofFlowClient is wired (kept for tests).
 */
export async function approveAction(
  client: ProofFlowClient,
  ctx?: ApproveActionContext
): Promise<void> {
  const cases = await client.listCases().catch(() => []);
  if (cases.length === 0) {
    vscode.window.showInformationMessage("ProofFlow: No cases found.");
    return;
  }

  const pendingActions: { label: string; action: ActionResponse }[] = [];
  for (const c of cases) {
    const actions = await client.listCaseActions(c.id).catch(() => []);
    for (const a of actions) {
      if (a.status === "pending_decision" || a.status === "pending") {
        pendingActions.push({
          label: `${c.title} -> ${a.title}`,
          action: a,
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

  if (ctx) {
    await ApproveGatePanel.show(ctx, picked.action.id, picked.action.case_id);
    return;
  }

  // Fallback path used by unit tests that pass a duck-typed client without the
  // MCP context. Mirrors the legacy policy-gate decision flow.
  try {
    const decisionPayload = buildPolicyGateDecisionPayload(picked.action);
    await client.createDecision(picked.action.case_id, decisionPayload);
    await client.executeAction(picked.action.id);
    vscode.window.showInformationMessage(
      "ProofFlow: Policy gate approved and action executed."
    );
    vscode.commands.executeCommand("proofflow.refresh");
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
  }
}
