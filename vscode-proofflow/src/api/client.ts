import * as vscode from "vscode";
import type {
  CaseResponse,
  ActionResponse,
  ReviewResponse,
  ScanResponse,
  HealthResponse,
  CasePacket,
  DecisionCreatePayload,
  DecisionResponse,
} from "../types";
import { McpClient } from "../mcp/client";

/**
 * Backwards-compatible facade over the MCP-backed client. The public surface
 * matches the original REST client so commands, the poller, and the tests can
 * keep talking to a single object. New code should reach for {@link McpClient}
 * directly to access ledger and webview features.
 */
export class ProofFlowClient {
  private output: vscode.OutputChannel | undefined;
  private mcp: McpClient;

  constructor(mcp: McpClient, output?: vscode.OutputChannel) {
    this.mcp = mcp;
    this.output = output;
  }

  private log(msg: string): void {
    if (this.output) {
      const ts = new Date().toISOString();
      this.output.appendLine(`[${ts}] ${msg}`);
    }
  }

  getMcp(): McpClient {
    return this.mcp;
  }

  async checkHealth(): Promise<HealthResponse> {
    this.log("mcp -> proofflow_health");
    return this.mcp.health();
  }

  async listCases(): Promise<CaseResponse[]> {
    this.log("mcp -> proofflow_list_cases");
    return this.mcp.listCases() as Promise<CaseResponse[]>;
  }

  async listCaseActions(caseId: string): Promise<ActionResponse[]> {
    this.log(`mcp -> proofflow_list_actions(${caseId})`);
    return this.mcp.listActions(caseId) as Promise<ActionResponse[]>;
  }

  async review(repoPath: string): Promise<ReviewResponse> {
    this.log(`mcp -> proofflow_review(${repoPath})`);
    return this.mcp.review(repoPath, {
      baseRef: "HEAD",
      includeUntracked: true,
    }) as Promise<ReviewResponse>;
  }

  async scan(folderPath: string): Promise<ScanResponse> {
    this.log(`mcp -> proofflow_scan(${folderPath})`);
    return this.mcp.scan(folderPath) as Promise<ScanResponse>;
  }

  async approveAction(actionId: string): Promise<void> {
    // proofflow_approve_execute does the approve+execute combo. We expose
    // the plain approve under the same name so legacy callers stay correct;
    // the policy-gate decision flow uses createDecision + executeAction below.
    this.log(`mcp -> proofflow_approve_execute(${actionId})`);
    await this.mcp.approveExecute(actionId);
  }

  async createDecision(
    caseId: string,
    payload: DecisionCreatePayload
  ): Promise<DecisionResponse> {
    this.log(`mcp -> proofflow_decide(${caseId})`);
    return this.mcp.decide(caseId, payload) as Promise<DecisionResponse>;
  }

  async executeAction(actionId: string): Promise<ActionResponse> {
    // approve_execute on the MCP server runs both approve and execute, which
    // matches the legacy semantics of "after the policy gate decision is in,
    // run the action". For undo we have a dedicated MCP wrapper.
    this.log(`mcp -> proofflow_approve_execute(${actionId}) [execute]`);
    return this.mcp.approveExecute(actionId) as Promise<ActionResponse>;
  }

  async getCasePacket(caseId: string): Promise<CasePacket> {
    this.log(`mcp -> proofflow_status(${caseId})`);
    return this.mcp.getStatus(caseId) as Promise<CasePacket>;
  }
}
