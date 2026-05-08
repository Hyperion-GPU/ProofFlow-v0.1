import { ProofFlowClient } from "../api/client";
import { StatusBar } from "../statusBar";
import { CasesTreeProvider } from "../views/casesTreeProvider";
import * as vscode from "vscode";

export class Poller {
  private timer: ReturnType<typeof setInterval> | undefined;
  private client: ProofFlowClient;
  private statusBar: StatusBar;
  private treeProvider: CasesTreeProvider;

  constructor(
    client: ProofFlowClient,
    statusBar: StatusBar,
    treeProvider: CasesTreeProvider
  ) {
    this.client = client;
    this.statusBar = statusBar;
    this.treeProvider = treeProvider;
  }

  start(): void {
    this.poll();
    this.timer = setInterval(() => this.poll(), 10_000);
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  private async poll(): Promise<void> {
    try {
      await this.client.checkHealth();
      this.statusBar.setOnline(true);

      const cases = await this.client.listCases();
      let pending = 0;
      for (const c of cases) {
        const actions = await this.client.listCaseActions(c.id);
        pending += actions.filter(
          (a) => a.status === "pending_decision"
        ).length;
      }
      this.statusBar.setPendingCount(pending);
      this.treeProvider.refresh();
    } catch {
      this.statusBar.setOnline(false);
    }
  }
}
