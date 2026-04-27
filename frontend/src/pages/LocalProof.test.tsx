import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LocalProof } from "./LocalProof";
import { apiGet, apiPost } from "../api/client";
import type { ActionResponse } from "../types";

vi.mock("../api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  formatApiError: (error: unknown) =>
    error instanceof Error ? error.message : "Unknown error",
}));

const mockApiGet = vi.mocked(apiGet);
const mockApiPost = vi.mocked(apiPost);

describe("LocalProof", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPost.mockReset();
  });

  it("scans, suggests, and completes action approve execute undo flow", async () => {
    let actions = [mkdirAction("pending"), moveAction("pending")];
    mockApiPost.mockImplementation((path: string) => {
      if (path === "/localproof/scan") {
        return Promise.resolve({
          case_id: "case-localproof",
          files_seen: 1,
          artifacts_created: 1,
          artifacts_updated: 0,
          text_chunks_created: 1,
          skipped: 0,
          skipped_items: [],
        });
      }
      if (path === "/localproof/suggest-actions") {
        return Promise.resolve({
          case_id: "case-localproof",
          target_root: "D:/sorted",
          actions_created: 2,
          skipped: 0,
          skipped_items: [],
          actions,
        });
      }
      if (path === "/actions/mkdir-1/approve") {
        actions = [mkdirAction("approved"), moveAction("pending")];
        return Promise.resolve(actions[0]);
      }
      if (path === "/actions/mkdir-1/execute") {
        actions = [mkdirAction("executed"), moveAction("pending")];
        return Promise.resolve(actions[0]);
      }
      if (path === "/actions/move-1/approve") {
        actions = [mkdirAction("executed"), moveAction("approved")];
        return Promise.resolve(actions[1]);
      }
      if (path === "/actions/move-1/execute") {
        actions = [mkdirAction("executed"), moveAction("executed")];
        return Promise.resolve(actions[1]);
      }
      if (path === "/actions/move-1/undo") {
        actions = [mkdirAction("executed"), moveAction("undone")];
        return Promise.resolve(actions[1]);
      }
      if (path === "/actions/mkdir-1/undo") {
        actions = [mkdirAction("undone"), moveAction("undone")];
        return Promise.resolve(actions[0]);
      }
      return Promise.reject(new Error(`unexpected post: ${path}`));
    });
    mockApiGet.mockImplementation((path: string) => {
      if (path === "/cases/case-localproof/actions") {
        return Promise.resolve(actions);
      }
      return Promise.reject(new Error(`unexpected get: ${path}`));
    });

    render(
      <MemoryRouter>
        <LocalProof />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Folder path"), "D:/inbox");
    await userEvent.click(screen.getByRole("button", { name: "Scan" }));

    expect(await screen.findByText("case-localproof")).toBeInTheDocument();
    expect(screen.getByText("Files seen")).toBeInTheDocument();
    expect(screen.getByText("Text chunks")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Target root"), "D:/sorted");
    await userEvent.click(screen.getByRole("button", { name: "Suggest actions" }));

    expect(await screen.findByText("Create Notes directory")).toBeInTheDocument();
    expect(screen.getByText("Move notes.md to Notes")).toBeInTheDocument();
    expect(screen.getAllByText("D:/sorted/Notes").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("D:/inbox/notes.md")).toBeInTheDocument();
    expect(screen.getAllByText("D:/sorted/Notes/notes.md").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Preview").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Result").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Undo").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Metadata").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Depends on action")).toBeInTheDocument();
    expect(screen.getAllByText("mkdir-1").length).toBeGreaterThanOrEqual(1);

    await userEvent.click(buttonInAction("Create Notes directory", "Approve"));
    expect(await statusInAction("Create Notes directory", "approved")).toBeInTheDocument();

    await userEvent.click(buttonInAction("Create Notes directory", "Execute"));
    expect(await statusInAction("Create Notes directory", "executed")).toBeInTheDocument();

    await userEvent.click(buttonInAction("Move notes.md to Notes", "Approve"));
    expect(await statusInAction("Move notes.md to Notes", "approved")).toBeInTheDocument();

    await userEvent.click(buttonInAction("Move notes.md to Notes", "Execute"));
    expect(await statusInAction("Move notes.md to Notes", "executed")).toBeInTheDocument();

    await userEvent.click(buttonInAction("Move notes.md to Notes", "Undo"));
    expect(await statusInAction("Move notes.md to Notes", "undone")).toBeInTheDocument();

    await userEvent.click(buttonInAction("Create Notes directory", "Undo"));
    expect(await statusInAction("Create Notes directory", "undone")).toBeInTheDocument();
  });
});

function buttonInAction(title: string, name: string): HTMLButtonElement {
  return within(actionItem(title)).getByRole("button", { name });
}

async function statusInAction(title: string, status: string) {
  return within(actionItem(title)).findByText(status);
}

function actionItem(title: string): HTMLElement {
  const titleNode = screen.getByText(title);
  const item = titleNode.closest("li");
  if (!item) {
    throw new Error(`action item not found: ${title}`);
  }
  return item;
}

function mkdirAction(status: string): ActionResponse {
  return {
    id: "mkdir-1",
    case_id: "case-localproof",
    kind: "mkdir_dir",
    status,
    title: "Create Notes directory",
    reason: "Deterministic LocalProof prerequisite: destination directory",
    preview: { dir_path: "D:/sorted/Notes" },
    result: status === "executed" || status === "undone"
      ? { operation: "mkdir_dir", created: true, already_exists: false }
      : null,
    undo: status === "executed" || status === "undone"
      ? { operation: "remove_dir", dir_path: "D:/sorted/Notes", created_by_action: true }
      : null,
    metadata: {
      source: "localproof_suggest_actions",
      category: "Notes",
      rule: "missing_destination_directory",
    },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function moveAction(status: string): ActionResponse {
  return {
    id: "move-1",
    case_id: "case-localproof",
    kind: "move_file",
    status,
    title: "Move notes.md to Notes",
    reason: "Deterministic LocalProof rule: note",
    preview: {
      from_path: "D:/inbox/notes.md",
      to_path: "D:/sorted/Notes/notes.md",
    },
    result: status === "executed" || status === "undone"
      ? {
          operation: "move_file",
          from_path: "D:/inbox/notes.md",
          to_path: "D:/sorted/Notes/notes.md",
        }
      : null,
    undo: status === "executed" || status === "undone"
      ? {
          operation: "restore_file",
          from_path: "D:/sorted/Notes/notes.md",
          to_path: "D:/inbox/notes.md",
        }
      : null,
    metadata: {
      source: "localproof_suggest_actions",
      category: "Notes",
      rule: "note",
      depends_on_action_id: "mkdir-1",
      depends_on_dir_path: "D:/sorted/Notes",
    },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}
