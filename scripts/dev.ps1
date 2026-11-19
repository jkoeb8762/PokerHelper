$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$dataDir = Join-Path $projectRoot "data"
$env:npm_config_cache = Join-Path $projectRoot ".cache\npm"

if (-not (Test-Path $python) -or -not (Test-Path (Join-Path $projectRoot "frontend\node_modules"))) {
    throw "PokerHelper dependencies are missing. Run .\scripts\setup.ps1 first."
}

$api = Start-Process -FilePath $python `
    -ArgumentList @("-m", "pokerhelper", "serve", "--data-dir", $dataDir, "--reload") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    Push-Location (Join-Path $projectRoot "frontend")
    npm run dev
}
finally {
    Pop-Location
    if (-not $api.HasExited) {
        Stop-Process -Id $api.Id
    }
}
