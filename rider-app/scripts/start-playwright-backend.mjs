/** Re-export pattern: launch isolated backend for rider Playwright (port via env). */
import { spawn } from 'node:child_process'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.resolve(__dirname, '../../backend')
const port = Number(process.env.PLAYWRIGHT_RIDER_FLOW_BACKEND_PORT || 8012)
const healthUrl = `http://127.0.0.1:${port}/health`

function waitForHealth(timeoutMs = 120_000) {
  const started = Date.now()
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(healthUrl, (res) => {
        res.resume()
        if (res.statusCode === 200) {
          resolve()
          return
        }
        retry()
      })
      req.on('error', retry)
      req.setTimeout(2_000, () => {
        req.destroy()
        retry()
      })
    }
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`Backend health check timed out: ${healthUrl}`))
        return
      }
      setTimeout(tick, 400)
    }
    tick()
  })
}

const python = process.platform === 'win32' ? 'py' : 'python3'
const pythonArgs =
  process.platform === 'win32'
    ? ['-3.11', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', `--port=${port}`]
    : ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', `--port=${port}`]

const child = spawn(python, pythonArgs, {
  cwd: backendDir,
  env: process.env,
  stdio: 'inherit',
  shell: false,
})

child.on('error', (err) => {
  console.error('[rider-playwright-backend] failed to start uvicorn:', err)
  process.exit(1)
})

child.on('exit', (code, signal) => {
  if (signal) process.exit(1)
  if (code && code !== 0) process.exit(code)
})

waitForHealth()
  .then(() => console.log(`[rider-playwright-backend] ready at ${healthUrl}`))
  .catch((err) => {
    console.error(String(err))
    child.kill()
    process.exit(1)
  })

process.on('SIGINT', () => child.kill())
process.on('SIGTERM', () => child.kill())
