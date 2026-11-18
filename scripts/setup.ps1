$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot "backend\.venv"
$python = Join-Path $venvPath "Scripts\python.exe"
$env:UV_CACHE_DIR = Join-Path $projectRoot ".cache\uv"

$nodeVersion = (& node --version).TrimStart("v")
$nodeParts = $nodeVersion.Split(".")
if ([int]$nodeParts[0] -lt 24) {
    throw "PokerHelper's primary frontend toolchain requires Node.js 24 LTS. Found $nodeVersion."
}

if (-not (Test-Path $python)) {
    python -m venv $venvPath
}

& $python -m pip install "uv==0.13.9"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$uv = Join-Path $venvPath "Scripts\uv.exe"
& $uv sync --project (Join-Path $projectRoot "backend") --extra dev --locked
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location (Join-Path $projectRoot "frontend")
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

Write-Host "PokerHelper is ready. Run .\scripts\start.ps1" -ForegroundColor Green
