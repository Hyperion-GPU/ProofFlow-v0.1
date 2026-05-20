import * as vscode from "vscode";
import type { McpClient } from "../mcp/client";
import type { McpCase, McpCasePacket, McpEvidence } from "../mcp/types";

/**
 * In-memory cache of ProofFlow case state, normalized by id. Tree views and
 * webviews subscribe to update events instead of fetching independently. The
 * store is intentionally tolerant of MCP errors — a failed packet fetch leaves
 * the previous snapshot in place rather than wiping the UI.
 */
export class LedgerStore implements vscode.Disposable {
  private cases = new Map<string, McpCase>();
  private packets = new Map<string, McpCasePacket>();
  private packetFetches = new Map<string, Promise<McpCasePacket | undefined>>();
  // Locally recorded evidence that has not yet been bound to a claim. The
  // backend's /cases/{id}/packet only returns evidence already attached to a
  // claim, so without this we would never see brand-new evidence rows in the
  // claim picker.
  private pendingEvidence = new Map<string, McpEvidence[]>();
  private emitter = new vscode.EventEmitter<LedgerStoreEvent>();
  readonly onDidChange = this.emitter.event;

  constructor(private mcp: McpClient) {}

  getCases(): McpCase[] {
    return Array.from(this.cases.values()).sort(byUpdatedAtDesc);
  }

  getCase(id: string): McpCase | undefined {
    return this.cases.get(id);
  }

  getPacket(id: string): McpCasePacket | undefined {
    return this.packets.get(id);
  }

  /**
   * Returns every evidence record we know about for a case — both the bound
   * evidence the backend reports inside packet.claims, and any locally tracked
   * evidence created during this session that hasn't been bound to a claim
   * yet. De-duplicated by id.
   */
  getAllEvidence(caseId: string): McpEvidence[] {
    const packet = this.packets.get(caseId);
    const fromClaims = (packet?.claims ?? []).flatMap((c) => c.evidence);
    const pending = this.pendingEvidence.get(caseId) ?? [];
    const seen = new Set<string>();
    const merged: McpEvidence[] = [];
    for (const ev of [...pending, ...fromClaims]) {
      if (!seen.has(ev.id)) {
        seen.add(ev.id);
        merged.push(ev);
      }
    }
    return merged;
  }

  rememberEvidence(caseId: string, ev: McpEvidence): void {
    const list = this.pendingEvidence.get(caseId) ?? [];
    if (!list.some((e) => e.id === ev.id)) {
      list.unshift(ev);
      this.pendingEvidence.set(caseId, list);
    }
  }

  /**
   * Refreshes the case list and (optionally) all packets in parallel. Returns
   * silently on transport errors so callers can keep showing stale data.
   */
  async refresh(opts: { includePackets?: boolean } = {}): Promise<void> {
    let nextCases: McpCase[];
    try {
      nextCases = await this.mcp.listCases();
    } catch {
      return;
    }

    this.cases.clear();
    for (const c of nextCases) {
      this.cases.set(c.id, c);
    }

    if (opts.includePackets) {
      await Promise.all(nextCases.map((c) => this.refreshPacket(c.id)));
    } else {
      // Drop packets for cases that disappeared.
      for (const id of [...this.packets.keys()]) {
        if (!this.cases.has(id)) {
          this.packets.delete(id);
          this.pendingEvidence.delete(id);
        }
      }
    }

    this.emitter.fire({ kind: "cases" });
  }

  async refreshPacket(caseId: string): Promise<McpCasePacket | undefined> {
    const inFlight = this.packetFetches.get(caseId);
    if (inFlight) {
      return inFlight;
    }
    const promise = this.mcp
      .getStatus(caseId)
      .then((packet) => {
        this.packets.set(caseId, packet);
        // Status payloads include the latest case row — refresh our copy.
        this.cases.set(packet.case.id, packet.case);
        // Drop any pending evidence the backend now reports as bound — keeps
        // the local cache from drifting from the server view.
        const bound = new Set(
          packet.claims.flatMap((c) => c.evidence.map((e) => e.id))
        );
        const pending = this.pendingEvidence.get(caseId);
        if (pending && pending.length > 0) {
          const stillPending = pending.filter((e) => !bound.has(e.id));
          if (stillPending.length === 0) {
            this.pendingEvidence.delete(caseId);
          } else {
            this.pendingEvidence.set(caseId, stillPending);
          }
        }
        this.emitter.fire({ kind: "packet", caseId });
        return packet;
      })
      .catch(() => undefined)
      .finally(() => {
        this.packetFetches.delete(caseId);
      });
    this.packetFetches.set(caseId, promise);
    return promise;
  }

  dispose(): void {
    this.emitter.dispose();
  }
}

export type LedgerStoreEvent =
  | { kind: "cases" }
  | { kind: "packet"; caseId: string };

export function isLedgerCase(c: McpCase): boolean {
  const kind = (c.kind || "").toLowerCase();
  if (kind.includes("ledger") || kind.includes("agent_work")) {
    return true;
  }
  // Fallback: presence of contract metadata is a strong signal.
  const metadata = c.metadata || {};
  return Boolean(metadata.contract || metadata.work_contract);
}

function byUpdatedAtDesc(a: McpCase, b: McpCase): number {
  return (b.updated_at || "").localeCompare(a.updated_at || "");
}
