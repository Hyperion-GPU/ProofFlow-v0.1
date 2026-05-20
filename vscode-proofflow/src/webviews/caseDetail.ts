import * as vscode from "vscode";
import * as path from "node:path";
import { promises as fs } from "node:fs";
import type { McpClient } from "../mcp/client";
import type { LedgerStore } from "../store/ledgerStore";
import type { McpCasePacket } from "../mcp/types";

interface CaseDetailContext {
  client: McpClient;
  store: LedgerStore;
  extensionUri: vscode.Uri;
}

const VIEW_TYPE = "proofflow.caseDetail";

/**
 * Singleton-per-case manager for Case Detail webviews. Reuses existing panels
 * when the same case is opened twice and patches them via postMessage on
 * store updates instead of re-rendering the whole HTML each time.
 */
export class CaseDetailPanelManager implements vscode.Disposable {
  private panels = new Map<string, CaseDetailPanel>();
  private storeSub: vscode.Disposable;

  constructor(private ctx: CaseDetailContext) {
    this.storeSub = ctx.store.onDidChange((event) => {
      if (event.kind === "packet") {
        this.panels.get(event.caseId)?.refresh();
      } else if (event.kind === "cases") {
        for (const panel of this.panels.values()) {
          panel.refresh();
        }
      }
    });
  }

  open(caseId: string): void {
    const existing = this.panels.get(caseId);
    if (existing) {
      existing.reveal();
      return;
    }
    const panel = new CaseDetailPanel(this.ctx, caseId, () => {
      this.panels.delete(caseId);
    });
    this.panels.set(caseId, panel);
    panel.reveal();
    void this.ctx.store.refreshPacket(caseId);
  }

  dispose(): void {
    this.storeSub.dispose();
    for (const panel of this.panels.values()) {
      panel.dispose();
    }
    this.panels.clear();
  }
}

class CaseDetailPanel implements vscode.Disposable {
  private panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];

  constructor(
    private ctx: CaseDetailContext,
    private caseId: string,
    onDispose: () => void
  ) {
    const cached = ctx.store.getCase(caseId);
    const title = cached?.title || `Case ${caseId.slice(0, 8)}`;

    this.panel = vscode.window.createWebviewPanel(
      VIEW_TYPE,
      `ProofFlow: ${title}`,
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(ctx.extensionUri, "media")],
      }
    );

    this.panel.webview.html = this.renderHtml();

    this.disposables.push(
      this.panel.webview.onDidReceiveMessage((msg) => this.handleMessage(msg)),
      this.panel.onDidDispose(() => {
        this.dispose();
        onDispose();
      })
    );

    this.refresh();
  }

  reveal(): void {
    this.panel.reveal(this.panel.viewColumn);
  }

  refresh(): void {
    const packet = this.ctx.store.getPacket(this.caseId);
    if (!packet) {
      void this.panel.webview.postMessage({ type: "loading" });
      return;
    }
    void this.panel.webview.postMessage({
      type: "packet",
      packet,
    });
    const title = packet.case.title || `Case ${this.caseId.slice(0, 8)}`;
    this.panel.title = `ProofFlow: ${title}`;
  }

  private async handleMessage(msg: unknown): Promise<void> {
    if (!msg || typeof msg !== "object") {
      return;
    }
    const message = msg as { type?: string; payload?: unknown };
    switch (message.type) {
      case "ready":
        this.refresh();
        break;
      case "exportPacket":
        await this.exportPacket();
        break;
      case "openSource":
        await this.openSource(message.payload);
        break;
      case "explainRiskHint":
        await this.handleExplainRiskHint(message.payload);
        break;
    }
  }

  private async exportPacket(): Promise<void> {
    try {
      const result = await this.ctx.client.exportPacket(this.caseId);
      const dest = await this.savePacketToDisk(result.content);
      if (dest) {
        await vscode.commands.executeCommand("markdown.showPreview", dest);
        vscode.window.showInformationMessage(
          `ProofFlow: Packet saved to ${vscode.workspace.asRelativePath(dest)}`
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
    }
  }

  private async savePacketToDisk(content: string): Promise<vscode.Uri | undefined> {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
      vscode.window.showErrorMessage(
        "ProofFlow: Open a workspace folder before exporting a packet."
      );
      return undefined;
    }
    const root = folders[0].uri.fsPath;
    const dir = path.join(root, ".proofflow", "exports");
    await fs.mkdir(dir, { recursive: true });
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    const file = path.join(dir, `${this.caseId.slice(0, 8)}-${ts}.md`);
    await fs.writeFile(file, content, "utf8");
    return vscode.Uri.file(file);
  }

  private async openSource(payload: unknown): Promise<void> {
    if (!payload || typeof payload !== "object") {
      return;
    }
    const { path: relPath, startLine } = payload as {
      path?: string;
      startLine?: number;
    };
    if (!relPath) {
      return;
    }
    const folders = vscode.workspace.workspaceFolders;
    let absPath = relPath;
    if (folders && folders.length > 0 && !path.isAbsolute(relPath)) {
      absPath = path.join(folders[0].uri.fsPath, relPath);
    }
    try {
      const doc = await vscode.workspace.openTextDocument(absPath);
      const editor = await vscode.window.showTextDocument(doc, {
        viewColumn: vscode.ViewColumn.One,
      });
      if (startLine && startLine > 0) {
        const range = new vscode.Range(startLine - 1, 0, startLine - 1, 0);
        editor.selection = new vscode.Selection(range.start, range.start);
        editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
      }
    } catch {
      vscode.window.showWarningMessage(
        `ProofFlow: Could not open ${relPath}. The file may live outside the workspace.`
      );
    }
  }

  private async handleExplainRiskHint(payload: unknown): Promise<void> {
    if (!payload || typeof payload !== "object") {
      return;
    }
    const { hintCode, evaluationRunId } = payload as {
      hintCode?: string;
      evaluationRunId?: string;
    };
    if (!hintCode || !evaluationRunId) {
      vscode.window.showErrorMessage(
        "ProofFlow: Risk hint is missing identifying metadata."
      );
      return;
    }
    const disposition = await vscode.window.showQuickPick(
      [
        { label: "accept", description: "Acknowledge and accept this risk" },
        { label: "mitigate", description: "Mitigation evidence is attached" },
        { label: "reject", description: "Reject this risk hint" },
      ],
      { title: `Disposition for ${hintCode}` }
    );
    if (!disposition) {
      return;
    }
    const rationale = await vscode.window.showInputBox({
      title: "Rationale",
      ignoreFocusOut: true,
    });
    if (!rationale) {
      return;
    }
    const packet = this.ctx.store.getPacket(this.caseId);
    const evidenceItems = packet?.claims.flatMap((c) => c.evidence) ?? [];
    const picked = await vscode.window.showQuickPick(
      evidenceItems.map((e) => ({
        label: (e.content || "").split(/\r?\n/)[0]?.slice(0, 80) || e.id,
        description: e.evidence_type,
        detail: e.source_ref ?? undefined,
        id: e.id,
      })),
      {
        title: "Evidence to support the explanation",
        canPickMany: true,
      }
    );
    try {
      await this.ctx.client.ledger.explainRiskHint({
        caseId: this.caseId,
        evaluationRunId,
        hintCode,
        disposition: disposition.label,
        rationale,
        evidenceIds: (picked || []).map((p) => p.id),
      });
      await this.ctx.store.refreshPacket(this.caseId);
      vscode.window.showInformationMessage(
        `ProofFlow: Recorded explanation for ${hintCode}.`
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
    }
  }

  private renderHtml(): string {
    const webview = this.panel.webview;
    const mediaRoot = vscode.Uri.joinPath(this.ctx.extensionUri, "media");
    const styleUri = webview.asWebviewUri(
      vscode.Uri.joinPath(mediaRoot, "caseDetail.css")
    );
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(mediaRoot, "caseDetail.js")
    );
    const nonce = generateNonce();
    const csp = [
      `default-src 'none'`,
      `style-src ${webview.cspSource} 'unsafe-inline'`,
      `script-src 'nonce-${nonce}'`,
      `img-src ${webview.cspSource} data:`,
      `font-src ${webview.cspSource}`,
    ].join("; ");

    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="${csp}" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>ProofFlow Case</title>
</head>
<body>
  <header class="case-header">
    <div>
      <h1 id="case-title">Loading…</h1>
      <div class="meta-row">
        <span id="case-kind" class="badge"></span>
        <span id="case-status" class="badge"></span>
        <span id="case-updated"></span>
      </div>
    </div>
    <button id="export-packet" class="primary">Export Packet</button>
  </header>
  <nav class="tabs" role="tablist">
    <button data-tab="overview" class="tab active" role="tab">Overview</button>
    <button data-tab="evidence" class="tab" role="tab">Evidence &amp; Claims</button>
    <button data-tab="actions" class="tab" role="tab">Actions</button>
    <button data-tab="hints" class="tab" role="tab">Risk Hints</button>
  </nav>
  <main>
    <section data-panel="overview" class="panel active">
      <div id="overview-empty" class="empty">No data yet.</div>
      <article id="overview-contract" class="card hidden">
        <h2>Work contract</h2>
        <dl id="contract-fields"></dl>
      </article>
      <article id="overview-budgets" class="card hidden">
        <h2>Cost budgets</h2>
        <ul id="budget-list"></ul>
      </article>
      <article id="overview-decisions" class="card hidden">
        <h2>Algorithm decisions</h2>
        <ul id="decision-list"></ul>
      </article>
    </section>
    <section data-panel="evidence" class="panel">
      <div class="two-col">
        <div>
          <h2>Evidence</h2>
          <ul id="evidence-list" class="evidence-list"></ul>
        </div>
        <div>
          <h2>Claims</h2>
          <ul id="claim-list" class="claim-list"></ul>
        </div>
      </div>
    </section>
    <section data-panel="actions" class="panel">
      <h2>Actions</h2>
      <ul id="action-list" class="action-list"></ul>
    </section>
    <section data-panel="hints" class="panel">
      <h2>Risk hints</h2>
      <div id="hints-empty" class="empty">No evaluation runs yet.</div>
      <ul id="hint-list"></ul>
    </section>
  </main>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }

  dispose(): void {
    for (const d of this.disposables) {
      d.dispose();
    }
    this.disposables = [];
    this.panel.dispose();
  }
}

function generateNonce(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let out = "";
  for (let i = 0; i < 32; i += 1) {
    out += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return out;
}

export function packetSnapshot(packet: McpCasePacket): {
  evidenceCount: number;
  claimCount: number;
  pendingActionCount: number;
} {
  return {
    evidenceCount: packet.claims.reduce((acc, c) => acc + c.evidence.length, 0),
    claimCount: packet.claims.length,
    pendingActionCount: packet.actions.filter(
      (a) => a.status === "pending_decision"
    ).length,
  };
}
