import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const settingsSrc = readFileSync(
  path.resolve(__dirname, '../../src/components/DriverSettings.jsx'),
  'utf8'
)
const mapSrc = readFileSync(
  path.resolve(__dirname, '../../src/components/MapHome.jsx'),
  'utf8'
)

describe('DriverSettings (product completion)', () => {
  it('loads session and connect status from driver API', () => {
    assert.match(settingsSrc, /getDriverMeStatus/)
    assert.match(settingsSrc, /getStripeConnectStatus/)
    assert.match(settingsSrc, /data-testid="settings-session-section"/)
    assert.match(settingsSrc, /data-testid="settings-connect-section"/)
  })

  it('loads and persists app settings via GET/PUT /drivers/me/settings', () => {
    assert.match(settingsSrc, /getDriverAppSettings/)
    assert.match(settingsSrc, /updatePreferences|putDriverAppSettings/)
    assert.match(settingsSrc, /data-testid="settings-preferences-section"/)
    assert.match(settingsSrc, /patchAppSettings/)
    assert.match(settingsSrc, /notif_push_enabled/)
  })

  it('supports app profile overlay via /drivers/me/profile', () => {
    assert.match(settingsSrc, /getDriverMeProfile/)
    assert.match(settingsSrc, /putDriverMeProfile/)
    assert.match(settingsSrc, /data-testid="settings-app-profile-section"/)
  })

  it('does not start Connect onboarding from settings', () => {
    assert.equal(settingsSrc.includes('connect/start'), false)
  })
})

describe('MapHome active ride resume', () => {
  it('prefers current_ride_id from me/status when restoring', () => {
    assert.match(mapSrc, /current_ride_id/)
    assert.match(mapSrc, /assignedByStatusId/)
  })

  it('refreshes on tab visibility and shows resume notice', () => {
    assert.match(mapSrc, /visibilitychange/)
    assert.match(mapSrc, /data-testid="cockpit-resume-notice"/)
  })
})
