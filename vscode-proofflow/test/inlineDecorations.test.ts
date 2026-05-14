import assert from "node:assert/strict";
import test from "node:test";

import { buildClaimDecorations, claimDecorationRange } from "../src/inlineDecorations";
import type { CasePacket } from "../src/types";
import { workspaceFolder } from "vscode";

function packet(overrides: Partial<CasePacket> = {}): CasePacket {
  return {
    case: {
      id: "case-1",
      title: "Review",
      kind: "code_review",
      status: "open",
      metadata: {},
      created_at: "2026-05-14T00:00:00Z",
      updated_at: "2026-05-14T00:00:00Z",
    },
    risk_level: "medium",
    artifacts: [],
    claims: [],
    actions: [],
    decisions: [],
    runs: [],
    observations: [],
    ...overrides,
  };
}

test("buildClaimDecorations resolves reliable source locations against workspace roots", () => {
  const decorations = buildClaimDecorations(
    packet({
      claims: [
        {
          id: "claim-1",
          run_id: "run-1",
          claim_text: "File operation code changed without tests.",
          claim_type: "agentguard_risk",
          status: "open",
          severity: "medium",
          created_at: "2026-05-14T00:00:00Z",
          updated_at: "2026-05-14T00:00:00Z",
          evidence: [
            {
              id: "evidence-1",
              artifact_id: "artifact-1",
              claim_id: "claim-1",
              evidence_type: "git_diff",
              content: "Changed files: src/actions.ts",
              source_ref: "src/actions.ts:12-14",
              artifact_name: "git-diff.patch",
              artifact_path: null,
              source_location: {
                path: "src/actions.ts",
                start_line: 12,
                end_line: 14,
                source: "source_ref",
              },
              created_at: "2026-05-14T00:00:00Z",
            },
          ],
        },
      ],
    }),
    [workspaceFolder("C:\\repo") as never]
  );

  assert.equal(decorations.length, 1);
  assert.equal(decorations[0].filePath, "C:\\repo\\src\\actions.ts");
  assert.equal(decorations[0].startLine, 12);
  assert.equal(decorations[0].endLine, 14);
  assert.equal(decorations[0].severity, "medium");
});

test("buildClaimDecorations skips claims without a reliable source location", () => {
  const decorations = buildClaimDecorations(
    packet({
      claims: [
        {
          id: "claim-1",
          run_id: "run-1",
          claim_text: "Changed file count: 1.",
          claim_type: "agentguard_risk",
          status: "open",
          severity: "info",
          created_at: "2026-05-14T00:00:00Z",
          updated_at: "2026-05-14T00:00:00Z",
          evidence: [
            {
              id: "evidence-1",
              artifact_id: "artifact-1",
              claim_id: "claim-1",
              evidence_type: "git_diff",
              content: "Changed files: src/actions.ts",
              source_ref: "src/actions.ts",
              artifact_name: "git-diff.patch",
              artifact_path: null,
              source_location: null,
              created_at: "2026-05-14T00:00:00Z",
            },
          ],
        },
      ],
    }),
    [workspaceFolder("C:\\repo") as never]
  );

  assert.deepEqual(decorations, []);
});

test("buildClaimDecorations can use packet repo_path when no workspace is available", () => {
  const decorations = buildClaimDecorations(
    packet({
      case: {
        id: "case-1",
        title: "Review",
        kind: "code_review",
        status: "open",
        metadata: { repo_path: "C:\\repo" },
        created_at: "2026-05-14T00:00:00Z",
        updated_at: "2026-05-14T00:00:00Z",
      },
      claims: [
        {
          id: "claim-1",
          run_id: null,
          claim_text: "Tests failed.",
          claim_type: "agentguard_risk",
          status: "open",
          severity: "high",
          created_at: "2026-05-14T00:00:00Z",
          updated_at: "2026-05-14T00:00:00Z",
          evidence: [
            {
              id: "evidence-1",
              artifact_id: null,
              claim_id: "claim-1",
              evidence_type: "test_output",
              content: "failed",
              source_ref: "tests/test_actions.py:42",
              artifact_name: null,
              artifact_path: null,
              source_location: {
                path: "tests/test_actions.py",
                start_line: 42,
                end_line: 42,
                source: "source_ref",
              },
              created_at: "2026-05-14T00:00:00Z",
            },
          ],
        },
      ],
    }),
    undefined
  );

  assert.equal(decorations[0].filePath, "C:\\repo\\tests\\test_actions.py");
  assert.equal(decorations[0].severity, "high");
});

test("claimDecorationRange includes the packet inclusive end line", () => {
  const range = claimDecorationRange({
    filePath: "C:\\repo\\src\\actions.ts",
    startLine: 12,
    endLine: 14,
    severity: "medium",
    message: "ProofFlow medium claim",
  });

  assert.equal(range.startLine, 11);
  assert.equal(range.startCharacter, 0);
  assert.equal(range.endLine, 14);
  assert.equal(range.endCharacter, 0);
});
