import * as vscode from "vscode";
import type { LedgerStore, LedgerStoreEvent } from "../store/ledgerStore";
import { isLedgerCase } from "../store/ledgerStore";
import type {
  McpArtifact,
  McpCase,
  McpCasePacket,
  McpClaim,
  McpEvidence,
  McpRun,
} from "../mcp/types";

export type LedgerTreeElement =
  | LedgerCaseNode
  | LedgerSectionNode
  | LedgerLeafNode;

const SECTIONS = [
  { id: "contract", label: "Contract" },
  { id: "algorithm_decisions", label: "Algorithm Decisions" },
  { id: "cost_budgets", label: "Cost Budgets" },
  { id: "snapshots", label: "Snapshots" },
  { id: "evidence", label: "Evidence" },
  { id: "claims", label: "Claims" },
  { id: "evaluations", label: "Evaluations" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

export class LedgerTreeProvider
  implements vscode.TreeDataProvider<LedgerTreeElement>, vscode.Disposable
{
  private emitter = new vscode.EventEmitter<LedgerTreeElement | undefined>();
  readonly onDidChangeTreeData = this.emitter.event;
  private storeSub: vscode.Disposable;

  constructor(private store: LedgerStore) {
    this.storeSub = store.onDidChange((event: LedgerStoreEvent) => {
      this.emitter.fire(undefined);
      void this.fireForEvent(event);
    });
  }

  private async fireForEvent(_event: LedgerStoreEvent): Promise<void> {
    // Coarse-grained refresh keeps the implementation small; the store does
    // the deduping via packetFetches so this is cheap.
    this.emitter.fire(undefined);
  }

  refresh(): void {
    this.emitter.fire(undefined);
  }

  getTreeItem(element: LedgerTreeElement): vscode.TreeItem {
    return element;
  }

  async getChildren(
    element?: LedgerTreeElement
  ): Promise<LedgerTreeElement[]> {
    if (!element) {
      return this.rootCases();
    }
    if (element instanceof LedgerCaseNode) {
      // Trigger a packet fetch in the background; sections render whatever is
      // already cached now, then the store fires another change once data is
      // in.
      void this.store.refreshPacket(element.caseRef.id);
      return SECTIONS.map(
        (s) => new LedgerSectionNode(element.caseRef.id, s.id, s.label)
      );
    }
    if (element instanceof LedgerSectionNode) {
      const packet = this.store.getPacket(element.caseId);
      if (!packet) {
        return [LedgerLeafNode.placeholder("Loading…")];
      }
      return buildSectionChildren(element, packet);
    }
    return [];
  }

  private rootCases(): LedgerTreeElement[] {
    const cases = this.store
      .getCases()
      .filter(isLedgerCase)
      .filter((c) => c.status !== "closed");
    if (cases.length === 0) {
      return [LedgerLeafNode.placeholder("No active ledger cases.")];
    }
    return cases.map((c) => new LedgerCaseNode(c));
  }

  dispose(): void {
    this.storeSub.dispose();
    this.emitter.dispose();
  }
}

export class LedgerCaseNode extends vscode.TreeItem {
  constructor(public readonly caseRef: McpCase) {
    super(caseRef.title || caseRef.id, vscode.TreeItemCollapsibleState.Expanded);
    this.description = caseRef.status;
    this.contextValue = "ledgerCase";
    this.iconPath = new vscode.ThemeIcon(
      "git-commit",
      caseRef.status === "open"
        ? new vscode.ThemeColor("charts.green")
        : new vscode.ThemeColor("charts.gray")
    );
    this.tooltip = formatCaseTooltip(caseRef);
    this.command = {
      command: "proofflow.openCaseDetail",
      title: "Open Case Detail",
      arguments: [caseRef.id],
    };
  }
}

export class LedgerSectionNode extends vscode.TreeItem {
  constructor(
    public readonly caseId: string,
    public readonly section: SectionId,
    label: string
  ) {
    super(label, vscode.TreeItemCollapsibleState.Collapsed);
    this.contextValue = `ledgerSection:${section}`;
    this.iconPath = new vscode.ThemeIcon(sectionIcon(section));
  }
}

export class LedgerLeafNode extends vscode.TreeItem {
  static placeholder(label: string): LedgerLeafNode {
    const node = new LedgerLeafNode(label, "placeholder");
    node.iconPath = new vscode.ThemeIcon("dash");
    return node;
  }

  constructor(label: string, contextValue: string, description?: string) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.contextValue = contextValue;
    if (description) {
      this.description = description;
    }
  }
}

function buildSectionChildren(
  section: LedgerSectionNode,
  packet: McpCasePacket
): LedgerTreeElement[] {
  switch (section.section) {
    case "contract":
      return contractRows(packet);
    case "algorithm_decisions":
      return artifactRows(packet, "algorithm_decision", "rocket");
    case "cost_budgets":
      return artifactRows(packet, "cost_budget", "graph");
    case "snapshots":
      return snapshotRows(packet);
    case "evidence":
      return evidenceRows(packet);
    case "claims":
      return claimRows(packet);
    case "evaluations":
      return evaluationRows(packet);
  }
}

function contractRows(packet: McpCasePacket): LedgerLeafNode[] {
  const metadata = (packet.case.metadata || {}) as Record<string, unknown>;
  const contract = pickContract(metadata);
  if (!contract) {
    return [LedgerLeafNode.placeholder("No contract recorded.")];
  }
  const rows: LedgerLeafNode[] = [];
  pushList(rows, "Objective", contract.objective);
  pushList(rows, "Allowed scope", contract.allowed_scope);
  pushList(rows, "Forbidden actions", contract.forbidden_actions);
  pushList(rows, "Required tests", contract.required_tests);
  pushList(rows, "Done criteria", contract.done_criteria);
  pushList(rows, "Evidence requirements", contract.evidence_requirements);
  if (rows.length === 0) {
    return [LedgerLeafNode.placeholder("Contract is empty.")];
  }
  return rows;
}

function artifactRows(
  packet: McpCasePacket,
  role: string,
  icon: string
): LedgerLeafNode[] {
  const artifacts = packet.artifacts.filter(
    (a) => a.role === role || a.kind === role
  );
  if (artifacts.length === 0) {
    return [LedgerLeafNode.placeholder("None recorded.")];
  }
  return artifacts.map((a) => artifactLeaf(a, icon));
}

function snapshotRows(packet: McpCasePacket): LedgerLeafNode[] {
  const snapshots = packet.runs.filter((r) =>
    r.run_type.toLowerCase().includes("snapshot")
  );
  if (snapshots.length === 0) {
    // Fall back to artifacts tagged as snapshots.
    return artifactRows(packet, "snapshot", "git-pull-request");
  }
  return snapshots.map((r) => runLeaf(r));
}

function evidenceRows(packet: McpCasePacket): LedgerLeafNode[] {
  const evidence = packet.claims.flatMap((c) => c.evidence);
  if (evidence.length === 0) {
    return [LedgerLeafNode.placeholder("No evidence recorded.")];
  }
  return evidence.map((e) => evidenceLeaf(e));
}

function claimRows(packet: McpCasePacket): LedgerLeafNode[] {
  if (packet.claims.length === 0) {
    return [LedgerLeafNode.placeholder("No claims recorded.")];
  }
  return packet.claims.map((c) => claimLeaf(c));
}

function evaluationRows(packet: McpCasePacket): LedgerLeafNode[] {
  const runs = packet.runs.filter((r) =>
    r.run_type.toLowerCase().includes("evaluat")
  );
  if (runs.length === 0) {
    return [LedgerLeafNode.placeholder("Not evaluated yet.")];
  }
  return runs.map((r) => runLeaf(r));
}

function pushList(
  rows: LedgerLeafNode[],
  label: string,
  value: unknown
): void {
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return;
    }
    for (const entry of value) {
      rows.push(
        new LedgerLeafNode(`${label}: ${String(entry)}`, "contractField")
      );
    }
    return;
  }
  if (typeof value === "string" && value) {
    rows.push(new LedgerLeafNode(`${label}: ${value}`, "contractField"));
  }
}

function artifactLeaf(a: McpArtifact, icon: string): LedgerLeafNode {
  const node = new LedgerLeafNode(a.name || a.id, "ledgerArtifact", a.kind);
  node.iconPath = new vscode.ThemeIcon(icon);
  node.tooltip = `${a.kind} (${a.role})\n${a.uri}`;
  return node;
}

function runLeaf(r: McpRun): LedgerLeafNode {
  const node = new LedgerLeafNode(
    r.run_type,
    "ledgerRun",
    `${r.status} • ${formatTime(r.created_at)}`
  );
  node.iconPath = new vscode.ThemeIcon(
    r.status === "passed" ? "pass" : r.status === "failed" ? "error" : "history"
  );
  node.tooltip = `Run ${r.id}\nstatus: ${r.status}`;
  return node;
}

function evidenceLeaf(e: McpEvidence): LedgerLeafNode {
  const summary = (e.content || "").split(/\r?\n/)[0]?.slice(0, 80) || e.id;
  const node = new LedgerLeafNode(summary, "ledgerEvidence", e.evidence_type);
  node.iconPath = new vscode.ThemeIcon("file-binary");
  node.tooltip = e.source_ref || e.content;
  return node;
}

function claimLeaf(c: McpClaim): LedgerLeafNode {
  const node = new LedgerLeafNode(c.claim_text, "ledgerClaim", c.severity);
  const icon =
    c.severity === "high"
      ? "warning"
      : c.severity === "medium"
        ? "info"
        : c.severity === "low"
          ? "circle-outline"
          : "pass";
  node.iconPath = new vscode.ThemeIcon(icon);
  node.tooltip = `${c.severity}: ${c.claim_text}`;
  return node;
}

function pickContract(metadata: Record<string, unknown>): ContractShape | undefined {
  for (const key of ["work_contract", "contract"]) {
    const value = metadata[key];
    if (value && typeof value === "object") {
      return value as ContractShape;
    }
  }
  // Some backends flatten the contract onto case metadata directly.
  if (
    typeof metadata.objective === "string" ||
    Array.isArray(metadata.allowed_scope)
  ) {
    return metadata as ContractShape;
  }
  return undefined;
}

interface ContractShape {
  objective?: string;
  allowed_scope?: string[];
  forbidden_actions?: string[];
  required_tests?: string[];
  done_criteria?: string[];
  evidence_requirements?: string[];
}

function sectionIcon(section: SectionId): string {
  switch (section) {
    case "contract":
      return "law";
    case "algorithm_decisions":
      return "rocket";
    case "cost_budgets":
      return "graph";
    case "snapshots":
      return "git-pull-request";
    case "evidence":
      return "file-binary";
    case "claims":
      return "checklist";
    case "evaluations":
      return "beaker";
  }
}

function formatTime(iso: string): string {
  if (!iso) {
    return "";
  }
  return iso.replace("T", " ").replace(/\..*$/, "");
}

function formatCaseTooltip(c: McpCase): string {
  const parts = [c.title, `Kind: ${c.kind}`, `Status: ${c.status}`];
  if (c.summary) {
    parts.push(`Summary: ${c.summary}`);
  }
  return parts.join("\n");
}
