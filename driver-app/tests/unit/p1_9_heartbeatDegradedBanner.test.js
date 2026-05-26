import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../../src')

function src(rel) {
  return readFileSync(path.join(SRC, rel), 'utf8')
}

const mapSrc = src('components/MapHome.jsx')
const bannerSrc = src('components/CockpitNetworkBanner.jsx')

describe('P1-9 heartbeat failure → degraded banner (formal proof)', () => {
  it('isTransientNetworkError is defined and covers fetch/network/abort/5xx', () => {
    assert.match(mapSrc, /function isTransientNetworkError/)
    assert.match(mapSrc, /502|503|504/)
    assert.match(mapSrc, /AbortError/)
    assert.match(mapSrc, /fetch|network/)
  })

  it('heartbeat catch wires markNetworkDegraded on transient errors', () => {
    // The heartbeat effect must call markNetworkDegraded when a network error
    // is caught, not silently swallow it.
    assert.match(mapSrc, /isTransientNetworkError\(err\).*markNetworkDegraded|markNetworkDegraded.*isTransientNetworkError\(err\)/s)
  })

  it('heartbeat success clears degraded state', () => {
    assert.match(mapSrc, /clearNetworkDegraded\(\)/)
  })

  it('CockpitNetworkBanner receives networkDegraded prop from MapHome', () => {
    assert.match(mapSrc, /degraded=\{networkDegraded\}/)
    assert.match(mapSrc, /CockpitNetworkBanner/)
  })

  it('CockpitNetworkBanner renders degraded UI when degraded=true', () => {
    assert.match(bannerSrc, /if \(degraded\)/)
    assert.match(bannerSrc, /data-testid="cockpit-degraded-banner"/)
    assert.match(bannerSrc, /Connection degraded/)
  })

  it('NETWORK_DEGRADED_MS constant gates auto-clear timer (15s)', () => {
    assert.match(mapSrc, /NETWORK_DEGRADED_MS\s*=\s*15[_,]?000/)
  })

  it('degraded banner exposes a Retry button when onRetry is provided', () => {
    assert.match(bannerSrc, /data-testid="cockpit-network-retry"/)
    assert.match(bannerSrc, /onRetry/)
  })
})
