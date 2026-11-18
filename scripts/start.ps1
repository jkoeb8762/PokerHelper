$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$frontend = Join-Path $projectRoot "frontend\dist\index.html"
$dataDir = Join-Path $projectRoot "data"
$url = "http://127.0.0.1:8000"

if (-not (Test-Path $python) -or -not (Test-Path $frontend)) {
    throw "PokerHelper is not prepared. Run .\scripts\setup.ps1 first."
}

$server = Start-Process -FilePath $python `
    -ArgumentList @("-m", "pokerhelper", "serve", "--data-dir", $dataDir) `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($server.HasExited) {
            throw "The local server stopped before it became ready."
        }
        try {
            $response = Invoke-RestMethod -Uri "$url/api/v1/health" -TimeoutSec 1
            if ($response.status -eq "ok") {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $ready) { throw "The local server did not become ready within 10 seconds." }
    Write-Host "PokerHelper is running at $url. Press Ctrl+C to stop." -ForegroundColor Green
    Start-Process $url
    Wait-Process -Id $server.Id
}
finally {
    if (-not $server.HasExited) {
        Stop-Process -Id $server.Id
    }
}
