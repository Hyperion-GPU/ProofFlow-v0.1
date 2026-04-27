# Action Safety Scope

ProofFlow v0.1 keeps filesystem actions local and scoped. A filesystem action is
any `move_file`, `rename_file`, or `mkdir_dir` action.

## Scope metadata

Every filesystem action must carry explicit `metadata.allowed_roots`.

LocalProof suggested actions also include the scan and target roots:

```json
{
  "source": "localproof_suggest_actions",
  "scope_kind": "localproof_file_cleanup",
  "source_root": "D:\\ProofFlow v0.1\\sample_data\\work\\files",
  "target_root": "D:\\ProofFlow v0.1\\sample_data\\work\\sorted",
  "allowed_roots": [
    "D:\\ProofFlow v0.1\\sample_data\\work\\files",
    "D:\\ProofFlow v0.1\\sample_data\\work\\sorted"
  ]
}
```

Manual filesystem actions may use a smaller metadata shape, but they still need
absolute local roots:

```json
{
  "scope_kind": "manual_file_cleanup",
  "allowed_roots": [
    "D:\\Users\\me\\Inbox",
    "D:\\Users\\me\\Sorted"
  ]
}
```

## Enforcement points

The backend validates scope before it stores a new filesystem action, before it
executes the action, and before it runs undo.

The scope check requires:

- preview paths are absolute local paths,
- every preview path is inside at least one `allowed_roots` entry,
- LocalProof actions include `source_root`, `target_root`, and both roots in
  `allowed_roots`,
- action paths do not touch ProofFlow's own database, data directory, or proof
  packet directory.

## Protected ProofFlow paths

Actions cannot operate on:

- the SQLite database from `PROOFFLOW_DB_PATH`, or `backend\data\proofflow.db`
  by default,
- the data directory from `PROOFFLOW_DATA_DIR`, or `backend\data` by default,
- the proof packet directory under the data directory.

This keeps LocalProof cleanup actions away from ProofFlow's own state and
generated proof packets.

## Undo hash guard

When a `move_file` or `rename_file` action executes, ProofFlow stores the moved
file's SHA-256 hash and size in the result and undo payload.

Undo refuses to move the file back if the file at the action destination no
longer matches the recorded hash. This prevents an undo from overwriting or
misplacing content that changed after execution.

## Legacy database upgrade

`init_db()` upgrades legacy filesystem actions that were created before action
safety metadata existed. When the old preview has enough path information, the
upgrade infers `allowed_roots` from the LocalProof scan folder and target root,
or from the legacy action paths for non-LocalProof actions.

If a legacy action stored relative paths, the upgrade resolves those paths
against the current process working directory, matching the old `Path(value)`
execution behavior. The migrated action stores absolute preview/result/undo
paths plus `path_migrated_from` and `legacy_relative_path_base` metadata. If a
path or scope cannot be inferred, the action is marked with migration failure
metadata instead of silently pretending it is safe.

For legacy executed `move_file` and `rename_file` actions that do not have an
undo hash guard, the upgrade records the file currently at the undo source as
the hash baseline and marks it with `hash_guard_migrated_from`. This cannot
recover a pre-upgrade hash that was never recorded, but it prevents silent
post-upgrade changes from being undone as if they were the original file.
