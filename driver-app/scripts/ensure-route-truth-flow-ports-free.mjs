/**
 * Free route-truth Playwright ports (3037 frontend, 8014 backend) before E2E.
 */
import { execSync } from 'node:child_process'

const PORTS = [
  Number(process.env.PLAYWRIGHT_ROUTE_TRUTH_FLOW_PORT || 3037),
  Number(process.env.PLAYWRIGHT_ROUTE_TRUTH_FLOW_BACKEND_PORT || 8014),
]

const isWin = process.platform === 'win32'

function log(msg) {
  console.log(`[route-truth-flow-port] ${msg}`)
}

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

function killPidWindows(pid) {
  execSync(`taskkill /PID ${pid} /F /T`, { encoding: 'utf8', windowsHide: true })
}

for (const port of PORTS) {
  if (!isWin) continue
  const pids = getListeningPidsWindows(port)
  if (pids.length === 0) {
    log(`Port ${port} is free.`)
    continue
  }
  for (const pid of pids) {
    log(`Stopping listener on port ${port} (PID ${pid})`)
    try {
      killPidWindows(pid)
    } catch (err) {
      console.error(`[route-truth-flow-port] Failed to stop PID ${pid}: ${err?.message || err}`)
      process.exit(1)
    }
  }
}

log('Route-truth-flow ports ready.')
