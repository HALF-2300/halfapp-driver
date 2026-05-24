# OSRM healthcheck (ops-only, Slice 05). Exits non-zero on failure.
# Requires: OSRM_BASE_URL (e.g. http://127.0.0.1:5000)
# Hits canonical Route API: /route/v1/driving/{lon,lat;lon,lat}

$ErrorActionPreference = "Stop"

$base = $env:OSRM_BASE_URL
if (-not $base) {
  Write-Host "FAIL: OSRM_BASE_URL not set"
  exit 2
}

$base = $base.TrimEnd("/")
# Portland metro leg (matches docker/osrm-portland README + verify_osrm_health.py)
$u = "$base/route/v1/driving/-122.5951,45.5898;-122.6784,45.5152?overview=false&steps=false"

try {
  $r = Invoke-WebRequest -Uri $u -TimeoutSec 10 -UseBasicParsing
  if ($r.StatusCode -ne 200) {
    Write-Host "FAIL: HTTP $($r.StatusCode)"
    exit 1
  }

  $json = $r.Content | ConvertFrom-Json
  if ($json.code -ne "Ok") {
    Write-Host "FAIL: OSRM code=$($json.code)"
    exit 1
  }

  if (-not $json.routes -or $json.routes.Count -lt 1) {
    Write-Host "FAIL: no routes"
    exit 1
  }

  $dist = [int]$json.routes[0].distance
  if ($dist -le 0) {
    Write-Host "FAIL: non-positive distance ($dist)"
    exit 1
  }

  Write-Host "OK: routes[0].distance=$dist"
  exit 0
}
catch {
  Write-Host "FAIL: $($_.Exception.Message)"
  exit 1
}
