import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  backupPreview,
  createBackup,
  getBackupDetail,
  listBackups,
  restorePreview,
  restoreToNewLocation,
  verifyBackup,
} from "../api/client";
import { ManagedBackupRestore } from "./ManagedBackupRestore";

vi.mock("../api/client", () => ({
  backupPreview: vi.fn(),
  createBackup: vi.fn(),
  listBackups: vi.fn(),
  getBackupDetail: vi.fn(),
  verifyBackup: vi.fn(),
  restorePreview: vi.fn(),
  restoreToNewLocation: vi.fn(),
  formatApiError: (error: unknown) =>
    error instanceof Error ? error.message : "Unknown error",
}));

const mockBackupPreview = vi.mocked(backupPreview);
const mockCreateBackup = vi.mocked(createBackup);
const mockListBackups = vi.mocked(listBackups);
const mockGetBackupDetail = vi.mocked(getBackupDetail);
const mockVerifyBackup = vi.mocked(verifyBackup);
const mockRestorePreview = vi.mocked(restorePreview);
const mockRestoreToNewLocation = vi.mocked(restoreToNewLocation);

describe("ManagedBackupRestore", () => {
  beforeEach(() => {
    mockBackupPreview.mockReset();
    mockCreateBackup.mockReset();
    mockListBackups.mockReset();
    mockGetBackupDetail.mockReset();
    mockVerifyBackup.mockReset();
    mockRestorePreview.mockReset();
    mockRestoreToNewLocation.mockReset();
    mockListBackups.mockResolvedValue({ backups: [] });
  });

  it("renders safety non-goals without live, overwrite, delete, or retention controls", async () => {
    renderPage();

    expect(await screen.findByText("Local-only")).toBeInTheDocument();
    expect(screen.getByText("No live restore")).toBeInTheDocument();
    expect(screen.getByText("New inspection location only")).toBeInTheDocument();
    expect(screen.getByText("No overwrite restore")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /live restore/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /overwrite/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/retention/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create backup" })).toBeDisabled();
  });

  it("previews a backup and displays planned files and warnings", async () => {
    mockBackupPreview.mockResolvedValue(backupPreviewResponse());
    renderPage();

    await userEvent.type(screen.getByLabelText("Backup root"), "D:/backups");
    await userEvent.click(screen.getByRole("button", { name: "Preview backup" }));

    expect(mockBackupPreview).toHaveBeenCalledWith({ backup_root: "D:/backups" });
    expect(await screen.findByText("db/proofflow.db")).toBeInTheDocument();
    expect(screen.getAllByText("D:/ProofFlow/proofflow.db").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("proof_packets/case-1.md")).toBeInTheDocument();
    expect(screen.getByText("review free disk space")).toBeInTheDocument();
  });

  it("creates a backup and displays identifiers and hashes", async () => {
    mockBackupPreview.mockResolvedValue(backupPreviewResponse());
    mockCreateBackup.mockResolvedValue(createBackupResponse());
    renderPage();

    await userEvent.type(screen.getByLabelText("Backup root"), "D:/backups");
    await userEvent.type(screen.getByLabelText("Optional label"), "before-upgrade");
    expect(screen.getByRole("button", { name: "Create backup" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Preview backup" }));
    expect(await screen.findByText("Backup preview result")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Create backup" }));

    expect(mockBackupPreview).toHaveBeenCalledWith({ backup_root: "D:/backups" });
    expect(mockCreateBackup).toHaveBeenCalledWith({
      backup_root: "D:/backups",
      label: "before-upgrade",
    });
    expect(await screen.findByText("backup-created")).toBeInTheDocument();
    expect(screen.getByText("case-backup")).toBeInTheDocument();
    expect(screen.getByText("manifest-sha")).toBeInTheDocument();
    expect(screen.getByText("archive-sha")).toBeInTheDocument();
  });

  it("lists backups newest first and shows detail manifest summary", async () => {
    mockListBackups.mockResolvedValue({
      backups: [
        backupListItem("backup-old", "2026-04-27T00:00:00Z", "created"),
        backupListItem("backup-new", "2026-04-28T00:00:00Z", "verified"),
      ],
    });
    mockGetBackupDetail.mockResolvedValue(backupDetailResponse());
    renderPage();

    expect(await screen.findByText("backup-new")).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("backup-new")).toBeInTheDocument();
    expect(within(rows[2]).getByText("backup-old")).toBeInTheDocument();

    await userEvent.click(within(rows[1]).getByRole("button", { name: "Details" }));
    expect(mockGetBackupDetail).toHaveBeenCalledWith("backup-new");
    expect(await screen.findByText("0.1.0-rc1")).toBeInTheDocument();
    expect(screen.getByText("v0.1")).toBeInTheDocument();
  });

  it("verifies a backup and displays verified status and checked file count", async () => {
    mockListBackups.mockResolvedValue({
      backups: [backupListItem("backup-new", "2026-04-28T00:00:00Z", "created")],
    });
    mockVerifyBackup.mockResolvedValue(backupVerifyResponse());
    renderPage();

    const backupId = await screen.findByText("backup-new");
    const row = backupId.closest("tr");
    if (!row) throw new Error("backup row not found");

    await userEvent.click(within(row).getByRole("button", { name: "Verify" }));

    expect(mockVerifyBackup).toHaveBeenCalledWith("backup-new");
    expect(await screen.findByText("Verify result")).toBeInTheDocument();
    expect(screen.getByText("Checked files")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getAllByText("verified").length).toBeGreaterThanOrEqual(1);
  });

  it("previews inspection restore and displays plan, writes, risks, and warnings", async () => {
    mockRestorePreview.mockResolvedValue(restorePreviewResponse());
    renderPage();

    await fillRestorePreviewForm();
    await userEvent.click(screen.getByRole("button", { name: "Preview inspection restore" }));

    expect(mockRestorePreview).toHaveBeenCalledWith({
      backup_id: "backup-new",
      target_db_path: "D:/restore/proofflow.db",
      target_data_dir: "D:/restore/data",
    });
    expect(await screen.findByText("restore-preview-1")).toBeInTheDocument();
    expect(screen.getByText("plan-hash")).toBeInTheDocument();
    expect(screen.getByText("db/proofflow.db")).toBeInTheDocument();
    expect(screen.getByText(/schema_diff/)).toBeInTheDocument();
    expect(screen.getByText(/version_diff/)).toBeInTheDocument();
    expect(screen.getByText("inspection target only")).toBeInTheDocument();
  });

  it("keeps restore-to-new-location disabled before preview", async () => {
    renderPage();

    expect(
      await screen.findByRole("button", { name: "Restore to new inspection location" }),
    ).toBeDisabled();
  });

  it("invalidates accepted preview when target path changes", async () => {
    mockRestorePreview.mockResolvedValue(restorePreviewResponse());
    renderPage();

    await fillRestorePreviewForm();
    await userEvent.click(screen.getByRole("button", { name: "Preview inspection restore" }));

    const restoreButton = await screen.findByRole("button", {
      name: "Restore to new inspection location",
    });
    expect(restoreButton).toBeDisabled();

    await userEvent.click(screen.getByRole("button", {
      name: "Accept preview for inspection restore",
    }));
    expect(restoreButton).toBeEnabled();

    await userEvent.clear(screen.getByLabelText("Target DB path"));
    await userEvent.type(screen.getByLabelText("Target DB path"), "D:/restore/changed.db");

    expect(restoreButton).toBeDisabled();
  });

  it("requires explicit preview acceptance before restore-to-new-location", async () => {
    mockRestorePreview.mockResolvedValue(restorePreviewResponse());
    mockRestoreToNewLocation.mockResolvedValue(restoreToNewLocationResponse());
    renderPage();

    await fillRestorePreviewForm();
    expect(
      screen.getByRole("button", { name: "Restore to new inspection location" }),
    ).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Preview inspection restore" }));
    expect(
      await screen.findByRole("button", { name: "Restore to new inspection location" }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole("button", {
      name: "Accept preview for inspection restore",
    }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Restore to new inspection location" }),
    );

    expect(mockRestoreToNewLocation).toHaveBeenCalledWith({
      backup_id: "backup-new",
      target_db_path: "D:/restore/proofflow.db",
      target_data_dir: "D:/restore/data",
      accepted_preview_id: "restore-preview-1",
    });
    expect(await screen.findByText("restored_to_new_location")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("invalidates accepted preview after restore safety rejection", async () => {
    mockRestorePreview.mockResolvedValue(restorePreviewResponse());
    mockRestoreToNewLocation.mockRejectedValue(new Error("restore preview is stale"));
    renderPage();

    await fillRestorePreviewForm();
    await userEvent.click(screen.getByRole("button", { name: "Preview inspection restore" }));
    await userEvent.click(screen.getByRole("button", {
      name: "Accept preview for inspection restore",
    }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Restore to new inspection location" }),
    );

    expect(await screen.findByText("restore preview is stale")).toBeInTheDocument();
    expect(screen.queryByText("restore-preview-1")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Restore to new inspection location" }),
    ).toBeDisabled();
    expect(screen.getByText("Run restore preview before this action is available.")).toBeInTheDocument();
  });

  it("blocks restore action when preview reports overwrite", async () => {
    mockRestorePreview.mockResolvedValue({
      ...restorePreviewResponse(),
      planned_writes: [
        {
          archive_relative_path: "db/proofflow.db",
          target_path: "D:/restore/proofflow.db",
          role: "sqlite_db",
          action: "overwrite",
          size_bytes: 4096,
          sha256: "db-sha",
          would_overwrite: true,
        },
      ],
    });
    renderPage();

    await fillRestorePreviewForm();
    await userEvent.click(screen.getByRole("button", { name: "Preview inspection restore" }));

    expect(
      await screen.findByText(/Existing target files were detected in preview/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Restore to new inspection location" }),
    ).toBeDisabled();
    expect(mockRestoreToNewLocation).not.toHaveBeenCalled();
  });

  it("displays backend safety errors without hiding rejection text", async () => {
    mockRestorePreview.mockRejectedValue(
      new Error("target_data_dir overlaps live ProofFlow data dir"),
    );
    renderPage();

    await fillRestorePreviewForm();
    await userEvent.click(screen.getByRole("button", { name: "Preview inspection restore" }));

    expect(
      await screen.findByText("target_data_dir overlaps live ProofFlow data dir"),
    ).toBeInTheDocument();
    expect(mockRestoreToNewLocation).not.toHaveBeenCalled();
  });
});

function renderPage() {
  render(
    <MemoryRouter>
      <ManagedBackupRestore />
    </MemoryRouter>,
  );
}

async function fillRestorePreviewForm() {
  await userEvent.type(screen.getByLabelText("Backup ID"), "backup-new");
  await userEvent.type(screen.getByLabelText("Target DB path"), "D:/restore/proofflow.db");
  await userEvent.type(screen.getByLabelText("Target data dir"), "D:/restore/data");
}

function backupPreviewResponse() {
  return {
    source: {
      db_path: "D:/ProofFlow/proofflow.db",
      data_dir: "D:/ProofFlow/data",
      proof_packets_dir: "D:/ProofFlow/data/proof_packets",
    },
    planned_files: [
      {
        role: "sqlite_db",
        relative_path: "db/proofflow.db",
        size_bytes: 4096,
        source_path: "D:/ProofFlow/proofflow.db",
      },
      {
        role: "proof_packet",
        relative_path: "proof_packets/case-1.md",
        size_bytes: 512,
        source_path: "D:/ProofFlow/data/proof_packets/case-1.md",
      },
    ],
    warnings: ["review free disk space"],
    would_create_case: true,
  };
}

function createBackupResponse() {
  return {
    backup_id: "backup-created",
    case_id: "case-backup",
    archive_path: "D:/backups/backup-created.zip",
    manifest_path: "D:/backups/backup-created.manifest.json",
    manifest_sha256: "manifest-sha",
    archive_sha256: "archive-sha",
    warnings: [],
  };
}

function backupListItem(backupId: string, createdAt: string, status: string) {
  return {
    backup_id: backupId,
    created_at: createdAt,
    status,
    verified_at: status === "verified" ? "2026-04-28T00:10:00Z" : null,
    archive_path: `D:/backups/${backupId}.zip`,
  };
}

function backupDetailResponse() {
  return {
    backup_id: "backup-new",
    case_id: "case-backup",
    manifest: {
      manifest_version: "1",
      app_version: "0.1.0-rc1",
      schema_version: "v0.1",
    },
    archive_path: "D:/backups/backup-new.zip",
    verification: {
      status: "verified",
      verified_at: "2026-04-28T00:10:00Z",
      errors: [],
    },
    warnings: ["detail warning"],
  };
}

function backupVerifyResponse() {
  return {
    backup_id: "backup-new",
    case_id: "case-backup",
    status: "verified",
    checked_files: 2,
    hash_mismatches: [],
    missing_files: [],
    warnings: ["verify warning"],
  };
}

function restorePreviewResponse() {
  return {
    restore_preview_id: "restore-preview-1",
    backup_id: "backup-new",
    case_id: "case-backup",
    verified: true,
    target: {
      db_path: "D:/restore/proofflow.db",
      data_dir: "D:/restore/data",
    },
    planned_writes: [
      {
        archive_relative_path: "db/proofflow.db",
        target_path: "D:/restore/proofflow.db",
        role: "sqlite_db",
        action: "create" as const,
        size_bytes: 4096,
        sha256: "db-sha",
        would_overwrite: false,
      },
      {
        archive_relative_path: "proof_packets/case-1.md",
        target_path: "D:/restore/data/proof_packets/case-1.md",
        role: "proof_packet",
        action: "create" as const,
        size_bytes: 512,
        sha256: "packet-sha",
        would_overwrite: false,
      },
    ],
    plan_hash: "plan-hash",
    schema_risks: [
      { code: "schema_diff", message: "schema changed", blocking: false },
    ],
    version_risks: [
      { code: "version_diff", message: "app version changed", blocking: false },
    ],
    warnings: ["inspection target only"],
  };
}

function restoreToNewLocationResponse() {
  return {
    backup_id: "backup-new",
    restore_preview_id: "restore-preview-1",
    case_id: "case-backup",
    target: {
      db_path: "D:/restore/proofflow.db",
      data_dir: "D:/restore/data",
    },
    restored_files: 2,
    status: "restored_to_new_location" as const,
    warnings: [],
  };
}
