# Full verification ritual (backend + driver-app). Exits non-zero on first failure.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1
# Optional: -SkipE2e to skip Playwright ride-flow (faster)

param(
  [switch]$SkipE2e
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "== Backend: alembic + pytest =="
Push-Location (Join-Path $root "backend")
py -3.11 -m alembic upgrade head
py -3.11 -m pytest tests -q
Pop-Location

Write-Host "== Driver app: unit tests + guards + build =="
Push-Location (Join-Path $root "driver-app")
npm test
npm run build
if (-not $SkipE2e) {
  Write-Host "== Driver app: ride-flow E2E =="
  npm run test:e2e:ride-flow
}
npm run assert-no-ai-providers
npm run assert-no-money-claims
Pop-Location

Write-Host ""
Write-Host "verify_all: OK"
