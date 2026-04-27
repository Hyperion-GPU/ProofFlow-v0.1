import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CaseDetail } from "./CaseDetail";
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

describe("CaseDetail", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPost.mockReset();
  });

  it("renders packet sections and exports a proof packet", async () => {
    mockApiGet.mockResolvedValue(casePacket());
    mockApiPost.mockResolvedValue({
      case_id: "case-detail",
      artifact_id: "packet-artifact",
      format: "markdown",
      path: "D:/ProofFlow/data/proof_packets/case-detail.md",
      filename: "case-detail.md",
      created_at: "2026-01-01T00:00:00Z",
      content: "# Proof Packet",
    });

    render(
      <MemoryRouter initialEntries={["/cases/case-detail"]}>
        <Routes>
          <Route path="/cases/:caseId" element={<CaseDetail />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Dogfood packet case")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Summary" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Linked Artifacts" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Claims & Evidence" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Actions" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Decisions" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Runs & Test Results" })).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Export Proof Packet" }));

    expect(mockApiPost).toHaveBeenCalledWith("/reports/cases/case-detail/export", {
      format: "markdown",
    });
    expect(
      await screen.findByText(
        "Exported case-detail.md at D:/ProofFlow/data/proof_packets/case-detail.md",
      ),
    ).toBeInTheDocument();
    expect(mockApiGet).toHaveBeenCalledTimes(2);
  });
});

function casePacket(): CasePacketResponse {
  const now = "2026-01-01T00:00:00Z";
  return {
    case: {
      id: "case-detail",
      title: "Dogfood packet case",
      kind: "code_review",
      status: "open",
      summary: "Dogfood summary",
      metadata: { risk_level: "high" },
      created_at: now,
      updated_at: now,
      decision_count: 1,
    },
    risk_level: "high",
    artifacts: [
      {
        id: "artifact-1",
        kind: "git_diff",
        role: "primary",
        name: "git-diff.patch",
        uri: "agentguard://case-detail/git-diff.patch",
        path: "D:/repo/git-diff.patch",
        mime_type: "text/plain",
        sha256: "sha256",
        size_bytes: 128,
        created_at: now,
        updated_at: now,
      },
    ],
    claims: [
      {
        id: "claim-1",
        run_id: "run-1",
        claim_text: "Claim with evidence",
        claim_type: "agentguard_risk",
        status: "open",
        severity: "high",
        evidence: [
          {
            id: "evidence-1",
            artifact_id: "artifact-1",
            claim_id: "claim-1",
            evidence_type: "git_diff",
            content: "Evidence content",
            source_ref: "src/app.py",
            artifact_name: "git-diff.patch",
            artifact_path: "D:/repo/git-diff.patch",
            created_at: now,
          },
        ],
        created_at: now,
        updated_at: now,
      },
    ],
    actions: [
      {
        id: "action-1",
        case_id: "case-detail",
        kind: "manual_check",
        status: "executed",
        title: "Review evidence",
        reason: "Human review",
        preview: {},
        result: { touched_files: false },
        undo: null,
        metadata: {},
        created_at: now,
        updated_at: now,
      },
    ],
    decisions: [
      {
        id: "decision-1",
        case_id: "case-detail",
        title: "Accept packet",
        status: "accepted",
        rationale: "Evidence is complete.",
        result: "Use for dogfood.",
        created_at: now,
        updated_at: now,
      },
    ],
    runs: [
      {
        id: "run-1",
        run_type: "agentguard_review",
        status: "failed",
        started_at: now,
        finished_at: now,
        metadata: {
          test_status: "failed",
          test_command: "python -m pytest",
          test_returncode: 7,
        },
        created_at: now,
        updated_at: now,
      },
    ],
  };
}
