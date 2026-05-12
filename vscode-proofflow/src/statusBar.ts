import * as vscode from "vscode";

export class StatusBar {
  private item: vscode.StatusBarItem;
  private pendingCount = 0;
  private online = false;

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

  private render(): void {
    if (!this.online) {
      this.item.text = "$(shield) ProofFlow: Offline";
      this.item.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.warningBackground"
      );
      this.item.tooltip = "ProofFlow backend is not reachable";
    } else if (this.pendingCount > 0) {
      this.item.text = `$(shield) ProofFlow (${this.pendingCount})`;
      this.item.backgroundColor = undefined;
      this.item.tooltip = `${this.pendingCount} action(s) pending decision. Run ProofFlow: Approve Gate & Execute to continue.`;
    } else {
      this.item.text = "$(shield) ProofFlow";
      this.item.backgroundColor = undefined;
      this.item.tooltip = "ProofFlow is connected";
    }
  }

  dispose(): void {
    this.item.dispose();
  }
}
