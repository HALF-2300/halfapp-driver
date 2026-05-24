# Run HalfApp driver stack in DEV (backend + driver-app).
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1 -RealBackend
#
# Ports (repo defaults):
#   Backend:  http://127.0.0.1:8000  (uvicorn main:app from backend/)
#   Frontend: http://127.0.0.1:3022  (vite.config.js strictPort)

param(
  [switch]$RealBackend
)

$ErrorActionPreference = "Stop"

$BackendPort = 8000
$FrontendPort = 3022
$BackendHost = "127.0.0.1"
$ApiBase = "http://${BackendHost}:${BackendPort}"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Write-Host "Repo root: $root"

$backend = Join-Path $root "backend"
$frontend = Join-Path $root "driver-app"

if (!(Test-Path $backend)) { throw "backend folder not found: $backend" }
if (!(Test-Path $frontend)) { throw "driver-app folder not found: $frontend" }

# --- Backend: migrate + uvicorn (reload) ---
Write-Host "== Backend: alembic upgrade head + uvicorn =="

Push-Location $backend
try {
  py -3.11 -m alembic upgrade head
}
catch {
  Pop-Location
  throw "Alembic failed. Activate venv or install Python 3.11 + requirements.txt"
}

$uvicornArgs = @(
  "-3.11", "-m", "uvicorn", "main:app",
  "--host", $BackendHost,
  "--port", "$BackendPort",
  "--reload"
)

Start-Process -FilePath "py" -ArgumentList $uvicornArgs -WorkingDirectory $backend
Pop-Location

# --- Frontend: npm install (if needed) + Vite dev ---
Write-Host "== Driver app: npm run dev =="

$env:VITE_API_BASE = $ApiBase
if ($RealBackend) {
  $env:VITE_ALLOW_OFFLINE_MOCK = "false"
  Write-Host "RealBackend: VITE_ALLOW_OFFLINE_MOCK=false (API calls hit $ApiBase)"
}
else {
  Write-Host "Default dev: .env.development may keep VITE_ALLOW_OFFLINE_MOCK=true for offline demo."
  Write-Host "Use -RealBackend to force live API against $ApiBase"
}

Push-Location $frontend
if (!(Test-Path (Join-Path $frontend "node_modules"))) {
  npm install
}

Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "npm", "run", "dev") -WorkingDirectory $frontend
Pop-Location

Write-Host ""
Write-Host "DEV started (new windows):"
Write-Host "- Backend:  $ApiBase  (health: $ApiBase/health)"
Write-Host "- Driver app: http://${BackendHost}:${FrontendPort}/"
Write-Host ""
Write-Host "Copy env templates if missing:"
Write-Host "  backend\.env.example -> backend\.env"
Write-Host "  driver-app\.env.example -> driver-app\.env"
