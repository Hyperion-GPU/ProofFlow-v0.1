import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AgentGuard } from "./AgentGuard";
import { apiGet, apiPost } from "../api/client";
import type { CasePacketResponse } from "../types";

vi.mock("../api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  formatApiError: (error: unknown) =>
    error instanceof Error ? error.message : "Unknown error",
}));

const mockApiGet = vi.mocked(apiGet);
const mockApiPost = vi.mocked(apiPost);

describe("AgentGuard", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPost.mockReset();
  });

  it("runs review and displays changed files, claims, and test metadata", async () => {
    mockApiPost.mockResolvedValue({
      case_id: "case-agentguard",
      run_id: "run-agentguard",
      risk_level: "medium",
      changed_files: ["src/app.py"],
      claims_created: 1,
      evidence_created: 1,
      artifacts: [{ id: "artifact-diff", kind: "git_diff", name: "git-diff.patch" }],
    });
    mockApiGet.mockResolvedValue(agentGuardPacket());

    render(
      <MemoryRouter>
        <AgentGuard />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Repo path"), "D:/repo");
    await userEvent.type(screen.getByLabelText("Test command"), "python -m pytest");
    await userEvent.click(screen.getByRole("button", { name: "Run review" }));

    expect(mockApiPost).toHaveBeenCalledWith("/agentguard/review", {
      repo_path: "D:/repo",
      base_ref: "HEAD",
      include_untracked: true,
      test_command: "python -m pytest",
    });
    expect(await screen.findByText("Risk medium")).toBeInTheDocument();
    expect(screen.getByText("Test passed")).toBeInTheDocument();
    expect(screen.getByText("python -m pytest")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("src/app.py")).toBeInTheDocument();
    expect(screen.getByText("Review claim with evidence")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Case" })).toHaveAttribute(
      "href",
      "/cases/case-agentguard",
    );
  });
});

function agentGuardPacket(): CasePacketResponse {
  const now = "2026-01-01T00:00:00Z";
  return {
    case: {
      id: "case-agentguard",
      title: "AgentGuard case",
      kind: "code_review",
      status: "open",
      summary: "Review summary",
      metadata: { risk_level: "medium" },
      created_at: now,
      updated_at: now,
      decision_count: 0,
    },
    risk_level: "medium",
    artifacts: [],
    claims: [
      {
        id: "claim-1",
        run_id: "run-agentguard",
        claim_text: "Review claim with evidence",
        claim_type: "agentguard_risk",
        status: "open",
        severity: "medium",
        evidence: [
          {
            id: "evidence-1",
            artifact_id: "artifact-diff",
            claim_id: "claim-1",
            evidence_type: "git_diff",
            content: "Changed file: src/app.py",
            source_ref: "src/app.py",
            artifact_name: "git-diff.patch",
            artifact_path: "agentguard://case-agentguard/git-diff.patch",
            created_at: now,
          },
        ],
        created_at: now,
        updated_at: now,
      },
    ],
    actions: [],
    decisions: [],
    runs: [
      {
        id: "run-agentguard",
        run_type: "agentguard_review",
        status: "completed",
        started_at: now,
        finished_at: now,
        metadata: {
          test_status: "passed",
          test_command: "python -m pytest",
          test_returncode: 0,
        },
        created_at: now,
        updated_at: now,
      },
    ],
  };
}
