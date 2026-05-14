import path from "node:path";
import * as vscode from "vscode";
import { ProofFlowClient } from "./api/client";
import type {
  CasePacket,
  CasePacketClaim,
  CaseResponse,
  RiskLevel,
} from "./types";

type DecorationSeverity = Extract<RiskLevel, "info" | "low" | "medium" | "high">;

export interface ClaimDecoration {
  filePath: string;
  startLine: number;
  endLine: number;
  severity: DecorationSeverity;
  message: string;
}

interface DecorationRefreshClient {
  listCases(): Promise<CaseResponse[]>;
  getCasePacket(caseId: string): Promise<CasePacket>;
}

export class InlineAuditDecorations {
  private client: DecorationRefreshClient;
  private output: vscode.OutputChannel | undefined;
  private decorationTypes: Record<DecorationSeverity, vscode.TextEditorDecorationType>;

  constructor(client: ProofFlowClient, output?: vscode.OutputChannel) {
    this.client = client;
    this.output = output;
    this.decorationTypes = {
      high: createDecorationType("editorError.foreground"),
      medium: createDecorationType("editorWarning.foreground"),
      low: createDecorationType("editorInfo.foreground"),
      info: createDecorationType("editorInfo.foreground"),
    };
  }

  async refresh(cases?: CaseResponse[]): Promise<void> {
    try {
      const caseList = cases ?? (await this.client.listCases());
      const packets = await Promise.all(
        caseList.map((c) => this.client.getCasePacket(c.id).catch(() => undefined))
      );
      const decorations = packets.flatMap((packet) =>
        packet ? buildClaimDecorations(packet, vscode.workspace.workspaceFolders) : []
      );
      this.applyDecorations(decorations);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      this.output?.appendLine(`[${new Date().toISOString()}] inline decorations failed: ${msg}`);
    }
  }

  dispose(): void {
    for (const decorationType of Object.values(this.decorationTypes)) {
      decorationType.dispose();
    }
  }

  private applyDecorations(decorations: ClaimDecoration[]): void {
    const editors = vscode.window.visibleTextEditors || [];
    for (const editor of editors) {
      for (const severity of Object.keys(this.decorationTypes) as DecorationSeverity[]) {
        const options = decorations
          .filter(
            (decoration) =>
              decoration.severity === severity &&
              sameFilePath(decoration.filePath, editor.document.uri.fsPath)
          )
          .map((decoration) => ({
            range: new vscode.Range(
              decoration.startLine - 1,
              0,
              decoration.endLine - 1,
              0
            ),
            hoverMessage: decoration.message,
          }));
        editor.setDecorations(this.decorationTypes[severity], options);
      }
    }
  }
}

export function buildClaimDecorations(
  packet: CasePacket,
  workspaceFolders: readonly vscode.WorkspaceFolder[] | undefined
): ClaimDecoration[] {
  const roots = packetRoots(packet, workspaceFolders);
  const decorations: ClaimDecoration[] = [];

  for (const claim of packet.claims || []) {
    for (const evidence of claim.evidence || []) {
      const location = evidence.source_location;
      if (!location || location.start_line < 1 || location.end_line < location.start_line) {
        continue;
      }

      const filePath = resolveSourcePath(location.path, roots);
      if (!filePath) {
        continue;
      }

      decorations.push({
        filePath,
        startLine: location.start_line,
        endLine: location.end_line,
        severity: normalizeSeverity(claim.severity),
        message: decorationMessage(claim, evidence.source_ref),
      });
    }
  }

  return decorations;
}

function createDecorationType(colorId: string): vscode.TextEditorDecorationType {
  return vscode.window.createTextEditorDecorationType({
    isWholeLine: true,
    borderWidth: "0 0 0 3px",
    borderStyle: "solid",
    borderColor: new vscode.ThemeColor(colorId),
    overviewRulerColor: new vscode.ThemeColor(colorId),
    overviewRulerLane: vscode.OverviewRulerLane.Right,
  });
}

function packetRoots(
  packet: CasePacket,
  workspaceFolders: readonly vscode.WorkspaceFolder[] | undefined
): string[] {
  const roots: string[] = [];
  const repoPath = packet.case?.metadata?.repo_path;
  if (typeof repoPath === "string" && repoPath) {
    roots.push(repoPath);
  }
  for (const folder of workspaceFolders || []) {
    roots.push(folder.uri.fsPath);
  }
  return roots;
}

function resolveSourcePath(sourcePath: string, roots: string[]): string | undefined {
  if (!sourcePath) {
    return undefined;
  }
  if (isAbsoluteSourcePath(sourcePath)) {
    return path.normalize(sourcePath);
  }
  const root = roots[0];
  if (!root) {
    return undefined;
  }
  return path.resolve(root, sourcePath);
}

function isAbsoluteSourcePath(sourcePath: string): boolean {
  return (
    path.isAbsolute(sourcePath) ||
    path.posix.isAbsolute(sourcePath) ||
    /^[A-Za-z]:[\\/]/.test(sourcePath) ||
    sourcePath.startsWith("\\\\")
  );
}

function normalizeSeverity(severity: string): DecorationSeverity {
  if (severity === "high" || severity === "medium" || severity === "low") {
    return severity;
  }
  return "info";
}

function decorationMessage(claim: CasePacketClaim, sourceRef?: string | null): string {
  const source = sourceRef ? `\n\nSource: ${sourceRef}` : "";
  return `ProofFlow ${claim.severity} claim: ${claim.claim_text}${source}`;
}

function sameFilePath(left: string, right: string): boolean {
  const normalizedLeft = path.normalize(left);
  const normalizedRight = path.normalize(right);
  if (process.platform === "win32") {
    return normalizedLeft.toLowerCase() === normalizedRight.toLowerCase();
  }
  return normalizedLeft === normalizedRight;
}
