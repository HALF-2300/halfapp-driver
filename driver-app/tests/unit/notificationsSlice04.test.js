import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import {
  isNotificationRead,
  normalizeNotification,
} from '../../src/utils/notificationDisplay.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const notificationsSrc = readFileSync(
  path.resolve(__dirname, '../../src/components/Notifications.jsx'),
  'utf8'
)

describe('notificationDisplay', () => {
  it('maps backend read flag', () => {
    assert.equal(isNotificationRead({ read: true }), true)
    assert.equal(isNotificationRead({ read: false }), false)
    assert.equal(isNotificationRead({ is_read: true }), true)
  })

  it('normalizes list items', () => {
    const n = normalizeNotification({
      id: 7,
      title: 'Ride accepted',
      message: 'Go to pickup',
      created_at: '2026-05-23T12:00:00Z',
      read: false,
    })
    assert.equal(n.id, 7)
    assert.equal(n.isRead, false)
  })
})

describe('Notifications screen (Slice 04)', () => {
  it('uses AppShellLayout and mark-read wiring', () => {
    assert.match(notificationsSrc, /AppShellLayout/)
    assert.match(notificationsSrc, /markNotificationRead/)
    assert.match(notificationsSrc, /testId="notifications-screen"/)
    assert.match(notificationsSrc, /data-testid="notifications-empty"/)
  })

  it('gates demo messages tab to development', () => {
    assert.match(notificationsSrc, /import\.meta\.env\.DEV/)
    assert.match(notificationsSrc, /SHOW_DEMO_MESSAGES_TAB/)
  })

  it('uses existing notifications API client', () => {
    assert.match(notificationsSrc, /getNotifications/)
  })
})
