# HalfApp Playwright Port Preflight

Date: 2026-05-22  
Order: `HALFAPP_PLAYWRIGHT_PORT_PREFLIGHT_01`

## Problem

Playwright starts its own Vite dev server on port **3022** (`playwright.config.js`, `reuseExistingServer: false`). If a previous `npm run dev` (or another Node/Vite HalfApp session) is still listening, Playwright fails with:

```txt
Error: http://127.0.0.1:3022 is already used
```

## Solution

Before targeted cockpit E2E runs, `scripts/ensure-playwright-port-free.mjs`:

1. Detects listeners on `PLAYWRIGHT_PORT` (default `3022`).
2. If free → prints `Port 3022 is free.` and exits `0`.
3. If occupied → reads process name/command line (Windows: `netstat` + PowerShell `Win32_Process`; Unix: `lsof` + `ps`).
4. Kills **only** when the listener looks like Node/Vite/HalfApp dev (`vite`, `halfapp-driver`, `npm run dev`, `--port 3022`, etc.).
5. Refuses to kill unknown processes with a clear error and exit `1`.
6. Waits until the port is free (or fails after retries).

## User command

From `driver-app/`:

```powershell
npm run test:e2e:cockpit
```

Runs preflight via npm `pretest:e2e:cockpit`, then:

```txt
tests/smoke-mvp.spec.ts
tests/cockpit-identity.spec.ts
tests/map-cockpit-truth.spec.ts
```

Override port:

```powershell
$env:PLAYWRIGHT_PORT=3023; npm run test:e2e:cockpit
```

## Safety

- Does **not** kill unrelated apps (browsers, databases, other services) unless their command line matches HalfApp/Vite dev heuristics.
- Uses `taskkill /PID … /F /T` on Windows only for approved listeners.

## Files

| File | Role |
|------|------|
| `driver-app/scripts/ensure-playwright-port-free.mjs` | Preflight |
| `driver-app/package.json` | `pretest:e2e:cockpit` + `test:e2e:cockpit` |
| `driver-app/playwright.config.js` | Port and `webServer` |

No product UI or backend behavior changes in this slice.
