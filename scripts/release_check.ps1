$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Invoke-ReleaseStep {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [string] $Path,
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    Write-Host ""
    Write-Host "==> $Name"
    Push-Location $Path
    try {
        & $Command
    }
    finally {
        Pop-Location
    }
}

Invoke-ReleaseStep -Name "Backend pytest" -Path (Join-Path $Root "backend") -Command {
    python -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "Backend pytest failed with exit code $LASTEXITCODE"
    }
}

Invoke-ReleaseStep -Name "Frontend install, test, and build" -Path (Join-Path $Root "frontend") -Command {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) {
        throw "npm ci failed with exit code $LASTEXITCODE"
    }

    npm.cmd run test
    if ($LASTEXITCODE -ne 0) {
        throw "npm run test failed with exit code $LASTEXITCODE"
    }

    npm.cmd run build
    if ($LASTEXITCODE -ne 0) {
        throw "npm run build failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "ProofFlow v0.1.0-rc1 release check passed."
