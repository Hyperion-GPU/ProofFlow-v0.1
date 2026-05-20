import * as vscode from "vscode";
import type { McpClient } from "../mcp/client";
import type { LedgerStore } from "../store/ledgerStore";
import { isLedgerCase } from "../store/ledgerStore";
import type { McpCase, McpRiskLevel } from "../mcp/types";

interface LedgerContext {
  client: McpClient;
  store: LedgerStore;
}

export async function startWorkContract(ctx: LedgerContext): Promise<void> {
  const repoPath = await pickWorkspacePath("Select repo for the work contract");
  if (!repoPath) {
    return;
  }
  const objective = await vscode.window.showInputBox({
    title: "Work contract objective",
    placeHolder: "What is this work meant to achieve?",
    ignoreFocusOut: true,
  });
  if (!objective) {
    return;
  }
  const allowedScope = await collectList("Allowed scope (one per line)");
  const forbiddenActions = await collectList("Forbidden actions (one per line)");
  const doneCriteria = await collectList("Done criteria (one per line)");

  await runWithProgress("ProofFlow: starting work contract", async () => {
    const result = await ctx.client.ledger.startContract({
      objective,
      repoPath,
      allowedScope,
      forbiddenActions,
      doneCriteria,
    });
    await ctx.store.refresh({ includePackets: true });
    if (result.case_id) {
      vscode.window.showInformationMessage(
        `ProofFlow: Work contract started (case ${shortId(result.case_id)}).`
      );
    }
  });
}

export async function recordEvent(ctx: LedgerContext): Promise<void> {
  const target = await pickLedgerCase(ctx, "Select ledger case to record event on");
  if (!target) {
    return;
  }
  const eventType = await vscode.window.showInputBox({
    title: "Event type",
    value: "progress",
    ignoreFocusOut: true,
  });
  if (!eventType) {
    return;
  }
  const summary = await vscode.window.showInputBox({
    title: "Event summary",
    ignoreFocusOut: true,
  });
  if (!summary) {
    return;
  }
  const content = await vscode.window.showInputBox({
    title: "Event content (optional)",
    ignoreFocusOut: true,
  });
  await runWithProgress("ProofFlow: recording event", async () => {
    await ctx.client.ledger.recordEvent({
      caseId: target.id,
      eventType,
      summary,
      content: content ?? "",
    });
    await ctx.store.refreshPacket(target.id);
  });
}

export async function recordAlgorithmDecision(
  ctx: LedgerContext
): Promise<void> {
  const target = await pickLedgerCase(ctx, "Select ledger case");
  if (!target) {
    return;
  }
  const summary = await vscode.window.showInputBox({
    title: "Algorithm decision summary",
    ignoreFocusOut: true,
  });
  if (!summary) {
    return;
  }
  const chosenApproach = await vscode.window.showInputBox({
    title: "Chosen approach",
    ignoreFocusOut: true,
  });
  if (!chosenApproach) {
    return;
  }
  const rationale = await vscode.window.showInputBox({
    title: "Rationale",
    ignoreFocusOut: true,
  });
  if (!rationale) {
    return;
  }
  const alternatives = await collectList("Alternatives considered (one per line)");
  const invariants = await collectList("Invariants (one per line)");

  await runWithProgress("ProofFlow: recording algorithm decision", async () => {
    await ctx.client.ledger.recordAlgorithmDecision({
      caseId: target.id,
      summary,
      chosenApproach,
      rationale,
      alternativesConsidered: alternatives,
      invariants,
    });
    await ctx.store.refreshPacket(target.id);
  });
}

export async function recordCostBudget(ctx: LedgerContext): Promise<void> {
  const target = await pickLedgerCase(ctx, "Select ledger case");
  if (!target) {
    return;
  }
  const summary = await vscode.window.showInputBox({
    title: "Cost budget summary",
    ignoreFocusOut: true,
  });
  if (!summary) {
    return;
  }
  const limits = await collectList("Hard limits in plain language (one per line)");
  const expected = await collectList("Expected expensive operations (one per line)");

  await runWithProgress("ProofFlow: recording cost budget", async () => {
    await ctx.client.ledger.recordCostBudget({
      caseId: target.id,
      summary,
      limits,
      expectedOperations: expected,
    });
    await ctx.store.refreshPacket(target.id);
  });
}

export async function captureSnapshot(ctx: LedgerContext): Promise<void> {
  const target = await pickLedgerCase(ctx, "Select ledger case");
  if (!target) {
    return;
  }
  const repoPath = await pickWorkspacePath("Select repo for the snapshot");
  if (!repoPath) {
    return;
  }
  const phase = (await vscode.window.showQuickPick(
    [
      { label: "start", description: "Initial snapshot before work begins" },
      { label: "checkpoint", description: "Mid-work snapshot" },
      { label: "final", description: "End-of-work snapshot" },
    ],
    { title: "Snapshot phase" }
  )) as { label: "start" | "checkpoint" | "final" } | undefined;
  if (!phase) {
    return;
  }
  await runWithProgress("ProofFlow: capturing snapshot", async () => {
    await ctx.client.ledger.captureSnapshot({
      caseId: target.id,
      repoPath,
      phase: phase.label,
    });
    await ctx.store.refreshPacket(target.id);
  });
}

export async function recordEvidence(
  ctx: LedgerContext,
  caseId?: string
): Promise<void> {
  const target = caseId
    ? ctx.store.getCase(caseId)
    : await pickLedgerCase(ctx, "Select ledger case");
  if (!target) {
    return;
  }
  const evidenceType = await vscode.window.showInputBox({
    title: "Evidence type",
    value: "note",
    ignoreFocusOut: true,
  });
  if (!evidenceType) {
    return;
  }
  const content = await vscode.window.showInputBox({
    title: "Evidence content",
    ignoreFocusOut: true,
  });
  if (!content) {
    return;
  }
  const sourceRef = await vscode.window.showInputBox({
    title: "Source reference (optional, e.g. path:line-line)",
    ignoreFocusOut: true,
  });
  await runWithProgress("ProofFlow: recording evidence", async () => {
    const result = await ctx.client.ledger.recordEvidence({
      caseId: target.id,
      evidenceType,
      content,
      sourceRef: sourceRef || undefined,
    });
    ctx.store.rememberEvidence(target.id, {
      id: result.evidence_id,
      artifact_id: result.artifact_id,
      claim_id: null,
      evidence_type: result.evidence_type,
      content,
      source_ref: sourceRef || null,
      artifact_name: null,
      artifact_path: null,
      source_location: null,
      created_at: result.created_at,
    });
    await ctx.store.refreshPacket(target.id);
  });
}

export async function recordClaim(
  ctx: LedgerContext,
  caseId?: string
): Promise<void> {
  const target = caseId
    ? ctx.store.getCase(caseId)
    : await pickLedgerCase(ctx, "Select ledger case");
  if (!target) {
    return;
  }
  await ctx.store.refreshPacket(target.id);
  const evidenceItems = ctx.store.getAllEvidence(target.id);
  if (evidenceItems.length === 0) {
    vscode.window.showWarningMessage(
      "ProofFlow: Record at least one Evidence before binding a Claim."
    );
    return;
  }
  const picked = await vscode.window.showQuickPick(
    evidenceItems.map((e) => ({
      label: (e.content || "").split(/\r?\n/)[0]?.slice(0, 80) || e.id,
      description: e.evidence_type,
      detail: e.source_ref ?? undefined,
      id: e.id,
      picked: false,
    })),
    {
      title: "Pick evidence to bind",
      canPickMany: true,
    }
  );
  if (!picked || picked.length === 0) {
    return;
  }
  const claimText = await vscode.window.showInputBox({
    title: "Claim text",
    ignoreFocusOut: true,
  });
  if (!claimText) {
    return;
  }
  const severity = (await vscode.window.showQuickPick(
    [
      { label: "info" },
      { label: "low" },
      { label: "medium" },
      { label: "high" },
    ],
    { title: "Claim severity" }
  )) as { label: McpRiskLevel } | undefined;
  await runWithProgress("ProofFlow: recording claim", async () => {
    await ctx.client.ledger.recordClaim({
      caseId: target.id,
      claimText,
      evidenceIds: picked.map((p) => p.id),
      severity: severity?.label ?? "info",
    });
    await ctx.store.refreshPacket(target.id);
  });
}

export async function evaluateContract(
  ctx: LedgerContext,
  caseId?: string
): Promise<void> {
  const target = caseId
    ? ctx.store.getCase(caseId)
    : await pickLedgerCase(ctx, "Select ledger case to evaluate");
  if (!target) {
    return;
  }
  await runWithProgress("ProofFlow: evaluating contract", async () => {
    const result = await ctx.client.ledger.evaluateContract(target.id);
    await ctx.store.refreshPacket(target.id);
    const failed = result.failed ?? [];
    const hints = result.risk_hints ?? [];
    const warnings = result.warnings ?? [];
    const passed = failed.length === 0 && hints.length === 0;
    const headline = passed
      ? `ProofFlow: Contract evaluation PASSED${
          warnings.length ? ` (${warnings.length} warning(s))` : ""
        }.`
      : `ProofFlow: Contract evaluation ${result.status?.toUpperCase() ?? "FAILED"} — ${failed.length} unmet, ${hints.length} risk hint(s)${
          warnings.length ? `, ${warnings.length} warning(s)` : ""
        }.`;
    vscode.window.showInformationMessage(headline);
  });
}

export async function finishWorkLedger(
  ctx: LedgerContext,
  caseId?: string
): Promise<void> {
  const target = caseId
    ? ctx.store.getCase(caseId)
    : await pickLedgerCase(ctx, "Select ledger case to finish");
  if (!target) {
    return;
  }
  const summary = await vscode.window.showInputBox({
    title: "Final summary (optional)",
    ignoreFocusOut: true,
  });
  await runWithProgress("ProofFlow: finishing ledger", async () => {
    await ctx.client.ledger.finish({
      caseId: target.id,
      summary: summary || undefined,
    });
    await ctx.store.refresh({ includePackets: true });
    vscode.window.showInformationMessage(
      `ProofFlow: Ledger ${shortId(target.id)} finished.`
    );
  });
}

async function pickLedgerCase(
  ctx: LedgerContext,
  title: string
): Promise<McpCase | undefined> {
  await ctx.store.refresh();
  const candidates = ctx.store
    .getCases()
    .filter(isLedgerCase)
    .filter((c) => c.status !== "closed");
  if (candidates.length === 0) {
    vscode.window.showWarningMessage(
      "ProofFlow: No active ledger cases. Run 'Start Work Contract' first."
    );
    return undefined;
  }
  const picked = await vscode.window.showQuickPick(
    candidates.map((c) => ({
      label: c.title || c.id,
      description: c.status,
      detail: c.summary ?? undefined,
      caseId: c.id,
    })),
    { title }
  );
  return picked ? candidates.find((c) => c.id === picked.caseId) : undefined;
}

async function pickWorkspacePath(title: string): Promise<string | undefined> {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showErrorMessage("ProofFlow: No workspace folder open.");
    return undefined;
  }
  if (folders.length === 1) {
    return folders[0].uri.fsPath;
  }
  const picked = await vscode.window.showWorkspaceFolderPick({
    placeHolder: title,
  });
  return picked?.uri.fsPath;
}

async function collectList(title: string): Promise<string[]> {
  const raw = await vscode.window.showInputBox({
    title,
    placeHolder: "Optional. Use \\n between entries.",
    ignoreFocusOut: true,
  });
  if (!raw) {
    return [];
  }
  return raw
    .split(/\\n|\r?\n/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

async function runWithProgress(
  title: string,
  task: () => Promise<void>
): Promise<void> {
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title,
      cancellable: false,
    },
    async () => {
      try {
        await task();
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
      }
    }
  );
}

function shortId(id: string): string {
  return id.split("-")[0] ?? id.slice(0, 8);
}
