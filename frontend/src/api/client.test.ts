import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  apiPost,
  backupPreview,
  createBackup,
  getBackupDetail,
  listBackups,
  restorePreview,
  restoreToNewLocation,
  verifyBackup,
} from "./client";

const mockFetch = vi.fn();

describe("managed backup restore API helpers", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses the existing backup and restore endpoints with strict payload shapes", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({ source: {}, planned_files: [], warnings: [] }))
      .mockResolvedValueOnce(jsonResponse({ backup_id: "backup-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ backups: [] }))
      .mockResolvedValueOnce(jsonResponse({ backup_id: "backup 1" }))
      .mockResolvedValueOnce(jsonResponse({ backup_id: "backup 1", status: "verified" }))
      .mockResolvedValueOnce(jsonResponse({ restore_preview_id: "preview-1" }))
      .mockResolvedValueOnce(jsonResponse({ status: "restored_to_new_location" }));

    await backupPreview({ backup_root: "D:/backups" });
    expectLastFetch("/backups/preview", "POST", { backup_root: "D:/backups" });

    await createBackup({ backup_root: "D:/backups", label: "before-upgrade" });
    expectLastFetch("/backups", "POST", {
      backup_root: "D:/backups",
      label: "before-upgrade",
    });

    await listBackups();
    expectLastFetch("/backups");

    await getBackupDetail("backup 1");
    expectLastFetch("/backups/backup%201");

    await verifyBackup("backup 1");
    expectLastFetch("/backups/backup%201/verify", "POST", {});

    await restorePreview({
      backup_id: "backup 1",
      target_db_path: "D:/restore/proofflow.db",
      target_data_dir: "D:/restore/data",
    });
    expectLastFetch("/restore/preview", "POST", {
      backup_id: "backup 1",
      target_db_path: "D:/restore/proofflow.db",
      target_data_dir: "D:/restore/data",
    });

    await restoreToNewLocation({
      backup_id: "backup 1",
      target_db_path: "D:/restore/proofflow.db",
      target_data_dir: "D:/restore/data",
      accepted_preview_id: "preview-1",
    });
    expectLastFetch("/restore/to-new-location", "POST", {
      backup_id: "backup 1",
      target_db_path: "D:/restore/proofflow.db",
      target_data_dir: "D:/restore/data",
      accepted_preview_id: "preview-1",
    });
  });

  it("preserves non-JSON non-OK response text", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response("restore preview is stale", {
        status: 400,
        statusText: "Bad Request",
        headers: { "Content-Type": "text/plain" },
      }),
    );

    await expect(
      restorePreview({
        backup_id: "backup 1",
        target_db_path: "D:/restore/proofflow.db",
        target_data_dir: "D:/restore/data",
      }),
    ).rejects.toMatchObject({
      status: 400,
      detail: "restore preview is stale",
      message: "restore preview is stale",
    });
  });

  it("rejects non-JSON OK responses with a clean API error", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response("<html>proxy fallback</html>", {
        status: 200,
        headers: { "Content-Type": "text/html" },
      }),
    );

    await expect(listBackups()).rejects.toMatchObject({
      status: 200,
      detail: "Malformed API response: expected JSON",
      message: "Malformed API response: expected JSON",
    });
  });

  it("preserves empty OK response behavior for void-style callers", async () => {
    mockFetch.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiPost<void>("/void-style")).resolves.toBeNull();
    expectLastFetch("/void-style", "POST", {});
  });
});

function expectLastFetch(path: string, method?: string, body?: unknown) {
  const [url, init] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1] ?? [];
  expect(url).toBe(`http://127.0.0.1:8787${path}`);
  expect(init).toEqual(
    expect.objectContaining({
      headers: expect.objectContaining({ "Content-Type": "application/json" }),
      ...(method ? { method } : {}),
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    }),
  );
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
