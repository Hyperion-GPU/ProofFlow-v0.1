import assert from "node:assert/strict";
import test from "node:test";

import { McpClient, resolveMcpEnv } from "../src/mcp/client";

interface CallRecord {
  method: string;
  url: string;
  body: unknown;
}

function installFetchMock(
  responder: (
    method: string,
    url: string,
    body: unknown
  ) =>
    | { status?: number; json?: unknown; text?: string; contentType?: string }
    | Promise<{ status?: number; json?: unknown; text?: string; contentType?: string }>,
  records: CallRecord[]
): () => void {
  const original = globalThis.fetch;
  globalThis.fetch = (async (
    input: string | URL | Request,
    init?: RequestInit
  ) => {
    const method = (init?.method || "GET").toUpperCase();
    const url = typeof input === "string" ? input : input.toString();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    records.push({ method, url, body });
    const result = await responder(method, url, body);
    const status = result.status ?? 200;
    const contentType =
      result.contentType ??
      (result.json !== undefined ? "application/json" : "text/plain");
    const payload =
      result.json !== undefined ? JSON.stringify(result.json) : result.text || "";
    return {
      ok: status >= 200 && status < 300,
      status,
      headers: { get: () => contentType },
      async json() {
        return result.json;
      },
      async text() {
        return payload;
      },
    } as unknown as Response;
  }) as typeof globalThis.fetch;
  return () => {
    globalThis.fetch = original;
  };
}

function defaultConfig() {
  return {
    pythonPath: "",
    backendUrl: "http://test.local",
    apiKey: "",
    extraEnv: {},
  };
}

function nonHealth(records: CallRecord[]): CallRecord[] {
  return records.filter((r) => !r.url.endsWith("/health"));
}

test("resolveMcpEnv forwards backend URL and api key", () => {
  const env = resolveMcpEnv({
    pythonPath: "",
    backendUrl: "http://example:1234",
    apiKey: "secret",
    extraEnv: { CUSTOM: "yes" },
  });
  assert.equal(env.PROOFFLOW_BASE_URL, "http://example:1234");
  assert.equal(env.PROOFFLOW_API_KEY, "secret");
  assert.equal(env.CUSTOM, "yes");
});

test("McpClient.health calls /health and returns the JSON body", async () => {
  const records: CallRecord[] = [];
  const restore = installFetchMock(
    () => ({ json: { status: "ok", version: "0.2.0-dev" } }),
    records
  );
  try {
    const client = new McpClient(defaultConfig());
    const result = await client.health();
    assert.equal(records[0].method, "GET");
    assert.ok(records[0].url.endsWith("/health"));
    assert.equal(result.version, "0.2.0-dev");
  } finally {
    restore();
  }
});

test("McpClient.health restores ready state after a failed check", async () => {
  const records: CallRecord[] = [];
  let healthCalls = 0;
  const states: string[] = [];
  const restore = installFetchMock(
    (_method, url) => {
      if (url.endsWith("/health")) {
        healthCalls += 1;
        if (healthCalls === 1) {
          return { status: 503, text: "backend not running" };
        }
        return { json: { status: "ok", version: "0.2.0-dev" } };
      }
      return { status: 404, text: "not found" };
    },
    records
  );
  try {
    const client = new McpClient(defaultConfig(), {
      onStateChange: (state) => states.push(state),
    });
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(client.getState(), "failed");

    const result = await client.health();

    assert.equal(result.version, "0.2.0-dev");
    assert.equal(client.getState(), "ready");
    assert.deepEqual(states, ["starting", "failed", "ready"]);
  } finally {
    restore();
  }
});

test("McpClient.listCases hits /cases", async () => {
  const records: CallRecord[] = [];
  const restore = installFetchMock(
    (_method, url) => {
      if (url.endsWith("/health")) {
        return { json: { status: "ok", version: "test" } };
      }
      return {
        json: [
          {
            id: "case-1",
            title: "x",
            kind: "code_review",
            status: "open",
            metadata: {},
            created_at: "",
            updated_at: "",
          },
        ],
      };
    },
    records
  );
  try {
    const client = new McpClient(defaultConfig());
    const cases = await client.listCases();
    assert.equal(cases[0].id, "case-1");
    const tracked = nonHealth(records);
    assert.ok(tracked[0].url.endsWith("/cases"));
  } finally {
    restore();
  }
});

test("McpClient.ledger.startContract sends snake_case payload to /ledger/start", async () => {
  const records: CallRecord[] = [];
  const restore = installFetchMock(
    (_method, url) => {
      if (url.endsWith("/health")) {
        return { json: { status: "ok", version: "test" } };
      }
      return { json: { case_id: "case-42" } };
    },
    records
  );
  try {
    const client = new McpClient(defaultConfig());
    const result = await client.ledger.startContract({
      objective: "Implement OAuth",
      repoPath: "C:/repo",
      allowedScope: ["src/auth"],
      forbiddenActions: ["touching prod"],
      doneCriteria: ["tests pass"],
    });
    assert.equal(result.case_id, "case-42");
    const call = nonHealth(records)[0];
    assert.equal(call.method, "POST");
    assert.ok(call.url.endsWith("/ledger/start"));
    assert.deepEqual(call.body, {
      objective: "Implement OAuth",
      repo_path: "C:/repo",
      allowed_scope: ["src/auth"],
      forbidden_actions: ["touching prod"],
      required_tests: [],
      done_criteria: ["tests pass"],
      evidence_requirements: [],
      algorithm_requirements: [],
      cost_budget: {},
    });
  } finally {
    restore();
  }
});

test("McpClient.ledger.recordEvidence omits source_ref when not provided", async () => {
  const records: CallRecord[] = [];
  const restore = installFetchMock(
    (_method, url) => {
      if (url.endsWith("/health")) {
        return { json: { status: "ok", version: "test" } };
      }
      return { json: { id: "ev-1" } };
    },
    records
  );
  try {
    const client = new McpClient(defaultConfig());
    await client.ledger.recordEvidence({
      caseId: "case-1",
      evidenceType: "command_output",
      content: "ok",
    });
    const call = nonHealth(records)[0];
    const body = call.body as Record<string, unknown>;
    assert.equal(body.evidence_type, "command_output");
    assert.equal(body.content, "ok");
    assert.equal(body.source_ref, undefined);
  } finally {
    restore();
  }
});

test("McpClient surfaces non-2xx responses as exceptions", async () => {
  const restore = installFetchMock(
    () => ({ status: 503, text: "backend not running" }),
    []
  );
  try {
    const client = new McpClient(defaultConfig());
    await assert.rejects(client.health(), /503/);
  } finally {
    restore();
  }
});

test("McpClient.approveExecute executes decision-gated actions directly", async () => {
  const records: CallRecord[] = [];
  const restore = installFetchMock((_method, url) => {
    if (url.endsWith("/health")) {
      return { json: { status: "ok", version: "test" } };
    }
    if (url.endsWith("/execute")) {
      return {
        json: {
          id: "action-1",
          status: "executed",
          kind: "move_file",
          title: "x",
          case_id: "case-1",
          created_at: "",
        },
      };
    }
    return { status: 404, text: "not found" };
  }, records);
  try {
    const client = new McpClient(defaultConfig());
    const result = await client.approveExecute("action-1");
    assert.equal(result.status, "executed");
    const actionCalls = records.filter((r) => !r.url.endsWith("/health"));
    assert.equal(actionCalls.length, 1);
    assert.ok(actionCalls[0].url.endsWith("/actions/action-1/execute"));
  } finally {
    restore();
  }
});

test("McpClient.approveExecute approves when backend says approval is required", async () => {
  const records: CallRecord[] = [];
  let executeCalls = 0;
  const restore = installFetchMock((_method, url) => {
    if (url.endsWith("/health")) {
      return { json: { status: "ok", version: "test" } };
    }
    if (url.endsWith("/execute")) {
      executeCalls += 1;
      if (executeCalls === 1) {
        return {
          status: 400,
          text: "only approved or decision-gated actions can execute",
        };
      }
      return {
        json: {
          id: "action-1",
          status: "executed",
          kind: "move_file",
          title: "x",
          case_id: "case-1",
          created_at: "",
        },
      };
    }
    if (url.endsWith("/approve")) {
      return { json: {} };
    }
    return { status: 404, text: "not found" };
  }, records);
  try {
    const client = new McpClient(defaultConfig());
    const result = await client.approveExecute("action-1");
    assert.equal(result.status, "executed");
    const actionCalls = records.filter((r) => !r.url.endsWith("/health"));
    assert.equal(actionCalls.length, 3);
    assert.ok(actionCalls[0].url.endsWith("/actions/action-1/execute"));
    assert.ok(actionCalls[1].url.endsWith("/actions/action-1/approve"));
    assert.ok(actionCalls[2].url.endsWith("/actions/action-1/execute"));
  } finally {
    restore();
  }
});
