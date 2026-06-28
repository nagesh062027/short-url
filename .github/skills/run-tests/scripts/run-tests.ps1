# Runs the full test + validation flow for the project.
# Usage:  ./.github/skills/run-tests/scripts/run-tests.ps1
$ErrorActionPreference = "Stop"

# Resolve repository root (four levels up from this script).
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $root

Write-Host "==> Installing dependencies" -ForegroundColor Cyan
python -m pip install -q -r requirements.txt

Write-Host "`n==> Full test suite" -ForegroundColor Cyan
python -m pytest -q

Write-Host "`n==> Coverage" -ForegroundColor Cyan
python -m pytest --cov=ai_eng --cov=app --cov-report=term-missing

Write-Host "`n==> End-to-end quality gate" -ForegroundColor Cyan
python -m ai_eng "Build a scalable URL shortener service with APIs, persistence, and analytics" --run-tests
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nQuality gate FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "`nAll checks passed." -ForegroundColor Green
