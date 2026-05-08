import * as vscode from "vscode";
import { ProofFlowClient } from "../api/client";
import { CaseItem, SectionItem, ActionItem, ClaimItem } from "./treeItems";
import type {
  CaseResponse,
  ActionResponse,
  CasePacketClaim,
} from "../types";

type TreeElement = CaseItem | SectionItem | ActionItem | ClaimItem;

export class CasesTreeProvider
  implements vscode.TreeDataProvider<TreeElement>
{
  private _onDidChangeTreeData = new vscode.EventEmitter<
    TreeElement | undefined
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private client: ProofFlowClient;
  private output: vscode.OutputChannel | undefined;

  constructor(client: ProofFlowClient, output?: vscode.OutputChannel) {
    this.client = client;
    this.output = output;
  }

  private log(msg: string): void {
    if (this.output) {
      const ts = new Date().toISOString();
      this.output.appendLine(`[${ts}] tree: ${msg}`);
    }
  }

  refresh(): void {
    this.log("refresh()");
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: TreeElement): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: TreeElement): Promise<TreeElement[]> {
    if (!element) {
      return this.getCases();
    }
    if (element instanceof CaseItem) {
      return [
        new SectionItem("Actions", element.caseData.id, "actions"),
        new SectionItem("Claims", element.caseData.id, "claims"),
      ];
    }
    if (element instanceof SectionItem) {
      if (element.section === "actions") {
        return this.getActions(element.caseId);
      }
      return this.getClaims(element.caseId);
    }
    return [];
  }

  private async getCases(): Promise<CaseItem[]> {
    try {
      const cases = await this.client.listCases();
      this.log(`getCases -> ${cases.length} item(s)`);
      return cases.map((c) => new CaseItem(c));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      this.log(`getCases failed: ${msg}`);
      return [];
    }
  }

  private async getActions(caseId: string): Promise<ActionItem[]> {
    try {
      const actions = await this.client.listCaseActions(caseId);
      this.log(`getActions(${caseId}) -> ${actions.length} item(s)`);
      return actions.map((a) => new ActionItem(a));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      this.log(`getActions failed: ${msg}`);
      return [];
    }
  }

  private async getClaims(caseId: string): Promise<ClaimItem[]> {
    try {
      const packet = await this.client.getCasePacket(caseId);
      const claims = packet.claims || [];
      this.log(`getClaims(${caseId}) -> ${claims.length} item(s)`);
      return claims.map((c) => new ClaimItem(c));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      this.log(`getClaims failed: ${msg}`);
      return [];
    }
  }
}
