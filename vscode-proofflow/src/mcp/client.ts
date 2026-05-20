import * as vscode from "vscode";
import type {
  McpAction,
  McpCase,
  McpCasePacket,
  McpDecision,
  McpDecisionPayload,
  McpEvaluationResult,
  McpExportResult,
  McpHealth,
  McpReviewResult,
  McpScanResult,
  McpSearchResult,
  ProofFlowMcpState,
} from "./types";

export interface McpClientConfig {
  /** Reserved for forward compatibility; ignored by the REST backend. */
  pythonPath: string;
  backendUrl: string;
  apiKey: string;
  /** Reserved for forward compatibility; ignored by the REST backend. */
  extraEnv: Record<string, string>;
}

export interface McpClientEvents {
  onStateChange?: (state: ProofFlowMcpState, detail?: string) => void;
  onLog?: (line: string) => void;
}

const HEALTHY_STATES: ProofFlowMcpState[] = ["ready"];

/**
 * Local-first ProofFlow client. Despite the `Mcp` prefix kept for backwards
 * compatibility within this extension, the implementation talks to the
 * ProofFlow backend over its REST API at `proofflow.backendUrl`.
 *
 * The original v0.2 design routed through `python -m proofflow_mcp` over
 * stdio, but the MCP server's tool responses are formatted as agent-readable
 * text, not JSON, which makes them unsuitable for a structured UI client.
 * Going REST keeps the same backend semantics and lets us reuse the typed
 * wrappers across the extension untouched.
 */
export class McpClient implements vscode.Disposable {
  private state: ProofFlowMcpState = "idle";
  private healthCheck: Promise<McpHealth> | undefined;

  constructor(private config: McpClientConfig, private events: McpClientEvents = {}) {
    this.transitionTo("starting");
    // Fire and forget — the poller will run health on its own cadence.
    this.healthCheck = this.health()
      .then((res) => {
        this.transitionTo("ready");
        return res;
      })
      .catch((err) => {
        this.transitionTo(
          "failed",
          err instanceof Error ? err.message : String(err)
        );
        return undefined as unknown as McpHealth;
      });
  }

  getState(): ProofFlowMcpState {
    return this.state;
  }

  applyConfig(config: McpClientConfig): void {
    this.config = config;
    this.transitionTo("starting");
    void this.health()
      .then(() => this.transitionTo("ready"))
      .catch((err) =>
        this.transitionTo(
          "failed",
          err instanceof Error ? err.message : String(err)
        )
      );
  }

  private transitionTo(state: ProofFlowMcpState, detail?: string): void {
    this.state = state;
    this.events.onStateChange?.(state, detail);
  }

  private get baseUrl(): string {
    return this.config.backendUrl.replace(/\/+$/, "");
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    query?: Record<string, string | number | boolean | undefined>
  ): Promise<T> {
    const params = query
      ? "?" +
        Object.entries(query)
          .filter(([, v]) => v !== undefined)
          .map(
            ([k, v]) =>
              `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`
          )
          .join("&")
      : "";
    const url = `${this.baseUrl}${path}${params}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.config.apiKey) {
      headers["X-ProofFlow-Token"] = this.config.apiKey;
    }
    this.events.onLog?.(`${method} ${url}`);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      // Soft-transition: only flip to failed if we were previously healthy or
      // never connected. Avoids flapping during transient network blips.
      if (!HEALTHY_STATES.includes(this.state)) {
        this.transitionTo("failed", detail);
      }
      throw new Error(`ProofFlow backend unreachable (${detail})`);
    }

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`ProofFlow API ${response.status}: ${text.slice(0, 200)}`);
    }

    if (response.status === 204) {
      return undefined as unknown as T;
    }
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return (await response.json()) as T;
    }
    return (await response.text()) as unknown as T;
  }

  // --- Health ---

  async health(): Promise<McpHealth> {
    return this.request<McpHealth>("GET", "/health");
  }

  // --- Cases ---

  async listCases(): Promise<McpCase[]> {
    return this.request<McpCase[]>("GET", "/cases");
  }

  async listActions(caseId: string): Promise<McpAction[]> {
    return this.request<McpAction[]>("GET", `/cases/${caseId}/actions`);
  }

  async getStatus(caseId: string): Promise<McpCasePacket> {
    return this.request<McpCasePacket>("GET", `/cases/${caseId}/packet`);
  }

  // --- Scan / suggest ---

  async scan(
    folderPath: string,
    opts: { recursive?: boolean; maxFiles?: number } = {}
  ): Promise<McpScanResult> {
    return this.request<McpScanResult>("POST", "/localproof/scan", {
      folder_path: folderPath,
      recursive: opts.recursive ?? true,
      max_files: opts.maxFiles ?? 500,
    });
  }

  async suggest(caseId: string, targetRoot: string): Promise<unknown> {
    return this.request<unknown>("POST", "/localproof/suggest-actions", {
      case_id: caseId,
      target_root: targetRoot,
    });
  }

  // --- AgentGuard ---

  async review(
    repoPath: string,
    opts: { baseRef?: string; includeUntracked?: boolean; testCommand?: string } = {}
  ): Promise<McpReviewResult> {
    const body: Record<string, unknown> = {
      repo_path: repoPath,
      base_ref: opts.baseRef ?? "HEAD",
      include_untracked: opts.includeUntracked ?? true,
    };
    if (opts.testCommand !== undefined) {
      body.test_command = opts.testCommand;
    }
    return this.request<McpReviewResult>("POST", "/agentguard/review", body);
  }

  // --- Triage ---

  async triageIssue(args: {
    title: string;
    body?: string;
    sourceUrl?: string;
    labels?: string[];
  }): Promise<unknown> {
    const payload: Record<string, unknown> = {
      title: args.title,
      body: args.body ?? "",
      labels: args.labels ?? [],
    };
    if (args.sourceUrl) {
      payload.source_url = args.sourceUrl;
    }
    return this.request<unknown>("POST", "/issue-triage", payload);
  }

  // --- Actions ---

  async approveExecute(actionId: string): Promise<McpAction> {
    // Two-step at the REST layer: approve flips status to approved, execute
    // performs the filesystem mutation. Mirrors the legacy ProofFlowClient
    // semantics so the policy gate flow stays correct.
    await this.request<unknown>("POST", `/actions/${actionId}/approve`);
    return this.request<McpAction>("POST", `/actions/${actionId}/execute`);
  }

  async undo(actionId: string): Promise<McpAction> {
    return this.request<McpAction>("POST", `/actions/${actionId}/undo`);
  }

  async decide(
    caseId: string,
    payload: McpDecisionPayload
  ): Promise<McpDecision> {
    return this.request<McpDecision>(
      "POST",
      `/cases/${caseId}/decisions`,
      {
        title: payload.title,
        status: payload.status,
        rationale: payload.rationale,
        result: payload.result,
        metadata: payload.metadata ?? {},
      }
    );
  }

  // --- Export / search ---

  async exportPacket(caseId: string): Promise<McpExportResult> {
    const result = await this.request<{
      case_id: string;
      content?: string;
      filename?: string;
      path?: string;
      format?: string;
    }>("POST", `/reports/cases/${caseId}/export`, { format: "markdown" });
    return {
      case_id: result.case_id,
      format: "markdown",
      content: result.content ?? "",
    };
  }

  async search(query: string, limit = 25): Promise<McpSearchResult> {
    return this.request<McpSearchResult>("GET", "/search", undefined, {
      q: query,
      limit,
    });
  }

  // --- Ledger ---

  ledger = {
    startContract: (args: {
      objective: string;
      repoPath: string;
      allowedScope?: string[];
      forbiddenActions?: string[];
      requiredTests?: string[];
      doneCriteria?: string[];
      evidenceRequirements?: string[];
      algorithmRequirements?: string[];
      costBudget?: Record<string, unknown>;
    }): Promise<{ case_id: string }> => {
      return this.request<{ case_id: string }>("POST", "/ledger/start", {
        objective: args.objective,
        repo_path: args.repoPath,
        allowed_scope: args.allowedScope ?? [],
        forbidden_actions: args.forbiddenActions ?? [],
        required_tests: args.requiredTests ?? [],
        done_criteria: args.doneCriteria ?? [],
        evidence_requirements: args.evidenceRequirements ?? [],
        algorithm_requirements: args.algorithmRequirements ?? [],
        cost_budget: args.costBudget ?? {},
      });
    },
    recordEvent: (args: {
      caseId: string;
      eventType: string;
      summary: string;
      content?: string;
      metadata?: Record<string, unknown>;
    }): Promise<unknown> => {
      return this.request<unknown>(
        "POST",
        `/ledger/cases/${args.caseId}/events`,
        {
          event_type: args.eventType,
          summary: args.summary,
          content: args.content ?? "",
          metadata: args.metadata ?? {},
        }
      );
    },
    recordAlgorithmDecision: (args: {
      caseId: string;
      summary: string;
      chosenApproach: string;
      rationale: string;
      alternativesConsidered?: string[];
      invariants?: string[];
      forbiddenApproaches?: string[];
      metadata?: Record<string, unknown>;
    }): Promise<unknown> => {
      return this.request<unknown>(
        "POST",
        `/ledger/cases/${args.caseId}/algorithm-decisions`,
        {
          summary: args.summary,
          chosen_approach: args.chosenApproach,
          rationale: args.rationale,
          alternatives_considered: args.alternativesConsidered ?? [],
          invariants: args.invariants ?? [],
          forbidden_approaches: args.forbiddenApproaches ?? [],
          metadata: args.metadata ?? {},
        }
      );
    },
    recordCostBudget: (args: {
      caseId: string;
      summary: string;
      budget?: Record<string, unknown>;
      expectedOperations?: string[];
      limits?: string[];
      metadata?: Record<string, unknown>;
    }): Promise<unknown> => {
      return this.request<unknown>(
        "POST",
        `/ledger/cases/${args.caseId}/cost-budgets`,
        {
          summary: args.summary,
          budget: args.budget ?? {},
          expected_operations: args.expectedOperations ?? [],
          limits: args.limits ?? [],
          metadata: args.metadata ?? {},
        }
      );
    },
    captureSnapshot: (args: {
      caseId: string;
      repoPath: string;
      phase: "start" | "checkpoint" | "final";
      baseRef?: string;
      includeUntracked?: boolean;
    }): Promise<unknown> => {
      return this.request<unknown>(
        "POST",
        `/ledger/cases/${args.caseId}/snapshots`,
        {
          repo_path: args.repoPath,
          phase: args.phase,
          base_ref: args.baseRef ?? "HEAD",
          include_untracked: args.includeUntracked ?? true,
        }
      );
    },
    recordEvidence: (args: {
      caseId: string;
      evidenceType: string;
      content: string;
      sourceRef?: string;
      metadata?: Record<string, unknown>;
    }): Promise<{
      case_id: string;
      artifact_id: string;
      evidence_id: string;
      evidence_type: string;
      created_at: string;
    }> => {
      const body: Record<string, unknown> = {
        evidence_type: args.evidenceType,
        content: args.content,
        metadata: args.metadata ?? {},
      };
      if (args.sourceRef) {
        body.source_ref = args.sourceRef;
      }
      return this.request(
        "POST",
        `/ledger/cases/${args.caseId}/evidence`,
        body
      );
    },
    recordClaim: (args: {
      caseId: string;
      claimText: string;
      evidenceIds: string[];
      severity?: "info" | "low" | "medium" | "high";
    }): Promise<{ id: string }> => {
      return this.request<{ id: string }>(
        "POST",
        `/ledger/cases/${args.caseId}/claims`,
        {
          claim_text: args.claimText,
          severity: args.severity ?? "info",
          evidence_ids: args.evidenceIds,
        }
      );
    },
    evaluateContract: (caseId: string): Promise<McpEvaluationResult> => {
      return this.request<McpEvaluationResult>(
        "POST",
        `/ledger/cases/${caseId}/evaluate`
      );
    },
    explainRiskHint: (args: {
      caseId: string;
      evaluationRunId: string;
      hintCode: string;
      disposition: string;
      rationale: string;
      evidenceIds: string[];
    }): Promise<unknown> => {
      return this.request<unknown>(
        "POST",
        `/ledger/cases/${args.caseId}/risk-hints/decisions`,
        {
          evaluation_run_id: args.evaluationRunId,
          hint_code: args.hintCode,
          disposition: args.disposition,
          rationale: args.rationale,
          evidence_ids: args.evidenceIds,
        }
      );
    },
    finish: (args: { caseId: string; summary?: string }): Promise<unknown> => {
      const body: Record<string, unknown> = {};
      if (args.summary !== undefined) {
        body.summary = args.summary;
      }
      return this.request<unknown>(
        "POST",
        `/ledger/cases/${args.caseId}/finish`,
        body
      );
    },
  };

  async dispose(): Promise<void> {
    // No long-lived resources to clean up — the v0.2 stdio transport has been
    // replaced with stateless fetch calls.
  }
}

export function resolvePythonCommand(): never {
  throw new Error(
    "resolvePythonCommand is no longer used; the extension now talks to the ProofFlow backend over REST."
  );
}

export function resolveMcpEnv(config: McpClientConfig): Record<string, string> {
  // Kept for backwards-compatible imports. Nothing reads this anymore but
  // tests still exercise it to make sure backendUrl/apiKey are surfaced.
  const env: Record<string, string> = { ...config.extraEnv };
  if (config.backendUrl) {
    env.PROOFFLOW_BASE_URL = config.backendUrl;
  }
  if (config.apiKey) {
    env.PROOFFLOW_API_KEY = config.apiKey;
  }
  return env;
}
