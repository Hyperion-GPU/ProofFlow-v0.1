import assert from "node:assert/strict";
import test from "node:test";

import { LedgerStore, isLedgerCase } from "../src/store/ledgerStore";
import type { McpCase, McpCasePacket } from "../src/mcp/types";

function fakeMcp(state: {
  cases: McpCase[];
  packets: Record<string, McpCasePacket>;
  failPacket?: boolean;
  failList?: boolean;
}) {
  const calls: string[] = [];
  return {
    calls,
    listCases: async () => {
      calls.push("listCases");
      if (state.failList) {
        throw new Error("offline");
      }
      return state.cases;
    },
    getStatus: async (id: string) => {
      calls.push(`getStatus:${id}`);
      if (state.failPacket) {
        throw new Error("packet failed");
      }
      const packet = state.packets[id];
      if (!packet) {
        throw new Error("not found");
      }
      return packet;
    },
  } as unknown as ConstructorParameters<typeof LedgerStore>[0];
}

function buildCase(id: string, overrides: Partial<McpCase> = {}): McpCase {
  return {
    id,
    title: `Case ${id}`,
    kind: "agent_work_ledger",
    status: "open",
    summary: null,
    metadata: {},
    created_at: "2026-05-19T00:00:00Z",
    updated_at: "2026-05-19T00:00:00Z",
    ...overrides,
  };
}

function buildPacket(c: McpCase): McpCasePacket {
  return {
    case: { ...c, decision_count: 0 },
    risk_level: "info",
    artifacts: [],
    claims: [],
    actions: [],
    decisions: [],
    runs: [],
    observations: [],
  };
}

test("isLedgerCase detects ledger kinds and contract metadata", () => {
  assert.ok(isLedgerCase(buildCase("a", { kind: "agent_work_ledger" })));
  assert.ok(isLedgerCase(buildCase("b", { kind: "ledger_case" })));
  assert.ok(
    isLedgerCase(
      buildCase("c", {
        kind: "code_review",
        metadata: { work_contract: { objective: "x" } },
      })
    )
  );
  assert.equal(
    isLedgerCase(buildCase("d", { kind: "code_review" })),
    false
  );
});

test("LedgerStore.refresh populates cases and emits events", async () => {
  const cases = [buildCase("a"), buildCase("b")];
  const mcp = fakeMcp({ cases, packets: {} });
  const store = new LedgerStore(mcp);
  let fired = 0;
  const sub = store.onDidChange((event) => {
    if (event.kind === "cases") {
      fired += 1;
    }
  });
  await store.refresh();
  assert.equal(fired, 1);
  assert.equal(store.getCases().length, 2);
  sub.dispose();
});

test("LedgerStore.refresh keeps prior data when MCP fails", async () => {
  const cases = [buildCase("a")];
  const mcp = fakeMcp({ cases, packets: {} });
  const store = new LedgerStore(mcp);
  await store.refresh();
  assert.equal(store.getCases().length, 1);

  // Now simulate an outage; the store should silently keep prior cache.
  (mcp as { failList?: boolean }).failList = true;
  await store.refresh();
  assert.equal(store.getCases().length, 1);
});

test("LedgerStore.refreshPacket caches packets and dedupes concurrent fetches", async () => {
  const c = buildCase("a");
  const packet = buildPacket(c);
  const mcp = fakeMcp({ cases: [c], packets: { a: packet } });
  const store = new LedgerStore(mcp);
  await store.refresh();
  const [p1, p2] = await Promise.all([
    store.refreshPacket("a"),
    store.refreshPacket("a"),
  ]);
  assert.equal(p1, p2);
  assert.equal(
    (mcp as { calls: string[] }).calls.filter((c2) =>
      c2.startsWith("getStatus")
    ).length,
    1
  );
  assert.deepEqual(store.getPacket("a"), packet);
});

test("LedgerStore.refreshPacket swallows errors and returns undefined", async () => {
  const c = buildCase("a");
  const mcp = fakeMcp({
    cases: [c],
    packets: {},
    failPacket: true,
  });
  const store = new LedgerStore(mcp);
  const result = await store.refreshPacket("a");
  assert.equal(result, undefined);
  assert.equal(store.getPacket("a"), undefined);
});

test("LedgerStore.refresh with includePackets fetches packets in parallel", async () => {
  const cases = [buildCase("a"), buildCase("b")];
  const mcp = fakeMcp({
    cases,
    packets: {
      a: buildPacket(cases[0]),
      b: buildPacket(cases[1]),
    },
  });
  const store = new LedgerStore(mcp);
  await store.refresh({ includePackets: true });
  assert.ok(store.getPacket("a"));
  assert.ok(store.getPacket("b"));
});
