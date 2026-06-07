import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../../src')

function readSrc(relativePath) {
  return readFileSync(path.resolve(SRC, relativePath), 'utf8')
}

describe('HalfApp Driver premium internal app design', () => {
  it('keeps a dedicated premium interior design layer for cockpit and app shell', () => {
    const css = readSrc('styles/globals.css')

    assert.match(css, /--ha-bg:/)
    assert.match(css, /\.marketplace-bottom-sheet/)
    assert.match(css, /\.driver-app-shell__header/)
    assert.match(css, /max-width: 430px/)
  })

  it('uses the mobile app nav classes instead of one-off template navigation styling', () => {
    const nav = readSrc('components/BottomNavigation.jsx')

    assert.match(nav, /bottom-nav-dock--fixed/)
    assert.match(nav, /bottom-nav-item--active/)
    assert.match(nav, /bottom-nav-icon/)
    assert.match(nav, /bottom-nav-badge/)
  })

  it('does not introduce false launch or payout claims in the design pass surfaces', () => {
    const surfaces = [
      readSrc('styles/globals.css'),
      readSrc('components/BottomNavigation.jsx'),
      readSrc('components/cockpit/RideRequestCard.jsx'),
      readSrc('components/cockpit/MarketplaceBottomSheet.jsx'),
    ].join('\n')

    assert.equal(/public launch ready|bank transfer complete|cash out|instant payout|paid to driver/i.test(surfaces), false)
  })
})
