# Reset And Backup

This repository is local-first. Reset and backup operations should stay on the
local machine and should be previewed before anything destructive runs.

## What to back up

Back up these paths before resetting local state:

- SQLite database: `PROOFFLOW_DB_PATH`, or `backend\data\proofflow.db` by
  default.
- Data directory: `PROOFFLOW_DATA_DIR`, or `backend\data` by default.
- Proof packets: `proof_packets` under the configured data directory.

## Backup command

PowerShell example:

```powershell
$repo = "D:\ProofFlow v0.1"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $env:USERPROFILE "ProofFlow-backups"
$backupDir = Join-Path $backupRoot $stamp
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$dbPath = Join-Path $repo "backend\data\proofflow.db"
$dataDir = Join-Path $repo "backend\data"

if (Test-Path -LiteralPath $dbPath) {
  Copy-Item -LiteralPath $dbPath -Destination (Join-Path $backupDir "proofflow.db") -Force
}

if (Test-Path -LiteralPath $dataDir) {
  Copy-Item -LiteralPath $dataDir -Destination (Join-Path $backupDir "data") -Recurse -Force
}

Write-Host "Backup written to $backupDir"
```

## Reset preview

Preview reset targets first:

```powershell
$repo = "D:\ProofFlow v0.1"
$targets = @(
  (Join-Path $repo "backend\data\proofflow.db"),
  (Join-Path $repo "backend\data\proof_packets")
)

$targets | ForEach-Object {
  if (Test-Path -LiteralPath $_) {
    Get-Item -LiteralPath $_
  }
}
```

Only run destructive commands after a backup exists and the human has approved
the exact targets.

## Reset command

PowerShell example after approval:

```powershell
$repo = "D:\ProofFlow v0.1"
$dbPath = Join-Path $repo "backend\data\proofflow.db"
$proofPackets = Join-Path $repo "backend\data\proof_packets"

if (Test-Path -LiteralPath $dbPath) {
  Remove-Item -LiteralPath $dbPath
}

if (Test-Path -LiteralPath $proofPackets) {
  Remove-Item -LiteralPath $proofPackets -Recurse
}
```

## Restore command

PowerShell example:

```powershell
$repo = "D:\ProofFlow v0.1"
$backupDir = "$env:USERPROFILE\ProofFlow-backups\YYYYMMDD-HHMMSS"
$dataDir = Join-Path $repo "backend\data"

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
Copy-Item -LiteralPath (Join-Path $backupDir "proofflow.db") -Destination (Join-Path $dataDir "proofflow.db") -Force

if (Test-Path -LiteralPath (Join-Path $backupDir "data\proof_packets")) {
  Copy-Item -LiteralPath (Join-Path $backupDir "data\proof_packets") -Destination (Join-Path $dataDir "proof_packets") -Recurse -Force
}
```

## Demo seed reset

`python .\scripts\demo_seed.py` resets only the guarded demo paths under
`backend\data\demo`, `sample_data\work`, and `sample_data\repos\demo-agentguard`.
The script rejects reset paths outside those demo roots.

