/**
 * Free the Playwright Vite port before E2E runs.
 * Windows-first: only stops listeners that look like Node/Vite/HalfApp dev servers.
 */
import { execSync } from 'child_process'

const PORT = Number(process.env.PLAYWRIGHT_PORT || 3022)
const isWin = process.platform === 'win32'

const HALFAPP_MARKERS = [
  'vite',
  'playwright',
  'halfapp-driver',
  'halfapp-driver-app',
  'npm run dev',
  'run dev',
  '@playwright/test',
  'node_modules/vite',
]

function log(msg) {
  console.log(`[playwright-port] ${msg}`)
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)
}

/** @returns {number[]} */
function getListeningPidsWindows(port) {
  const out = execSync('netstat -ano -p tcp', { encoding: 'utf8', windowsHide: true })
  const pids = new Set()
  const portPattern = new RegExp(`:${port}\\s+\\S+\\s+LISTENING\\s+(\\d+)\\s*$`, 'i')
  for (const line of out.split(/\r?\n/)) {
    const match = line.match(portPattern)
    if (match) pids.add(Number(match[1]))
  }
  return [...pids].filter((pid) => Number.isFinite(pid) && pid > 0)
}

/** @returns {{ name: string, commandLine: string } | null} */
function getProcessInfoWindows(pid) {
  try {
    const script = `(Get-CimInstance Win32_Process -Filter "ProcessId = ${pid}" | Select-Object -First 1 Name, CommandLine | ConvertTo-Json -Compress)`
    const raw = execSync(`powershell -NoProfile -Command ${JSON.stringify(script)}`, {
      encoding: 'utf8',
      windowsHide: true,
    }).trim()
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return {
      name: String(parsed.Name || ''),
      commandLine: String(parsed.CommandLine || ''),
    }
  } catch {
    return null
  }
}

/** @returns {boolean} */
function isLikelyHalfAppDevServer(name, commandLine) {
  const proc = (name || '').toLowerCase()
  const cmd = (commandLine || '').toLowerCase()

  if (HALFAPP_MARKERS.some((marker) => cmd.includes(marker))) {
    return true
  }

  if (proc === 'node.exe' || proc === 'node') {
    if (
      cmd.includes('vite') ||
      cmd.includes(`--port ${PORT}`) ||
      cmd.includes(`--port=${PORT}`) ||
      cmd.includes(`:${PORT}`)
    ) {
      return true
    }
  }

  if (proc === 'cmd.exe' || proc === 'powershell.exe') {
    if (cmd.includes('npm') && (cmd.includes('dev') || cmd.includes('vite'))) {
      return true
    }
  }

  return false
}

function killProcessWindows(pid) {
  execSync(`taskkill /PID ${pid} /F /T`, { encoding: 'utf8', windowsHide: true })
}

/** @returns {number[]} */
function getListeningPidsUnix(port) {
  try {
    const out = execSync(`lsof -nP -iTCP:${port} -sTCP:LISTEN -t`, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'ignore'],
    }).trim()
    if (!out) return []
    return out
      .split(/\r?\n/)
      .map((line) => Number(line.trim()))
      .filter((pid) => Number.isFinite(pid) && pid > 0)
  } catch {
    return []
  }
}

/** @returns {{ name: string, commandLine: string } | null} */
function getProcessInfoUnix(pid) {
  try {
    const out = execSync(`ps -p ${pid} -o comm=,args=`, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'ignore'],
    }).trim()
    if (!out) return null
    const space = out.indexOf(' ')
    if (space === -1) return { name: out, commandLine: out }
    return { name: out.slice(0, space), commandLine: out.slice(space + 1) }
  } catch {
    return null
  }
}

function killProcessUnix(pid) {
  execSync(`kill -9 ${pid}`, { stdio: 'ignore' })
}

function getListeningPids(port) {
  return isWin ? getListeningPidsWindows(port) : getListeningPidsUnix(port)
}

function getProcessInfo(pid) {
  return isWin ? getProcessInfoWindows(pid) : getProcessInfoUnix(pid)
}

function killProcess(pid) {
  if (isWin) killProcessWindows(pid)
  else killProcessUnix(pid)
}

function portIsFree(port) {
  return getListeningPids(port).length === 0
}

function describeProcess(pid) {
  const info = getProcessInfo(pid)
  if (!info) return `PID ${pid} (command line unavailable)`
  const cmd = info.commandLine.length > 160 ? `${info.commandLine.slice(0, 160)}…` : info.commandLine
  return `PID ${pid} (${info.name}) — ${cmd || '(no command line)'}`
}

function main() {
  log(`Checking port ${PORT}…`)

  if (portIsFree(PORT)) {
    log(`Port ${PORT} is free.`)
    process.exit(0)
  }

  const pids = getListeningPids(PORT)
  log(`Port ${PORT} is in use by: ${pids.join(', ')}`)

  for (const pid of pids) {
    const info = getProcessInfo(pid)
    const name = info?.name ?? ''
    const commandLine = info?.commandLine ?? ''

    if (!isLikelyHalfAppDevServer(name, commandLine)) {
      console.error(
        `[playwright-port] Refusing to kill non-HalfApp process on port ${PORT}:\n  ${describeProcess(pid)}\n` +
          'Stop that process manually, or set PLAYWRIGHT_PORT to a different free port.',
      )
      process.exit(1)
    }

    log(`Stopping HalfApp/Vite dev listener: ${describeProcess(pid)}`)
    try {
      killProcess(pid)
    } catch (err) {
      console.error(`[playwright-port] Failed to stop PID ${pid}: ${err?.message || err}`)
      process.exit(1)
    }
  }

  for (let attempt = 0; attempt < 10; attempt += 1) {
    if (portIsFree(PORT)) {
      log(`Port ${PORT} is now free.`)
      process.exit(0)
    }
    sleep(200)
  }

  console.error(`[playwright-port] Port ${PORT} is still in use after stopping dev listeners.`)
  process.exit(1)
}

main()
