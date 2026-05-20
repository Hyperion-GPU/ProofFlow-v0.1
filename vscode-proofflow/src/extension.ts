import * as vscode from "vscode";
import { ProofFlowClient } from "./api/client";
import { McpClient, type McpClientConfig } from "./mcp/client";
import { StatusBar } from "./statusBar";
import { Poller } from "./polling";
import { CasesTreeProvider } from "./views/casesTreeProvider";
import { LedgerTreeProvider } from "./views/ledgerTreeProvider";
import { LedgerStore } from "./store/ledgerStore";
import { reviewChanges } from "./commands/reviewChanges";
import { scanFolder } from "./commands/scanFolder";
import { approveAction } from "./commands/approveAction";
import {
  startWorkContract,
  recordEvent,
  recordAlgorithmDecision,
  recordCostBudget,
  captureSnapshot,
  recordEvidence,
  recordClaim,
  evaluateContract,
  finishWorkLedger,
} from "./commands/ledger";
import { InlineAuditDecorations } from "./inlineDecorations";
import type { LedgerCaseNode } from "./views/ledgerTreeProvider";
import { CaseDetailPanelManager } from "./webviews/caseDetail";

let poller: Poller | undefined;
let mcpClient: McpClient | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel("ProofFlow");
  output.appendLine(`[${new Date().toISOString()}] ProofFlow extension activated`);

  const statusBar = new StatusBar();
  mcpClient = new McpClient(readMcpConfig(), {
    onStateChange: (state, detail) => {
      statusBar.setMcpState(state, detail);
      output.appendLine(
        `[${new Date().toISOString()}] mcp state -> ${state}${detail ? `: ${detail}` : ""}`
      );
    },
    onLog: (line) =>
      output.appendLine(`[${new Date().toISOString()}] ${line}`),
  });

  const client = new ProofFlowClient(mcpClient, output);
  const store = new LedgerStore(mcpClient);
  const treeProvider = new CasesTreeProvider(client, output);
  const ledgerProvider = new LedgerTreeProvider(store);
  const inlineDecorations = new InlineAuditDecorations(client, output);

  const treeView = vscode.window.createTreeView("proofflow.casesView", {
    treeDataProvider: treeProvider,
    showCollapseAll: true,
  });
  const ledgerView = vscode.window.createTreeView("proofflow.ledgerView", {
    treeDataProvider: ledgerProvider,
    showCollapseAll: true,
  });

  const ledgerCtx = { client: mcpClient, store };
  const caseDetailManager = new CaseDetailPanelManager({
    client: mcpClient,
    store,
    extensionUri: context.extensionUri,
  });
  const refreshAll = () => {
    treeProvider.refresh();
    ledgerProvider.refresh();
    void store.refresh();
    void inlineDecorations.refresh();
  };

  context.subscriptions.push(
    output,
    treeView,
    ledgerView,
    statusBar,
    inlineDecorations,
    store,
    ledgerProvider,
    caseDetailManager,
    { dispose: () => void mcpClient?.dispose() },
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
      approveAction(client, {
        client: mcpClient!,
        store,
        extensionUri: context.extensionUri,
      })
    ),
    vscode.commands.registerCommand("proofflow.refresh", refreshAll),
    vscode.commands.registerCommand("proofflow.showLogs", () =>
      output.show(true)
    ),
    vscode.commands.registerCommand("proofflow.startWorkContract", () =>
      startWorkContract(ledgerCtx)
    ),
    vscode.commands.registerCommand("proofflow.recordEvent", () =>
      recordEvent(ledgerCtx)
    ),
    vscode.commands.registerCommand("proofflow.recordAlgorithmDecision", () =>
      recordAlgorithmDecision(ledgerCtx)
    ),
    vscode.commands.registerCommand("proofflow.recordCostBudget", () =>
      recordCostBudget(ledgerCtx)
    ),
    vscode.commands.registerCommand("proofflow.captureSnapshot", () =>
      captureSnapshot(ledgerCtx)
    ),
    vscode.commands.registerCommand(
      "proofflow.recordEvidence",
      (node?: LedgerCaseNode | { caseId?: string; section?: string }) =>
        recordEvidence(ledgerCtx, resolveCaseId(node))
    ),
    vscode.commands.registerCommand(
      "proofflow.recordClaim",
      (node?: LedgerCaseNode | { caseId?: string; section?: string }) =>
        recordClaim(ledgerCtx, resolveCaseId(node))
    ),
    vscode.commands.registerCommand(
      "proofflow.evaluateContract",
      (node?: LedgerCaseNode) => evaluateContract(ledgerCtx, node?.caseRef?.id)
    ),
    vscode.commands.registerCommand(
      "proofflow.finishWorkLedger",
      (node?: LedgerCaseNode) => finishWorkLedger(ledgerCtx, node?.caseRef?.id)
    ),
    vscode.commands.registerCommand(
      "proofflow.openCaseDetail",
      (caseIdOrNode?: string | LedgerCaseNode) => {
        const caseId =
          typeof caseIdOrNode === "string"
            ? caseIdOrNode
            : caseIdOrNode?.caseRef?.id;
        if (!caseId) {
          vscode.window.showWarningMessage(
            "ProofFlow: Select a case from the tree to open its detail view."
          );
          return;
        }
        caseDetailManager.open(caseId);
      }
    ),
    vscode.commands.registerCommand(
      "proofflow.exportPacket",
      (node?: LedgerCaseNode) => {
        const caseId = node?.caseRef?.id;
        if (!caseId) {
          vscode.window.showWarningMessage(
            "ProofFlow: Right-click a ledger case to export."
          );
          return;
        }
        caseDetailManager.open(caseId);
        // Trigger the same flow the panel button uses, so users land in the
        // detail view and immediately get the markdown preview.
        void vscode.commands.executeCommand("proofflow.exportPacketFromPanel", caseId);
      }
    ),
    vscode.commands.registerCommand(
      "proofflow.exportPacketFromPanel",
      async (caseId: string) => {
        try {
          const result = await mcpClient!.exportPacket(caseId);
          const folders = vscode.workspace.workspaceFolders;
          if (!folders || folders.length === 0) {
            vscode.window.showErrorMessage(
              "ProofFlow: Open a workspace folder before exporting a packet."
            );
            return;
          }
          const root = folders[0].uri.fsPath;
          const dir = vscode.Uri.file(`${root}/.proofflow/exports`);
          await vscode.workspace.fs.createDirectory(dir);
          const ts = new Date().toISOString().replace(/[:.]/g, "-");
          const file = vscode.Uri.joinPath(
            dir,
            `${caseId.slice(0, 8)}-${ts}.md`
          );
          await vscode.workspace.fs.writeFile(
            file,
            Buffer.from(result.content, "utf8")
          );
          await vscode.commands.executeCommand("markdown.showPreview", file);
          vscode.window.showInformationMessage(
            `ProofFlow: Packet saved to ${vscode.workspace.asRelativePath(file)}`
          );
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
        }
      }
    )
  );

  const autoRefresh = vscode.workspace
    .getConfiguration("proofflow")
    .get<boolean>("autoRefresh", true);

  if (autoRefresh) {
    poller = new Poller(client, statusBar, treeProvider, inlineDecorations, store);
    poller.start();
  }

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("proofflow.autoRefresh")) {
        const enabled = vscode.workspace
          .getConfiguration("proofflow")
          .get<boolean>("autoRefresh", true);
        if (enabled && !poller) {
          poller = new Poller(
            client,
            statusBar,
            treeProvider,
            inlineDecorations,
            store
          );
          poller.start();
        } else if (!enabled && poller) {
          poller.stop();
          poller = undefined;
        }
      }
      if (
        e.affectsConfiguration("proofflow.backendUrl") ||
        e.affectsConfiguration("proofflow.apiKey")
      ) {
        mcpClient?.applyConfig(readMcpConfig());
      }
    })
  );
}

export function deactivate(): void {
  if (poller) {
    poller.stop();
    poller = undefined;
  }
  void mcpClient?.dispose();
  mcpClient = undefined;
}

function readMcpConfig(): McpClientConfig {
  const config = vscode.workspace.getConfiguration("proofflow");
  return {
    pythonPath: "",
    backendUrl: config.get<string>("backendUrl", "http://127.0.0.1:8787"),
    apiKey: config.get<string>("apiKey", ""),
    extraEnv: {},
  };
}

function resolveCaseId(
  node: LedgerCaseNode | { caseId?: string; section?: string } | undefined
): string | undefined {
  if (!node) {
    return undefined;
  }
  if ("caseRef" in node) {
    return node.caseRef.id;
  }
  if ("caseId" in node) {
    return node.caseId;
  }
  return undefined;
}
