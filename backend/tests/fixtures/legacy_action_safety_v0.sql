CREATE TABLE cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    case_type TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE actions (
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
    updated_at TEXT NOT NULL
);

INSERT INTO cases (
    id, title, case_type, status, summary, metadata_json, created_at, updated_at
)
VALUES (
    'case-legacy-actions',
    'Legacy LocalProof actions',
    'file_cleanup',
    'open',
    'Fixture from before action safety metadata was required.',
    '{"folder_path":__SOURCE_ROOT_JSON__,"recursive":true,"max_files":500,"source":"localproof_scan"}',
    '2026-04-01T00:00:00Z',
    '2026-04-01T00:00:00Z'
);

INSERT INTO actions (
    id, case_id, run_id, action_type, status, description, title, reason,
    preview_json, result_json, undo_json, metadata_json, created_at, updated_at
)
VALUES (
    'legacy-approved-move',
    'case-legacy-actions',
    NULL,
    'move_file',
    'approved',
    'Move approved legacy note',
    'Move approved legacy note',
    'Created before action safety metadata existed.',
    '{"from_path":__APPROVED_SOURCE_JSON__,"to_path":__APPROVED_DEST_JSON__}',
    NULL,
    NULL,
    '{"source":"localproof_suggest_actions","artifact_id":"artifact-approved","category":"Notes","rule":"note"}',
    '2026-04-01T00:01:00Z',
    '2026-04-01T00:01:00Z'
);

INSERT INTO actions (
    id, case_id, run_id, action_type, status, description, title, reason,
    preview_json, result_json, undo_json, metadata_json, created_at, updated_at
)
VALUES (
    'legacy-executed-move',
    'case-legacy-actions',
    NULL,
    'move_file',
    'executed',
    'Move executed legacy note',
    'Move executed legacy note',
    'Executed before undo hash guards existed.',
    '{"from_path":__EXECUTED_SOURCE_JSON__,"to_path":__EXECUTED_DEST_JSON__}',
    '{"operation":"move_file","from_path":__EXECUTED_SOURCE_JSON__,"to_path":__EXECUTED_DEST_JSON__,"executed_at":"2026-04-01T00:02:00Z"}',
    '{"operation":"restore_file","from_path":__EXECUTED_DEST_JSON__,"to_path":__EXECUTED_SOURCE_JSON__,"created_at":"2026-04-01T00:02:00Z"}',
    '{"source":"localproof_suggest_actions","artifact_id":"artifact-executed","category":"Notes","rule":"note"}',
    '2026-04-01T00:02:00Z',
    '2026-04-01T00:02:00Z'
);

INSERT INTO actions (
    id, case_id, run_id, action_type, status, description, title, reason,
    preview_json, result_json, undo_json, metadata_json, created_at, updated_at
)
VALUES (
    'legacy-relative-approved-move',
    'case-legacy-actions',
    NULL,
    'move_file',
    'approved',
    'Move relative approved legacy note',
    'Move relative approved legacy note',
    'Created with relative preview paths before action safety metadata existed.',
    '{"from_path":__RELATIVE_APPROVED_SOURCE_JSON__,"to_path":__RELATIVE_APPROVED_DEST_JSON__}',
    NULL,
    NULL,
    '{"source":"localproof_suggest_actions","artifact_id":"artifact-relative-approved","category":"Notes","rule":"note"}',
    '2026-04-01T00:03:00Z',
    '2026-04-01T00:03:00Z'
);

INSERT INTO actions (
    id, case_id, run_id, action_type, status, description, title, reason,
    preview_json, result_json, undo_json, metadata_json, created_at, updated_at
)
VALUES (
    'legacy-relative-executed-move',
    'case-legacy-actions',
    NULL,
    'move_file',
    'executed',
    'Move relative executed legacy note',
    'Move relative executed legacy note',
    'Executed with relative undo paths before hash guards existed.',
    '{"from_path":__RELATIVE_EXECUTED_SOURCE_JSON__,"to_path":__RELATIVE_EXECUTED_DEST_JSON__}',
    '{"operation":"move_file","from_path":__RELATIVE_EXECUTED_SOURCE_JSON__,"to_path":__RELATIVE_EXECUTED_DEST_JSON__,"executed_at":"2026-04-01T00:04:00Z"}',
    '{"operation":"restore_file","from_path":__RELATIVE_EXECUTED_DEST_JSON__,"to_path":__RELATIVE_EXECUTED_SOURCE_JSON__,"created_at":"2026-04-01T00:04:00Z"}',
    '{"source":"localproof_suggest_actions","artifact_id":"artifact-relative-executed","category":"Notes","rule":"note"}',
    '2026-04-01T00:04:00Z',
    '2026-04-01T00:04:00Z'
);
