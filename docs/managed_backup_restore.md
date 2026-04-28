# Managed Backup / Restore Foundation

## Purpose

Managed Backup / Restore Foundation protects ProofFlow's own local state and
Proof Packets. It gives a human a repeatable way to understand what would be
backed up, verify that backup by manifest and hash, and preview restore risk
before any restore action is trusted.

This is not cloud sync. It is not a full archive system for arbitrary user
source folders. LocalProof source roots remain user-owned inputs unless a later
phase explicitly adds a previewed and verified source-archive workflow.

## Foundation invariants

- No Manifest, no Backup.
- No Verify, no trusted Backup.
- No Preview, no Restore.
- No Pre-restore Backup, no destructive Restore.
- No Hash Match, no Restore.
- No Source Version, no Restore Trust.
- No Restore to live DB in foundation phase.

## Scope for foundation phase

The foundation phase defines the design and API contract for a local-only
managed backup workflow:

- Backup ProofFlow SQLite DB via a consistent snapshot.
- Backup ProofFlow-managed data directory.
- Backup proof_packets directory.
- Generate `manifest.json`.
- Verify manifest and file hashes.
- Restore preview only.
- Restore to a new location only.
- Record backup, verify, and restore-preview as Case / Artifact / Evidence /
  Decision where practical.

The backup set is limited to ProofFlow-managed state. The default roots are the
configured `PROOFFLOW_DB_PATH`, configured `PROOFFLOW_DATA_DIR`, and
`proof_packets` under that data directory.

## Explicit non-goals

- No cloud backup.
- No scheduled backup.
- No encryption.
- No multi-user access control.
- No destructive live restore.
- No deletion action.
- No LocalProof source-root bulk archiving by default.
- No RAG / ComfyUI / plugin work.
- No Docker.
- No cloud sync.
- No automatic AI code edits.

## Data model

Every backup archive has a manifest. The manifest is the source of truth for
what the backup claims to contain, what app/schema version created it, and which
hashes must match before the backup can be trusted.

Required manifest fields:

- `manifest_version`: version of this manifest contract.
- `app_name`: expected to be `ProofFlow`.
- `app_version`: release/version string from the running app.
- `schema_version`: database schema version or migration marker known at backup
  time.
- `created_at`: UTC timestamp for manifest creation.
- `backup_id`: stable backup identifier.
- `source.db_path`: source SQLite database path.
- `source.data_dir`: source ProofFlow data directory.
- `source.proof_packets_dir`: source Proof Packet directory.
- `files[]`: every backed-up file with role, relative path, size, hash, and
  modification time.
- `archive.format`: archive format, for example `zip`.
- `archive.sha256`: archive hash after the archive is finalized.
- `archive.size_bytes`: archive size after the archive is finalized.
- `warnings[]`: non-fatal issues that reduce confidence or require review.

Example:

```json
{
  "manifest_version": "1",
  "app_name": "ProofFlow",
  "app_version": "0.1.0-rc1",
  "schema_version": "v0.1",
  "created_at": "2026-04-27T00:00:00Z",
  "backup_id": "backup_20260427_000000",
  "source": {
    "db_path": "<repo>/backend/data/proofflow.db",
    "data_dir": "<repo>/backend/data",
    "proof_packets_dir": "<repo>/backend/data/proof_packets"
  },
  "files": [
    {
      "role": "sqlite_db",
      "relative_path": "db/proofflow.db",
      "size_bytes": 40960,
      "sha256": "example-db-sha256",
      "mtime": "2026-04-27T00:00:00Z"
    },
    {
      "role": "proof_packet",
      "relative_path": "proof_packets/case-1.md",
      "size_bytes": 2048,
      "sha256": "example-packet-sha256",
      "mtime": "2026-04-27T00:00:00Z"
    }
  ],
  "archive": {
    "format": "zip",
    "sha256": "example-archive-sha256",
    "size_bytes": 65536
  },
  "warnings": []
}
```

## Safety model

- The backup archive must not include arbitrary LocalProof source roots by
  default.
- LocalProof source roots are not bulk archived by default.
- Backup traversal must not follow symlinks outside allowed ProofFlow-managed
  roots.
- Backup creation must write a manifest before the archive is trusted.
- Verification must recompute file and archive hashes from disk.
- Restore preview must show overwrites and schema/version risks.
- Restore preview must compare the manifest `app_version` and `schema_version`
  against the current runtime before any trust decision.
- Foundation restore writes only to a new location.
- Foundation phase does not restore into the live DB.
- Live restore is deferred until a later phase and must require a pre-restore
  backup.

## API contract and implementation status

Phase 2 implements the backup endpoints: preview, create, list, detail, and
verify. Restore endpoints remain proposed only for later phases and are not
exposed by the Phase 2 backend.

### POST /backups/preview

Purpose: show the backup plan before writing an archive.

Request shape:

```json
{
  "backup_root": "<local-backup-root>",
  "include_data_dir": true,
  "include_proof_packets": true
}
```

Response shape:

```json
{
  "source": {
    "db_path": "<db-path>",
    "data_dir": "<data-dir>",
    "proof_packets_dir": "<proof-packets-dir>"
  },
  "planned_files": [
    {
      "role": "sqlite_db",
      "relative_path": "db/proofflow.db",
      "size_bytes": 40960,
      "source_path": "<db-path>"
    }
  ],
  "warnings": [],
  "would_create_case": true
}
```

Safety notes: preview must not write the archive. It must flag missing DB/data
paths, symlink escapes, and LocalProof source roots that are outside the managed
state boundary.

Case / Artifact / Evidence: Phase 2 keeps preview read-only. It does not create
a Case, Artifact, Evidence, backup directory, archive, manifest, or DB row.

### POST /backups

Purpose: create a managed local backup archive and `manifest.json`.

Request shape:

```json
{
  "backup_root": "<local-backup-root>",
  "label": "before-upgrade"
}
```

Response shape:

```json
{
  "backup_id": "backup_20260427_000000",
  "case_id": "case-id",
  "archive_path": "<backup-root>/backup_20260427_000000.zip",
  "manifest_path": "<backup-root>/backup_20260427_000000.manifest.json",
  "manifest_sha256": "manifest-sha256",
  "archive_sha256": "archive-sha256",
  "warnings": []
}
```

Safety notes: creation must use a consistent SQLite snapshot and must write
only under the requested local backup root. The backup is not trusted until
`POST /backups/{backup_id}/verify` succeeds.

Case / Artifact / Evidence: creates a Case where practical. The archive and
manifest are Artifacts. The creation log is Evidence for the backup attempt,
not proof that the backup is trusted.

### GET /backups

Purpose: list known backup records from ProofFlow metadata.

Request shape: none.

Response shape:

```json
{
  "backups": [
    {
      "backup_id": "backup_20260427_000000",
      "created_at": "2026-04-27T00:00:00Z",
      "status": "created",
      "verified_at": null,
      "archive_path": "<backup-root>/backup_20260427_000000.zip"
    }
  ]
}
```

Safety notes: listing must not scan arbitrary directories by default. It should
read only ProofFlow's recorded backup metadata.

Case / Artifact / Evidence: does not create new records.

### GET /backups/{backup_id}

Purpose: show one backup record, its manifest summary, verification status, and
warnings.

Request shape: path parameter `backup_id`.

Response shape:

```json
{
  "backup_id": "backup_20260427_000000",
  "case_id": "case-id",
  "manifest": {
    "manifest_version": "1",
    "app_version": "0.1.0-rc1",
    "schema_version": "v0.1"
  },
  "archive_path": "<backup-root>/backup_20260427_000000.zip",
  "verification": {
    "status": "not_verified",
    "verified_at": null,
    "errors": []
  },
  "warnings": []
}
```

Safety notes: detail lookup must not trust manifest claims unless the manifest
and archive have been verified.

Case / Artifact / Evidence: does not create new records.

### POST /backups/{backup_id}/verify

Purpose: verify manifest completeness and file/archive hash matches.

Request shape:

```json
{
  "recompute_archive_hash": true,
  "recompute_file_hashes": true
}
```

Response shape:

```json
{
  "backup_id": "backup_20260427_000000",
  "case_id": "case-id",
  "status": "verified",
  "checked_files": 2,
  "hash_mismatches": [],
  "missing_files": [],
  "warnings": []
}
```

Safety notes: no hash match means no restore trust. Verification must not
silently ignore missing files, hash mismatches, or source version mismatch
warnings.

Case / Artifact / Evidence: creates Evidence for the verification report. A
Claim such as "backup is complete" is trusted only after this endpoint reports
successful hash verification.

### POST /restore/preview

Status: proposed only. This endpoint is not implemented in Phase 2.

Purpose: inspect a verified backup and show what restore would write before any
restore action.

Request shape:

```json
{
  "backup_id": "backup_20260427_000000",
  "target_db_path": "<new-location>/proofflow.db",
  "target_data_dir": "<new-location>/data"
}
```

Response shape:

```json
{
  "backup_id": "backup_20260427_000000",
  "case_id": "case-id",
  "verified": true,
  "target": {
    "db_path": "<new-location>/proofflow.db",
    "data_dir": "<new-location>/data"
  },
  "planned_writes": [
    {
      "relative_path": "proofflow.db",
      "action": "create",
      "would_overwrite": false
    }
  ],
  "schema_risks": [],
  "version_risks": [],
  "warnings": []
}
```

Safety notes: preview must not write files. It must reject or warn when the
target is the current live DB or current live data directory.

Case / Artifact / Evidence: creates Evidence for restore risk review where
practical. Restore preview is Evidence before any restore Decision.

### POST /restore/to-new-location

Status: proposed only. This endpoint is not implemented in Phase 2.

Purpose: restore a verified backup into a new DB/data location for inspection.

Request shape:

```json
{
  "backup_id": "backup_20260427_000000",
  "target_db_path": "<new-location>/proofflow.db",
  "target_data_dir": "<new-location>/data",
  "accepted_preview_id": "restore-preview-id"
}
```

Response shape:

```json
{
  "backup_id": "backup_20260427_000000",
  "case_id": "case-id",
  "target": {
    "db_path": "<new-location>/proofflow.db",
    "data_dir": "<new-location>/data"
  },
  "restored_files": 2,
  "status": "restored_to_new_location",
  "warnings": []
}
```

Safety notes: foundation restore writes only to a new location. It must require
a prior successful verify result, hash matches, source version metadata, and an
accepted restore preview. It must not restore into the current live DB.

Case / Artifact / Evidence: records the restore target and result as Evidence.
A human Decision should accept the preview before this endpoint is called.

## Proof Packet mapping

- Backup archive is an Artifact.
- Manifest is an Artifact.
- Verification report is Evidence.
- "Backup is complete" is a Claim only trusted after hash verification.
- Restore preview is Evidence before any restore Decision.
- Restore-to-new-location output is Evidence for inspection, not proof that a
  live restore is safe.

## Phase plan

### Phase 1: design doc and contract tests

- Add this design document.
- Add lightweight tests that preserve the invariants, endpoint names, manifest
  fields, and foundation non-goals.
- Do not implement product routes in this phase.

### Phase 2: backend backup create/list/verify

- Implemented backup preview, creation, list, detail, and verify endpoints.
- Create archive and manifest Artifacts.
- Record backup creation and verification Evidence.
- Keep restore preview, restore-to-new-location, and live DB restore blocked.

### Phase 3: restore preview and restore to new location

- Implement restore preview.
- Implement restore to a new location only.
- Keep live DB restore blocked.

### Phase 4: thin UI

- Add a small UI surface for preview, create, verify, and restore-to-new-location
  flows after backend contracts are proven.

### Phase 5: optional future live restore with stricter gates

- Consider live restore only after stricter preview, pre-restore backup,
  rollback, and operator confirmation gates exist.
