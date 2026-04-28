import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  backupPreview,
  createBackup,
  formatApiError,
  getBackupDetail,
  listBackups,
  restorePreview,
  restoreToNewLocation,
  verifyBackup,
} from "../api/client";
import type {
  BackupCreateResponse,
  BackupDetailResponse,
  BackupListItem,
  BackupPreviewResponse,
  BackupVerifyResponse,
  PlannedBackupFile,
  RestorePlannedWrite,
  RestorePreviewResponse,
  RestoreRisk,
  RestoreToNewLocationResponse,
} from "../types";

type AcceptedPreview = {
  restorePreviewId: string;
  backupId: string;
  targetDbPath: string;
  targetDataDir: string;
};

export function ManagedBackupRestore() {
  const [backupRoot, setBackupRoot] = useState("");
  const [backupLabel, setBackupLabel] = useState("");
  const [backupPreviewResult, setBackupPreviewResult] =
    useState<BackupPreviewResponse | null>(null);
  const [backupPreviewRoot, setBackupPreviewRoot] = useState<string | null>(null);
  const [createResult, setCreateResult] = useState<BackupCreateResponse | null>(null);
  const [backups, setBackups] = useState<BackupListItem[]>([]);
  const [detailResult, setDetailResult] = useState<BackupDetailResponse | null>(null);
  const [verifyResult, setVerifyResult] = useState<BackupVerifyResponse | null>(null);
  const [restoreBackupId, setRestoreBackupId] = useState("");
  const [targetDbPath, setTargetDbPath] = useState("");
  const [targetDataDir, setTargetDataDir] = useState("");
  const [restorePreviewResult, setRestorePreviewResult] =
    useState<RestorePreviewResponse | null>(null);
  const [restorePreviewScope, setRestorePreviewScope] =
    useState<Omit<AcceptedPreview, "restorePreviewId"> | null>(null);
  const [acceptedPreview, setAcceptedPreview] = useState<AcceptedPreview | null>(null);
  const [restoreResult, setRestoreResult] =
    useState<RestoreToNewLocationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [backupBusy, setBackupBusy] = useState<"preview" | "create" | null>(null);
  const [detailBusy, setDetailBusy] = useState<string | null>(null);
  const [verifyBusy, setVerifyBusy] = useState<string | null>(null);
  const [restoreBusy, setRestoreBusy] = useState<"preview" | "restore" | null>(null);

  useEffect(() => {
    let active = true;
    setListLoading(true);
    listBackups()
      .then((response) => {
        if (!active) return;
        setBackups(sortBackups(response.backups));
        setError(null);
      })
      .catch((requestError: unknown) => {
        if (active) setError(formatApiError(requestError));
      })
      .finally(() => {
        if (active) setListLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!backupPreviewRoot) return;
    if (backupPreviewRoot !== backupRoot.trim()) {
      setBackupPreviewRoot(null);
      setBackupPreviewResult(null);
      setCreateResult(null);
    }
  }, [backupPreviewRoot, backupRoot]);

  useEffect(() => {
    if (!acceptedPreview) return;
    if (
      acceptedPreview.backupId !== restoreBackupId.trim() ||
      acceptedPreview.targetDbPath !== targetDbPath.trim() ||
      acceptedPreview.targetDataDir !== targetDataDir.trim()
    ) {
      setAcceptedPreview(null);
      setRestorePreviewResult(null);
      setRestoreResult(null);
    }
  }, [acceptedPreview, restoreBackupId, targetDataDir, targetDbPath]);

  useEffect(() => {
    if (!restorePreviewScope) return;
    if (
      restorePreviewScope.backupId !== restoreBackupId.trim() ||
      restorePreviewScope.targetDbPath !== targetDbPath.trim() ||
      restorePreviewScope.targetDataDir !== targetDataDir.trim()
    ) {
      setRestorePreviewResult(null);
      setRestorePreviewScope(null);
      setAcceptedPreview(null);
      setRestoreResult(null);
    }
  }, [restorePreviewScope, restoreBackupId, targetDataDir, targetDbPath]);

  const restoreBlockingRisks = useMemo(
    () =>
      [
        ...(restorePreviewResult?.schema_risks ?? []),
        ...(restorePreviewResult?.version_risks ?? []),
      ].filter((risk) => risk.blocking),
    [restorePreviewResult],
  );
  const restoreWouldOverwrite =
    restorePreviewResult?.planned_writes.some((write) => write.would_overwrite) ?? false;
  const restoreInputsReady =
    restoreBackupId.trim() && targetDbPath.trim() && targetDataDir.trim();
  const restorePreviewMatchesInputs =
    restorePreviewResult !== null &&
    restorePreviewScope !== null &&
    restorePreviewScope.backupId === restoreBackupId.trim() &&
    restorePreviewScope.targetDbPath === targetDbPath.trim() &&
    restorePreviewScope.targetDataDir === targetDataDir.trim();
  const acceptedPreviewMatchesInputs =
    acceptedPreview !== null &&
    acceptedPreview.backupId === restoreBackupId.trim() &&
    acceptedPreview.targetDbPath === targetDbPath.trim() &&
    acceptedPreview.targetDataDir === targetDataDir.trim();
  const canCreateBackup =
    Boolean(backupRoot.trim()) &&
    backupPreviewResult !== null &&
    backupPreviewRoot === backupRoot.trim() &&
    backupBusy === null;
  const canAcceptRestorePreview =
    Boolean(restoreInputsReady) &&
    restorePreviewMatchesInputs &&
    acceptedPreview === null &&
    restoreBlockingRisks.length === 0 &&
    !restoreWouldOverwrite &&
    restoreBusy === null;
  const canRunRestore =
    Boolean(restoreInputsReady) &&
    restorePreviewMatchesInputs &&
    acceptedPreviewMatchesInputs &&
    restoreBlockingRisks.length === 0 &&
    !restoreWouldOverwrite &&
    restoreBusy === null;

  function refreshBackupList() {
    setListLoading(true);
    listBackups()
      .then((response) => {
        setBackups(sortBackups(response.backups));
        setError(null);
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)))
      .finally(() => setListLoading(false));
  }

  function runBackupPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBackupBusy("preview");
    backupPreview({ backup_root: backupRoot.trim() })
      .then((response) => {
        setBackupPreviewResult(response);
        setBackupPreviewRoot(backupRoot.trim());
        setError(null);
      })
      .catch((requestError: unknown) => {
        setBackupPreviewRoot(null);
        setBackupPreviewResult(null);
        setError(formatApiError(requestError));
      })
      .finally(() => setBackupBusy(null));
  }

  function runCreateBackup() {
    if (!canCreateBackup) return;
    setBackupBusy("create");
    createBackup({
      backup_root: backupRoot.trim(),
      label: backupLabel.trim() || undefined,
    })
      .then((response) => {
        setCreateResult(response);
        setError(null);
        refreshBackupList();
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)))
      .finally(() => setBackupBusy(null));
  }

  function loadBackupDetail(backupId: string) {
    setDetailBusy(backupId);
    getBackupDetail(backupId)
      .then((response) => {
        setDetailResult(response);
        setError(null);
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)))
      .finally(() => setDetailBusy(null));
  }

  function runVerifyBackup(backupId: string) {
    setVerifyBusy(backupId);
    verifyBackup(backupId)
      .then((response) => {
        setVerifyResult(response);
        setError(null);
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)))
      .finally(() => setVerifyBusy(null));
  }

  function runRestorePreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRestoreBusy("preview");
    restorePreview({
      backup_id: restoreBackupId.trim(),
      target_db_path: targetDbPath.trim(),
      target_data_dir: targetDataDir.trim(),
    })
      .then((response) => {
        setRestorePreviewResult(response);
        setRestorePreviewScope({
          backupId: restoreBackupId.trim(),
          targetDbPath: targetDbPath.trim(),
          targetDataDir: targetDataDir.trim(),
        });
        setAcceptedPreview(null);
        setRestoreResult(null);
        setError(null);
      })
      .catch((requestError: unknown) => {
        setRestorePreviewResult(null);
        setRestorePreviewScope(null);
        setAcceptedPreview(null);
        setRestoreResult(null);
        setError(formatApiError(requestError));
      })
      .finally(() => setRestoreBusy(null));
  }

  function acceptRestorePreview() {
    if (!restorePreviewResult || !restorePreviewScope || !canAcceptRestorePreview) return;
    setAcceptedPreview({
      restorePreviewId: restorePreviewResult.restore_preview_id,
      backupId: restorePreviewScope.backupId,
      targetDbPath: restorePreviewScope.targetDbPath,
      targetDataDir: restorePreviewScope.targetDataDir,
    });
    setRestoreResult(null);
    setError(null);
  }

  function runRestoreToNewLocation() {
    if (!acceptedPreview || !restorePreviewResult) return;
    setRestoreBusy("restore");
    restoreToNewLocation({
      backup_id: restoreBackupId.trim(),
      target_db_path: targetDbPath.trim(),
      target_data_dir: targetDataDir.trim(),
      accepted_preview_id: acceptedPreview.restorePreviewId,
      })
      .then((response) => {
        setRestoreResult(response);
        setError(null);
      })
      .catch((requestError: unknown) => {
        setAcceptedPreview(null);
        setRestorePreviewResult(null);
        setRestorePreviewScope(null);
        setRestoreResult(null);
        setError(formatApiError(requestError));
      })
      .finally(() => setRestoreBusy(null));
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Managed backup / restore</p>
          <h1>Backup and inspection restore</h1>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Safety status</h2>
            <p className="summary-text">
              This surface controls existing local backup APIs. Restore output is
              inspection evidence only.
            </p>
          </div>
        </div>
        <div className="chip-row" aria-label="Managed backup restore guardrails">
          <span className="status-pill ok">Local-only</span>
          <span className="status-pill warn">No live restore</span>
          <span className="status-pill ok">New inspection location only</span>
          <span className="status-pill warn">No overwrite restore</span>
        </div>
      </section>

      <div className="two-column">
        <form className="panel form-grid" onSubmit={runBackupPreview}>
          <h2>Backup preview and create</h2>
          <label>
            Backup root
            <input
              value={backupRoot}
              placeholder="D:\\ProofFlowBackups"
              onChange={(event) => setBackupRoot(event.target.value)}
            />
          </label>
          <label>
            Optional label
            <input
              value={backupLabel}
              placeholder="before-upgrade"
              onChange={(event) => setBackupLabel(event.target.value)}
            />
          </label>
          <div className="action-buttons">
            <button type="submit" disabled={!backupRoot.trim() || backupBusy !== null}>
              {backupBusy === "preview" ? "Previewing..." : "Preview backup"}
            </button>
            <button
              type="button"
              disabled={!canCreateBackup}
              onClick={runCreateBackup}
            >
              {backupBusy === "create" ? "Creating..." : "Create backup"}
            </button>
          </div>
        </form>

        <form className="panel form-grid" onSubmit={runRestorePreview}>
          <h2>Restore preview</h2>
          <p className="notice-text">
            Restore preview only plans a new inspection location. It does not apply
            changes to the live workspace.
          </p>
          <label>
            Backup ID
            <input
              value={restoreBackupId}
              placeholder="backup_20260427_000000"
              onChange={(event) => setRestoreBackupId(event.target.value)}
            />
          </label>
          <label>
            Target DB path
            <input
              value={targetDbPath}
              placeholder="D:\\ProofFlowRestore\\proofflow.db"
              onChange={(event) => setTargetDbPath(event.target.value)}
            />
          </label>
          <label>
            Target data dir
            <input
              value={targetDataDir}
              placeholder="D:\\ProofFlowRestore\\data"
              onChange={(event) => setTargetDataDir(event.target.value)}
            />
          </label>
          <button
            type="submit"
            disabled={!restoreInputsReady || restoreBusy !== null}
          >
            {restoreBusy === "preview" ? "Previewing..." : "Preview inspection restore"}
          </button>
        </form>
      </div>

      <BackupPreviewResult result={backupPreviewResult} />
      <CreateBackupResult result={createResult} />

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Backup records</h2>
            <p className="muted">Newest backups are shown first.</p>
          </div>
          <button type="button" onClick={refreshBackupList} disabled={listLoading}>
            {listLoading ? "Refreshing..." : "Refresh list"}
          </button>
        </div>
        <BackupTable
          backups={backups}
          detailBusy={detailBusy}
          verifyBusy={verifyBusy}
          onDetail={loadBackupDetail}
          onVerify={runVerifyBackup}
          onUseForRestore={(backupId) => setRestoreBackupId(backupId)}
        />
      </section>

      <div className="two-column">
        <BackupDetailResult result={detailResult} />
        <BackupVerifyResult result={verifyResult} />
      </div>

      <RestorePreviewResult
        result={restorePreviewResult}
        blockingRisks={restoreBlockingRisks}
        wouldOverwrite={restoreWouldOverwrite}
      />

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Restore to new inspection location</h2>
            <p className="summary-text">
              This action requires an accepted preview for the same backup ID and
              target paths.
            </p>
          </div>
        </div>
        {!restorePreviewResult && (
          <p className="muted">Run restore preview before this action is available.</p>
        )}
        {restoreWouldOverwrite && (
          <p className="error-text">
            The preview reports existing target files. Choose an empty target and run
            preview again.
          </p>
        )}
        {restoreBlockingRisks.length > 0 && (
          <p className="error-text">
            The preview has blocking schema or version risks. Review the backup before
            restoring to an inspection location.
          </p>
        )}
        {restorePreviewResult && !acceptedPreview && !restoreWouldOverwrite && (
          <button
            type="button"
            disabled={!canAcceptRestorePreview}
            onClick={acceptRestorePreview}
          >
            Accept preview for inspection restore
          </button>
        )}
        <button type="button" disabled={!canRunRestore} onClick={runRestoreToNewLocation}>
          {restoreBusy === "restore"
            ? "Restoring..."
            : "Restore to new inspection location"}
        </button>
        <RestoreResult result={restoreResult} />
      </section>
    </section>
  );
}

function BackupPreviewResult({ result }: { result: BackupPreviewResponse | null }) {
  if (!result) {
    return null;
  }
  return (
    <section className="panel">
      <h2>Backup preview result</h2>
      <dl className="detail-list">
        <div>
          <dt>DB path</dt>
          <dd className="mono-cell">{result.source.db_path}</dd>
        </div>
        <div>
          <dt>Data dir</dt>
          <dd className="mono-cell">{result.source.data_dir}</dd>
        </div>
        <div>
          <dt>Proof packets</dt>
          <dd className="mono-cell">{result.source.proof_packets_dir}</dd>
        </div>
        <div>
          <dt>Would create Case</dt>
          <dd>{result.would_create_case ? "yes" : "no"}</dd>
        </div>
      </dl>
      <PlannedBackupFilesTable files={result.planned_files} />
      <WarningList warnings={result.warnings} emptyText="No backup preview warnings." />
    </section>
  );
}

function CreateBackupResult({ result }: { result: BackupCreateResponse | null }) {
  if (!result) return null;
  return (
    <section className="panel">
      <h2>Created backup</h2>
      <dl className="detail-list">
        <div>
          <dt>Backup ID</dt>
          <dd className="mono-cell">{result.backup_id}</dd>
        </div>
        <div>
          <dt>Case</dt>
          <dd>{caseLink(result.case_id)}</dd>
        </div>
        <div>
          <dt>Archive</dt>
          <dd className="mono-cell">{result.archive_path}</dd>
        </div>
        <div>
          <dt>Manifest</dt>
          <dd className="mono-cell">{result.manifest_path}</dd>
        </div>
        <div>
          <dt>Manifest SHA-256</dt>
          <dd className="mono-cell">{result.manifest_sha256}</dd>
        </div>
        <div>
          <dt>Archive SHA-256</dt>
          <dd className="mono-cell">{result.archive_sha256}</dd>
        </div>
      </dl>
      <WarningList warnings={result.warnings} emptyText="No backup creation warnings." />
    </section>
  );
}

function BackupTable({
  backups,
  detailBusy,
  verifyBusy,
  onDetail,
  onVerify,
  onUseForRestore,
}: {
  backups: BackupListItem[];
  detailBusy: string | null;
  verifyBusy: string | null;
  onDetail: (backupId: string) => void;
  onVerify: (backupId: string) => void;
  onUseForRestore: (backupId: string) => void;
}) {
  if (backups.length === 0) {
    return <p className="muted">No managed backups recorded yet.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Backup ID</th>
            <th>Status</th>
            <th>Created</th>
            <th>Verified</th>
            <th>Archive</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {backups.map((backup) => (
            <tr key={backup.backup_id}>
              <td className="mono-cell">{backup.backup_id}</td>
              <td>
                <span className={statusClass(backup.status)}>{backup.status}</span>
              </td>
              <td>{backup.created_at}</td>
              <td>{backup.verified_at ?? "not verified"}</td>
              <td className="mono-cell">{backup.archive_path}</td>
              <td>
                <div className="action-buttons">
                  <button
                    type="button"
                    disabled={detailBusy !== null || verifyBusy !== null}
                    onClick={() => onDetail(backup.backup_id)}
                  >
                    {detailBusy === backup.backup_id ? "Loading..." : "Details"}
                  </button>
                  <button
                    type="button"
                    disabled={detailBusy !== null || verifyBusy !== null}
                    onClick={() => onVerify(backup.backup_id)}
                  >
                    {verifyBusy === backup.backup_id ? "Verifying..." : "Verify"}
                  </button>
                  <button type="button" onClick={() => onUseForRestore(backup.backup_id)}>
                    Use for restore preview
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BackupDetailResult({ result }: { result: BackupDetailResponse | null }) {
  if (!result) {
    return (
      <section className="panel">
        <h2>Backup detail</h2>
        <p className="muted">Select Details on a backup record.</p>
      </section>
    );
  }
  return (
    <section className="panel">
      <h2>Backup detail</h2>
      <dl className="detail-list">
        <div>
          <dt>Backup ID</dt>
          <dd className="mono-cell">{result.backup_id}</dd>
        </div>
        <div>
          <dt>Case</dt>
          <dd>{caseLink(result.case_id)}</dd>
        </div>
        <div>
          <dt>Archive</dt>
          <dd className="mono-cell">{result.archive_path}</dd>
        </div>
        <div>
          <dt>Verification</dt>
          <dd>
            <span className={statusClass(result.verification.status)}>
              {result.verification.status}
            </span>
          </dd>
        </div>
        <div>
          <dt>Verified at</dt>
          <dd>{result.verification.verified_at ?? "not verified"}</dd>
        </div>
        <div>
          <dt>Manifest version</dt>
          <dd>{result.manifest?.manifest_version ?? "not recorded"}</dd>
        </div>
        <div>
          <dt>App version</dt>
          <dd>{result.manifest?.app_version ?? "not recorded"}</dd>
        </div>
        <div>
          <dt>Schema version</dt>
          <dd>{result.manifest?.schema_version ?? "not recorded"}</dd>
        </div>
      </dl>
      <StringList
        title="Verification errors"
        items={result.verification.errors}
        emptyText="No verification errors recorded."
      />
      <WarningList warnings={result.warnings} emptyText="No backup detail warnings." />
    </section>
  );
}

function BackupVerifyResult({ result }: { result: BackupVerifyResponse | null }) {
  if (!result) {
    return (
      <section className="panel">
        <h2>Verify result</h2>
        <p className="muted">Run Verify on a backup record.</p>
      </section>
    );
  }
  return (
    <section className="panel">
      <h2>Verify result</h2>
      <dl className="detail-list">
        <div>
          <dt>Backup ID</dt>
          <dd className="mono-cell">{result.backup_id}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>
            <span className={statusClass(result.status)}>{result.status}</span>
          </dd>
        </div>
        <div>
          <dt>Checked files</dt>
          <dd>{result.checked_files}</dd>
        </div>
        <div>
          <dt>Case</dt>
          <dd>{caseLink(result.case_id)}</dd>
        </div>
      </dl>
      <HashMismatchTable mismatches={result.hash_mismatches} />
      <StringList
        title="Missing files"
        items={result.missing_files}
        emptyText="No missing files."
      />
      <WarningList warnings={result.warnings} emptyText="No verify warnings." />
    </section>
  );
}

function RestorePreviewResult({
  result,
  blockingRisks,
  wouldOverwrite,
}: {
  result: RestorePreviewResponse | null;
  blockingRisks: RestoreRisk[];
  wouldOverwrite: boolean;
}) {
  if (!result) return null;
  return (
    <section className="panel">
      <h2>Restore preview result</h2>
      <dl className="detail-list">
        <div>
          <dt>Preview ID</dt>
          <dd className="mono-cell">{result.restore_preview_id}</dd>
        </div>
        <div>
          <dt>Plan hash</dt>
          <dd className="mono-cell">{result.plan_hash}</dd>
        </div>
        <div>
          <dt>Backup ID</dt>
          <dd className="mono-cell">{result.backup_id}</dd>
        </div>
        <div>
          <dt>Verified</dt>
          <dd>{result.verified ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>Target DB</dt>
          <dd className="mono-cell">{result.target.db_path}</dd>
        </div>
        <div>
          <dt>Target data</dt>
          <dd className="mono-cell">{result.target.data_dir}</dd>
        </div>
      </dl>
      {wouldOverwrite && (
        <p className="error-text">
          Existing target files were detected in preview. This UI does not continue
          when overwrite would occur.
        </p>
      )}
      {blockingRisks.length > 0 && (
        <p className="error-text">Blocking restore risks must be resolved first.</p>
      )}
      <RestoreWritesTable writes={result.planned_writes} />
      <RiskList title="Schema risks" risks={result.schema_risks} />
      <RiskList title="Version risks" risks={result.version_risks} />
      <WarningList warnings={result.warnings} emptyText="No restore preview warnings." />
    </section>
  );
}

function RestoreResult({ result }: { result: RestoreToNewLocationResponse | null }) {
  if (!result) return null;
  return (
    <div className="result-block">
      <h3>Inspection restore result</h3>
      <dl className="detail-list compact-detail">
        <div>
          <dt>Status</dt>
          <dd>
            <span className="status-pill ok">{result.status}</span>
          </dd>
        </div>
        <div>
          <dt>Restored files</dt>
          <dd>{result.restored_files}</dd>
        </div>
        <div>
          <dt>Preview ID</dt>
          <dd className="mono-cell">{result.restore_preview_id}</dd>
        </div>
        <div>
          <dt>Target DB</dt>
          <dd className="mono-cell">{result.target.db_path}</dd>
        </div>
        <div>
          <dt>Target data</dt>
          <dd className="mono-cell">{result.target.data_dir}</dd>
        </div>
      </dl>
      <WarningList warnings={result.warnings} emptyText="No inspection restore warnings." />
    </div>
  );
}

function PlannedBackupFilesTable({ files }: { files: PlannedBackupFile[] }) {
  if (files.length === 0) {
    return <p className="muted">No files planned for backup.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Role</th>
            <th>Relative path</th>
            <th>Source path</th>
            <th>Size</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={`${file.role}:${file.relative_path}`}>
              <td>{file.role}</td>
              <td className="mono-cell">{file.relative_path}</td>
              <td className="mono-cell">{file.source_path}</td>
              <td>{formatBytes(file.size_bytes)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RestoreWritesTable({ writes }: { writes: RestorePlannedWrite[] }) {
  if (writes.length === 0) {
    return <p className="muted">No restore writes planned.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Archive path</th>
            <th>Target path</th>
            <th>Role</th>
            <th>Action</th>
            <th>Overwrite</th>
            <th>Size</th>
            <th>SHA-256</th>
          </tr>
        </thead>
        <tbody>
          {writes.map((write) => (
            <tr key={`${write.archive_relative_path}:${write.target_path}`}>
              <td className="mono-cell">{write.archive_relative_path}</td>
              <td className="mono-cell">{write.target_path}</td>
              <td>{write.role}</td>
              <td>{write.action}</td>
              <td>{write.would_overwrite ? "yes" : "no"}</td>
              <td>{formatBytes(write.size_bytes)}</td>
              <td className="mono-cell">{write.sha256}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HashMismatchTable({ mismatches }: { mismatches: BackupVerifyResponse["hash_mismatches"] }) {
  if (mismatches.length === 0) {
    return <p className="muted">No hash mismatches.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Relative path</th>
            <th>Expected</th>
            <th>Actual</th>
          </tr>
        </thead>
        <tbody>
          {mismatches.map((mismatch) => (
            <tr key={mismatch.relative_path}>
              <td className="mono-cell">{mismatch.relative_path}</td>
              <td className="mono-cell">{mismatch.expected_sha256 ?? "not recorded"}</td>
              <td className="mono-cell">{mismatch.actual_sha256 ?? "not recorded"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiskList({ title, risks }: { title: string; risks: RestoreRisk[] }) {
  return (
    <StringList
      title={title}
      items={risks.map((risk) =>
        `${risk.blocking ? "blocking" : "review"}: ${risk.code} - ${risk.message}`,
      )}
      emptyText={`No ${title.toLowerCase()}.`}
    />
  );
}

function WarningList({
  warnings,
  emptyText,
}: {
  warnings: string[];
  emptyText: string;
}) {
  return <StringList title="Warnings" items={warnings} emptyText={emptyText} />;
}

function StringList({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div className="result-block">
      <h3>{title}</h3>
      {items.length === 0 ? (
        <p className="muted">{emptyText}</p>
      ) : (
        <ul className="compact-list">
          {items.map((item, index) => (
            <li key={`${title}-${item}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function sortBackups(backups: BackupListItem[]): BackupListItem[] {
  return [...backups].sort((left, right) =>
    right.created_at.localeCompare(left.created_at),
  );
}

function statusClass(status: string): string {
  return status === "verified" || status === "restored_to_new_location"
    ? "status-pill ok"
    : "status-pill";
}

function caseLink(caseId: string | null) {
  if (!caseId) return "not recorded";
  return (
    <Link className="mono-cell" to={`/cases/${caseId}`}>
      {caseId}
    </Link>
  );
}

function formatBytes(sizeBytes: number): string {
  return `${sizeBytes.toLocaleString()} B`;
}
