import * as vscode from "vscode";
import type {
  CaseResponse,
  ActionResponse,
  ReviewResponse,
  ScanResponse,
  HealthResponse,
  CasePacket,
} from "../types";

export class ProofFlowClient {
  private output: vscode.OutputChannel | undefined;

  constructor(output?: vscode.OutputChannel) {
    this.output = output;
  }

  private log(msg: string): void {
    if (this.output) {
      const ts = new Date().toISOString();
      this.output.appendLine(`[${ts}] ${msg}`);
    }
  }

  private get baseUrl(): string {
    return vscode.workspace
      .getConfiguration("proofflow")
      .get<string>("backendUrl", "http://127.0.0.1:8787");
  }

  private get apiKey(): string {
    return vscode.workspace
      .getConfiguration("proofflow")
      .get<string>("apiKey", "");
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["X-ProofFlow-Token"] = this.apiKey;
    }

    this.log(`${method} ${url}`);

    let resp: Response;
    try {
      resp = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      this.log(`  fetch threw: ${msg}`);
      throw err;
    }

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      this.log(`  ${resp.status} ${text.slice(0, 200)}`);
      throw new Error(`ProofFlow API ${resp.status}: ${text}`);
    }

    const data = (await resp.json()) as T;
    const summary = Array.isArray(data)
      ? `array(${data.length})`
      : "object";
    this.log(`  ${resp.status} ${summary}`);
    return data;
  }

  async checkHealth(): Promise<HealthResponse> {
    return this.request("GET", "/health");
  }

  async listCases(): Promise<CaseResponse[]> {
    return this.request("GET", "/cases");
  }

  async listCaseActions(caseId: string): Promise<ActionResponse[]> {
    return this.request("GET", `/cases/${caseId}/actions`);
  }

  async review(repoPath: string): Promise<ReviewResponse> {
    return this.request("POST", "/agentguard/review", {
      repo_path: repoPath,
      base_ref: "HEAD",
      include_untracked: true,
    });
  }

  async scan(folderPath: string): Promise<ScanResponse> {
    return this.request("POST", "/localproof/scan", {
      folder_path: folderPath,
      recursive: true,
      max_files: 500,
    });
  }

  async approveAction(actionId: string): Promise<void> {
    await this.request("POST", `/actions/${actionId}/approve`);
  }

  async executeAction(actionId: string): Promise<void> {
    await this.request("POST", `/actions/${actionId}/execute`);
  }

  async getCasePacket(caseId: string): Promise<CasePacket> {
    return this.request("GET", `/cases/${caseId}/packet`);
  }
}
