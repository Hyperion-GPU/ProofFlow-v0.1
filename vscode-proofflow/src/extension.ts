import * as vscode from "vscode";
import { ProofFlowClient } from "./api/client";
import { StatusBar } from "./statusBar";
import { Poller } from "./polling";
import { CasesTreeProvider } from "./views/casesTreeProvider";
import { reviewChanges } from "./commands/reviewChanges";
import { scanFolder } from "./commands/scanFolder";
import { approveAction } from "./commands/approveAction";
import { InlineAuditDecorations } from "./inlineDecorations";

let poller: Poller | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel("ProofFlow");
  output.appendLine(`[${new Date().toISOString()}] ProofFlow extension activated`);

  const client = new ProofFlowClient(output);
  const statusBar = new StatusBar();
  const treeProvider = new CasesTreeProvider(client, output);
  const inlineDecorations = new InlineAuditDecorations(client, output);

  const treeView = vscode.window.createTreeView("proofflow.casesView", {
    treeDataProvider: treeProvider,
    showCollapseAll: true,
  });

  context.subscriptions.push(
    output,
    treeView,
    statusBar,
    inlineDecorations,
    vscode.window.onDidChangeVisibleTextEditors(() =>
      void inlineDecorations.refresh()
    ),
    vscode.commands.registerCommand("proofflow.reviewLastChanges", (uri?: vscode.Uri) =>
      reviewChanges(client, uri)
    ),
    vscode.commands.registerCommand("proofflow.scanFolder", (uri?: vscode.Uri) =>
      scanFolder(client, uri)
    ),
    vscode.commands.registerCommand("proofflow.approveAction", () =>
      approveAction(client)
    ),
    vscode.commands.registerCommand("proofflow.refresh", () => {
      treeProvider.refresh();
      void inlineDecorations.refresh();
    }),
    vscode.commands.registerCommand("proofflow.showLogs", () =>
      output.show(true)
    )
  );

  const autoRefresh = vscode.workspace
    .getConfiguration("proofflow")
    .get<boolean>("autoRefresh", true);

  if (autoRefresh) {
    poller = new Poller(client, statusBar, treeProvider, inlineDecorations);
    poller.start();
  }

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("proofflow.autoRefresh")) {
        const enabled = vscode.workspace
          .getConfiguration("proofflow")
          .get<boolean>("autoRefresh", true);
        if (enabled && !poller) {
          poller = new Poller(client, statusBar, treeProvider, inlineDecorations);
          poller.start();
        } else if (!enabled && poller) {
          poller.stop();
          poller = undefined;
        }
      }
    })
  );
}

export function deactivate(): void {
  if (poller) {
    poller.stop();
    poller = undefined;
  }
}
