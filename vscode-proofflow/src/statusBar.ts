import * as vscode from "vscode";
import type { ProofFlowMcpState } from "./mcp/types";

export class StatusBar {
  private item: vscode.StatusBarItem;
  private pendingCount = 0;
  private online = false;
  private mcpState: ProofFlowMcpState = "idle";
  private mcpDetail: string | undefined;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
    this.item.command = "proofflow.casesView.focus";
    this.render();
    this.item.show();
  }

  setOnline(online: boolean): void {
    this.online = online;
    this.render();
  }

  setPendingCount(count: number): void {
    this.pendingCount = count;
    this.render();
  }

  setMcpState(state: ProofFlowMcpState, detail?: string): void {
    this.mcpState = state;
    this.mcpDetail = detail;
    this.render();
  }

  private render(): void {
    const mcpLabel = mcpStateLabel(this.mcpState);

    if (this.mcpState === "failed") {
      this.item.text = `$(shield) ProofFlow: MCP ${mcpLabel}`;
      this.item.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.errorBackground"
      );
      this.item.tooltip =
        this.mcpDetail ||
        "ProofFlow MCP server failed to start. Check Output > ProofFlow.";
      return;
    }

    if (this.mcpState === "starting" || this.mcpState === "restarting") {
      this.item.text = `$(sync~spin) ProofFlow: MCP ${mcpLabel}`;
      this.item.backgroundColor = undefined;
      this.item.tooltip = `ProofFlow MCP ${mcpLabel}…`;
      return;
    }

    if (!this.online) {
      this.item.text = "$(shield) ProofFlow: Backend offline";
      this.item.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.warningBackground"
      );
      this.item.tooltip = "ProofFlow backend is not reachable via MCP";
      return;
    }

    if (this.pendingCount > 0) {
      this.item.text = `$(shield) ProofFlow (${this.pendingCount})`;
      this.item.backgroundColor = undefined;
      this.item.tooltip = `${this.pendingCount} action(s) pending decision. Run ProofFlow: Approve Gate & Execute to continue.`;
      return;
    }

    this.item.text = "$(shield) ProofFlow";
    this.item.backgroundColor = undefined;
    this.item.tooltip = "ProofFlow is connected via MCP";
  }

  dispose(): void {
    this.item.dispose();
  }
}

function mcpStateLabel(state: ProofFlowMcpState): string {
  switch (state) {
    case "idle":
      return "idle";
    case "starting":
      return "starting";
    case "ready":
      return "ready";
    case "restarting":
      return "restarting";
    case "failed":
      return "failed";
  }
}
