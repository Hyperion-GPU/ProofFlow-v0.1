import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "./Dashboard";
import { apiGet } from "../api/client";

vi.mock("../api/client", () => ({
  API_BASE_URL: "http://127.0.0.1:8787",
  apiGet: vi.fn(),
  formatApiError: (error: unknown) =>
    error instanceof Error ? error.message : "Unknown error",
}));

const mockApiGet = vi.mocked(apiGet);

describe("Dashboard", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
  });

  it("shows backend health and recent cases", async () => {
    mockApiGet.mockImplementation((path: string) => {
      if (path === "/health") {
        return Promise.resolve({ ok: true, service: "proofflow" });
      }
      if (path === "/cases") {
        return Promise.resolve([
          {
            id: "case-1",
            title: "Dogfood case",
            kind: "local_proof",
            status: "open",
            summary: "Seeded dogfood case",
            metadata: {},
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ]);
      }
      return Promise.reject(new Error(`unexpected path: ${path}`));
    });

    render(<Dashboard />);

    expect(screen.getByText("ProofFlow workspace")).toBeInTheDocument();
    expect(await screen.findByText("Backend online")).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:8787")).toBeInTheDocument();
    expect(screen.getByText("Dogfood case")).toBeInTheDocument();
  });
});
