CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    case_type TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    uri TEXT NOT NULL,
    name TEXT NOT NULL,
    mime_type TEXT,
    sha256 TEXT,
    size_bytes INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_artifacts (
    case_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (case_id, artifact_id),
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS artifact_text_chunks (
    id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
    UNIQUE (artifact_id, chunk_index)
);

CREATE VIRTUAL TABLE IF NOT EXISTS artifact_text_fts USING fts5(
    content,
    artifact_id UNINDEXED,
    chunk_index UNINDEXED,
    content='artifact_text_chunks',
    content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    run_id TEXT,
    claim_text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    artifact_id TEXT,
    claim_id TEXT,
    evidence_type TEXT NOT NULL,
    content TEXT NOT NULL,
    source_ref TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE SET NULL,
    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    run_id TEXT,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    preview_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT,
    undo_json TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    rationale TEXT NOT NULL,
    result TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS backups (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    label TEXT,
    status TEXT NOT NULL,
    archive_path TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    manifest_sha256 TEXT,
    archive_sha256 TEXT,
    archive_size_bytes INTEGER,
    file_count INTEGER,
    verified_at TEXT,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS restore_previews (
    id TEXT PRIMARY KEY,
    backup_id TEXT NOT NULL,
    case_id TEXT,
    target_db_path TEXT NOT NULL,
    target_data_dir TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    archive_sha256 TEXT,
    manifest_sha256 TEXT,
    planned_writes_json TEXT NOT NULL,
    schema_risks_json TEXT NOT NULL DEFAULT '[]',
    version_risks_json TEXT NOT NULL DEFAULT '[]',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (backup_id) REFERENCES backups(id) ON DELETE CASCADE,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
);
