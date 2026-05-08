import * as vscode from "vscode";
import type {
  CaseResponse,
  ActionResponse,
  CasePacketClaim,
} from "../types";

export class CaseItem extends vscode.TreeItem {
  caseData: CaseResponse;

  constructor(c: CaseResponse) {
    super(c.title || c.id, vscode.TreeItemCollapsibleState.Collapsed);
    this.caseData = c;
    this.description = c.status;
    this.contextValue = "case";

    const color =
      c.status === "open"
        ? new vscode.ThemeColor("charts.green")
        : new vscode.ThemeColor("charts.gray");
    this.iconPath = new vscode.ThemeIcon("folder", color);
  }
}

export class SectionItem extends vscode.TreeItem {
  caseId: string;
  section: "actions" | "claims";

  constructor(
    label: string,
    caseId: string,
    section: "actions" | "claims"
  ) {
    super(label, vscode.TreeItemCollapsibleState.Collapsed);
    this.caseId = caseId;
    this.section = section;
    this.contextValue = "section";
    this.iconPath = new vscode.ThemeIcon(
      section === "actions" ? "play" : "checklist"
    );
  }
}

export class ActionItem extends vscode.TreeItem {
  actionData: ActionResponse;

  constructor(a: ActionResponse) {
    super(a.title || a.id, vscode.TreeItemCollapsibleState.None);
    this.actionData = a;
    this.description = a.status;
    this.contextValue = "action";

    const color =
      a.status === "pending_decision"
        ? new vscode.ThemeColor("charts.orange")
        : a.status === "executed"
          ? new vscode.ThemeColor("charts.green")
          : undefined;
    this.iconPath = new vscode.ThemeIcon("circle-filled", color);
  }
}

export class ClaimItem extends vscode.TreeItem {
  constructor(claim: CasePacketClaim) {
    super(claim.claim_text, vscode.TreeItemCollapsibleState.None);
    this.description = claim.severity;
    this.contextValue = "claim";

    const icon =
      claim.severity === "high"
        ? "warning"
        : claim.severity === "medium"
          ? "info"
          : "pass";
    this.iconPath = new vscode.ThemeIcon(icon);
  }
}
