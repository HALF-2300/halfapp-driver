# RIDE_AI_ROUTE_GROUNDING_RUNTIME_PROOF_01 — run after OSRM is up (docker/osrm-portland).
$ErrorActionPreference = "Stop"

$env:OSRM_BASE_URL = if ($env:OSRM_BASE_URL) { $env:OSRM_BASE_URL } else { "http://127.0.0.1:5000" }
$env:ROUTING_PROVIDER = "osrm_self_hosted"
$env:HALFAPP_ENABLE_RIDE_SIMULATION = "1"
$env:ROUTING_FALLBACK_ENABLED = "true"
$env:ALLOW_TEST_USER_SEED = "1"

Write-Host "OSRM healthcheck..."
$env:OSRM_BASE_URL = $env:OSRM_BASE_URL.TrimEnd("/")
powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\osrm_healthcheck.ps1"
if ($LASTEXITCODE -ne 0) {
  Write-Host "BLOCKED: start OSRM first (cd docker/osrm-portland; docker compose up -d)"
  exit 2
}

Set-Location "$PSScriptRoot\..\backend"
py -3.11 scripts/proof_ride_ai_route_grounding_runtime.py
exit $LASTEXITCODE
