import { ProofFlowClient } from "./api/client";
import { StatusBar } from "./statusBar";
import { CasesTreeProvider } from "./views/casesTreeProvider";
import * as vscode from "vscode";
import type { CaseResponse } from "./types";
import type { LedgerStore } from "./store/ledgerStore";

const APPROVE_GATE_LABEL = "Approve Gate & Execute";

interface InlineDecorations {
  refresh(cases?: CaseResponse[]): Promise<void>;
}

export class Poller {
  private timer: ReturnType<typeof setInterval> | undefined;
  private notifiedPendingActionIds = new Set<string>();
  private client: ProofFlowClient;
  private statusBar: StatusBar;
  private treeProvider: CasesTreeProvider;
  private inlineDecorations: InlineDecorations | undefined;
  private store: LedgerStore | undefined;

  constructor(
    client: ProofFlowClient,
    statusBar: StatusBar,
    treeProvider: CasesTreeProvider,
    inlineDecorations?: InlineDecorations,
    store?: LedgerStore
  ) {
    this.client = client;
    this.statusBar = statusBar;
    this.treeProvider = treeProvider;
    this.inlineDecorations = inlineDecorations;
    this.store = store;
  }

  start(): void {
    void this.pollNow();
    this.timer = setInterval(() => void this.pollNow(), 10_000);
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  async pollNow(): Promise<void> {
    try {
      await this.client.checkHealth();
      this.statusBar.setOnline(true);

      const cases = await this.client.listCases();
      const pendingActionIds: string[] = [];
      for (const c of cases) {
        const actions = await this.client.listCaseActions(c.id);
        for (const action of actions) {
          if (
            action.status === "pending_decision" ||
            action.status === "pending"
          ) {
            pendingActionIds.push(action.id);
          }
        }
      }
      this.statusBar.setPendingCount(pendingActionIds.length);
      await this.notifyPendingActions(pendingActionIds);
      this.treeProvider.refresh();
      await this.inlineDecorations?.refresh(cases).catch(() => undefined);
      if (this.store) {
        await this.store.refresh().catch(() => undefined);
      }
    } catch {
      this.statusBar.setOnline(false);
    }
  }

  private async notifyPendingActions(actionIds: string[]): Promise<void> {
    const pendingActionIds = new Set(actionIds);
    if (pendingActionIds.size === 0) {
      this.notifiedPendingActionIds.clear();
      return;
    }

    const hasNewPendingAction = [...pendingActionIds].some(
      (actionId) => !this.notifiedPendingActionIds.has(actionId)
    );
    if (!hasNewPendingAction) {
      return;
    }

    this.notifiedPendingActionIds = pendingActionIds;
    const picked = await vscode.window.showInformationMessage(
      `ProofFlow: ${pendingActionIds.size} action(s) pending decision.`,
      APPROVE_GATE_LABEL
    );
    if (picked === APPROVE_GATE_LABEL) {
      vscode.commands.executeCommand("proofflow.approveAction");
    }
  }
}
