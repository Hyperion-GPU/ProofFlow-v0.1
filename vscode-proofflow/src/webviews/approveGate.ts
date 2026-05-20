import * as vscode from "vscode";
import type { McpClient } from "../mcp/client";
import type { LedgerStore } from "../store/ledgerStore";
import type {
  McpAction,
  McpCasePacket,
  McpClaim,
} from "../mcp/types";

interface ApproveGateContext {
  client: McpClient;
  store: LedgerStore;
  extensionUri: vscode.Uri;
}

const VIEW_TYPE = "proofflow.approveGate";

export class ApproveGatePanel implements vscode.Disposable {
  private static current: ApproveGatePanel | undefined;
  private panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];
  private actionId: string;
  private caseId: string;

  static async show(
    ctx: ApproveGateContext,
    actionId: string,
    caseId: string
  ): Promise<void> {
    if (ApproveGatePanel.current) {
      ApproveGatePanel.current.update(actionId, caseId);
      ApproveGatePanel.current.panel.reveal();
      return;
    }
    ApproveGatePanel.current = new ApproveGatePanel(ctx, actionId, caseId);
  }

  private constructor(
    private ctx: ApproveGateContext,
    actionId: string,
    caseId: string
  ) {
    this.actionId = actionId;
    this.caseId = caseId;
    this.panel = vscode.window.createWebviewPanel(
      VIEW_TYPE,
      "ProofFlow: Approve Gate",
      vscode.ViewColumn.Active,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(ctx.extensionUri, "media")],
      }
    );
    this.panel.webview.html = this.renderHtml();

    this.disposables.push(
      this.panel.webview.onDidReceiveMessage((m) => this.handleMessage(m)),
      this.panel.onDidDispose(() => this.dispose()),
      ctx.store.onDidChange((event) => {
        if (event.kind === "packet" && event.caseId === this.caseId) {
          this.refresh();
        }
        if (event.kind === "cases") {
          this.refresh();
        }
      })
    );

    void this.ctx.store.refreshPacket(this.caseId);
    this.refresh();
  }

  private update(actionId: string, caseId: string): void {
    this.actionId = actionId;
    this.caseId = caseId;
    void this.ctx.store.refreshPacket(caseId);
    this.refresh();
  }

  private refresh(): void {
    const packet = this.ctx.store.getPacket(this.caseId);
    if (!packet) {
      void this.panel.webview.postMessage({ type: "loading" });
      return;
    }
    const action = (packet.actions as Array<McpAction | { id: string; title: string; status: string }>)
      .find((a) => a.id === this.actionId);
    void this.panel.webview.postMessage({
      type: "render",
      action,
      packet,
      meta: this.gatherActionMeta(packet),
    });
  }

  private gatherActionMeta(_packet: McpCasePacket): {
    risk_claims: McpClaim[];
  } {
    // We surface every medium/high-severity claim for the case so the reviewer
    // sees the full risk context before approving.
    const packet = this.ctx.store.getPacket(this.caseId);
    if (!packet) {
      return { risk_claims: [] };
    }
    const risk_claims = packet.claims.filter(
      (c) => c.severity === "high" || c.severity === "medium"
    );
    return { risk_claims };
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
      case "approve":
        await this.approveAndExecute();
        break;
      case "reject":
        await this.reject();
        break;
      case "openSource":
        await this.openSource(message.payload);
        break;
      case "explain":
        await this.explain(message.payload);
        break;
    }
  }

  private async approveAndExecute(): Promise<void> {
    try {
      await this.ctx.client.approveExecute(this.actionId);
      vscode.window.showInformationMessage(
        "ProofFlow: Approve Gate approved and action executed."
      );
      await this.ctx.store.refresh({ includePackets: true });
      this.panel.dispose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
    }
  }

  private async reject(): Promise<void> {
    const rationale = await vscode.window.showInputBox({
      title: "Rejection rationale",
      ignoreFocusOut: true,
    });
    if (!rationale) {
      return;
    }
    try {
      await this.ctx.client.decide(this.caseId, {
        title: `Reject action ${this.actionId}`,
        status: "rejected",
        rationale,
        result: "rejected",
        metadata: {
          decision_kind: "policy_gate_owner_decision",
          action_id: this.actionId,
          source: "vscode-proofflow",
        },
      });
      await this.ctx.store.refresh({ includePackets: true });
      vscode.window.showInformationMessage(
        "ProofFlow: Action rejected. The agent will need to revise."
      );
      this.panel.dispose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
    }
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
    if (folders && folders.length > 0) {
      const root = folders[0].uri.fsPath;
      if (!/^[A-Za-z]:[\\/]/.test(relPath) && !relPath.startsWith("/")) {
        absPath = `${root}/${relPath}`;
      }
    }
    try {
      const doc = await vscode.workspace.openTextDocument(absPath);
      const editor = await vscode.window.showTextDocument(doc, {
        viewColumn: vscode.ViewColumn.Beside,
      });
      if (startLine && startLine > 0) {
        const range = new vscode.Range(startLine - 1, 0, startLine - 1, 0);
        editor.selection = new vscode.Selection(range.start, range.start);
        editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
      }
    } catch {
      vscode.window.showWarningMessage(
        `ProofFlow: Could not open ${relPath}.`
      );
    }
  }

  private async explain(payload: unknown): Promise<void> {
    if (!payload || typeof payload !== "object") {
      return;
    }
    const { claimId } = payload as { claimId?: string };
    if (!claimId) {
      return;
    }
    const packet = this.ctx.store.getPacket(this.caseId);
    const claim = packet?.claims.find((c) => c.id === claimId);
    if (!claim) {
      vscode.window.showErrorMessage(
        "ProofFlow: Claim no longer present in this case."
      );
      return;
    }
    const evaluations = (packet?.runs || []).filter((r) =>
      (r.run_type || "").toLowerCase().includes("evaluat")
    );
    const lastRun = evaluations[evaluations.length - 1];
    if (!lastRun) {
      vscode.window.showWarningMessage(
        "ProofFlow: Run Evaluate Contract first to attach an explanation to the latest evaluation."
      );
      return;
    }
    const disposition = await vscode.window.showQuickPick(
      [
        { label: "accept", description: "Acknowledge this claim's risk" },
        { label: "mitigate", description: "Mitigation evidence is attached" },
        { label: "reject", description: "Disagree with the claim" },
      ],
      { title: `Disposition for ${claim.claim_text.slice(0, 50)}` }
    );
    if (!disposition) {
      return;
    }
    const rationale = await vscode.window.showInputBox({
      title: "Explanation rationale",
      ignoreFocusOut: true,
    });
    if (!rationale) {
      return;
    }
    try {
      await this.ctx.client.ledger.explainRiskHint({
        caseId: this.caseId,
        evaluationRunId: lastRun.id,
        hintCode: claim.id,
        disposition: disposition.label,
        rationale,
        evidenceIds: claim.evidence.map((e) => e.id),
      });
      await this.ctx.store.refreshPacket(this.caseId);
      vscode.window.showInformationMessage(
        "ProofFlow: Explanation recorded against the latest evaluation."
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
      vscode.Uri.joinPath(mediaRoot, "approveGate.css")
    );
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(mediaRoot, "approveGate.js")
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
  <title>ProofFlow Approve Gate</title>
</head>
<body>
  <header class="gate-header">
    <h1 id="action-title">Loading…</h1>
    <div id="action-meta" class="meta-row"></div>
  </header>
  <main class="gate-main">
    <section class="preview-pane">
      <h2>Action preview</h2>
      <div id="preview-body" class="preview-body">No preview.</div>
      <button id="open-inline" class="link-like hidden">Open inline view</button>
    </section>
    <section class="risk-pane">
      <h2>Risk claims</h2>
      <ul id="risk-list" class="risk-list"></ul>
    </section>
  </main>
  <footer class="gate-footer">
    <button id="reject" class="secondary">Reject</button>
    <button id="approve" class="primary">Approve &amp; Execute</button>
  </footer>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }

  dispose(): void {
    if (ApproveGatePanel.current === this) {
      ApproveGatePanel.current = undefined;
    }
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
