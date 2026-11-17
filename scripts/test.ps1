$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "backend\src"
python -m unittest discover -s (Join-Path $projectRoot "backend\tests") -p "test_*.py" -v

