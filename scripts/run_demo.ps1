# Runs the AI-assisted engineering demo end-to-end.
# Usage:  ./scripts/run_demo.ps1
$ErrorActionPreference = "Stop"

# Move to the repository root (parent of this script's folder).
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Installing dependencies" -ForegroundColor Cyan
python -m pip install -q -r requirements.txt

$env:PYTHONPATH = "src"
$requirement = "Build a scalable URL shortener service with APIs, persistence, and analytics"

Write-Host "`n==> Running the prototype pipeline on the mandatory requirement" -ForegroundColor Cyan
python -m ai_eng $requirement --json summary.json

Write-Host "`n==> Running the full test suite (prototype + URL shortener)" -ForegroundColor Cyan
python -m pytest -q

Write-Host "`n==> Done. See summary.json for the machine-readable engineering summary." -ForegroundColor Green
Write-Host "    Start the demo API with:  cd examples/url_shortener; uvicorn app.main:app --reload" -ForegroundColor Green
