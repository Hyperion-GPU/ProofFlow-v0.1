import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiGet, apiPost } from "../api/client";
import type { CasePacketResponse } from "../types";
import { IssueTriage } from "./IssueTriage";

vi.mock("../api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  formatApiError: (error: unknown) =>
    error instanceof Error ? error.message : "Unknown error",
}));

const mockApiGet = vi.mocked(apiGet);
const mockApiPost = vi.mocked(apiPost);

describe("IssueTriage", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPost.mockReset();
  });

  it("creates an issue triage Case and exports a Proof Packet", async () => {
    mockApiPost
      .mockResolvedValueOnce({
        case_id: "case-issue",
        run_id: "run-issue",
        risk_level: "info",
        artifact_id: "artifact-issue",
        component: "codex_plugin",
        suggested_labels: ["bug", "component:codex_plugin", "usability"],
        has_reproduction_steps: true,
        has_expected_behavior: true,
        has_environment_details: true,
        claims_created: 5,
        evidence_created: 5,
      })
      .mockResolvedValueOnce({
        case_id: "case-issue",
        artifact_id: "packet-artifact",
        format: "markdown",
        path: "D:/ProofFlow/data/proof_packets/case-issue.md",
        filename: "case-issue.md",
        created_at: "2026-01-01T00:00:00Z",
        content: "# Proof Packet",
      });
    mockApiGet.mockResolvedValue(issuePacket());

    render(
      <MemoryRouter>
        <IssueTriage />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Issue title"), "Codex plugin triage is indirect");
    await userEvent.type(screen.getByLabelText("Source URL"), "https://github.com/org/repo/issues/1");
    await userEvent.type(screen.getByLabelText("Labels"), "bug, usability, bug");
    await userEvent.type(
      screen.getByLabelText("Issue body"),
      "Steps to Reproduce\n1. Open Codex\n2. Ask for triage\nExpected Behavior\nCreate a Case\nEnvironment\nWindows 11",
    );
    await userEvent.click(screen.getByRole("button", { name: "Create triage Case" }));

    expect(mockApiPost).toHaveBeenCalledWith("/issue-triage", {
      title: "Codex plugin triage is indirect",
      body: "Steps to Reproduce\n1. Open Codex\n2. Ask for triage\nExpected Behavior\nCreate a Case\nEnvironment\nWindows 11",
      source_url: "https://github.com/org/repo/issues/1",
      labels: ["bug", "usability"],
    });
    expect(await screen.findByText("Risk info")).toBeInTheDocument();
    expect(screen.getByText("Component codex_plugin")).toBeInTheDocument();
    expect(screen.getByText("Repro present")).toBeInTheDocument();
    expect(screen.getByText("Expected present")).toBeInTheDocument();
    expect(screen.getByText("Env present")).toBeInTheDocument();
    expect(screen.getByText("Issue source captured for triage")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Case" })).toHaveAttribute(
      "href",
      "/cases/case-issue",
    );

    await userEvent.click(screen.getByRole("button", { name: "Export Packet" }));
    expect(mockApiPost).toHaveBeenLastCalledWith("/reports/cases/case-issue/export", {
      format: "markdown",
    });
    expect(
      await screen.findByText(/Exported case-issue.md at/),
    ).toBeInTheDocument();
  });

  it("shows missing triage signals for incomplete reports", async () => {
    mockApiPost.mockResolvedValue({
      case_id: "case-issue",
      run_id: "run-issue",
      risk_level: "medium",
      artifact_id: "artifact-issue",
      component: "mcp_server",
      suggested_labels: ["bug", "component:mcp_server"],
      has_reproduction_steps: false,
      has_expected_behavior: false,
      has_environment_details: false,
      claims_created: 4,
      evidence_created: 4,
    });
    mockApiGet.mockResolvedValue(issuePacket("medium"));

    render(
      <MemoryRouter>
        <IssueTriage />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Issue title"), "MCP review tool fails");
    await userEvent.click(screen.getByRole("button", { name: "Create triage Case" }));

    expect(await screen.findByText("Risk medium")).toBeInTheDocument();
    expect(screen.getByText("Repro missing")).toBeInTheDocument();
    expect(screen.getByText("Expected missing")).toBeInTheDocument();
    expect(screen.getByText("Env missing")).toBeInTheDocument();
  });
});

function issuePacket(risk = "info"): CasePacketResponse {
  const now = "2026-01-01T00:00:00Z";
  return {
    case: {
      id: "case-issue",
      title: "Issue triage: Codex plugin triage is indirect",
      kind: "issue_triage",
      status: "open",
      summary: "ProofFlow issue triage",
      metadata: { risk_level: risk },
      created_at: now,
      updated_at: now,
      decision_count: 0,
    },
    risk_level: risk as CasePacketResponse["risk_level"],
    artifacts: [],
    claims: [
      {
        id: "claim-1",
        run_id: "run-issue",
        claim_text: "Issue source captured for triage",
        claim_type: "issue_triage",
        status: "open",
        severity: risk as CasePacketResponse["risk_level"],
        evidence: [],
        created_at: now,
        updated_at: now,
      },
    ],
    actions: [],
    decisions: [],
    runs: [],
    observations: [],
  };
}
