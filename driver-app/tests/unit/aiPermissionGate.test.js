import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  AI_CONNECTION_STATES,
  DEFAULT_AI_CONNECTION_STATE,
  canSendToModel,
} from '../../src/utils/aiConnectionState.js'
import { resolveEngineeringAssistantUrl } from '../../src/services/engineeringAssistantApi.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC_ROOT = path.resolve(__dirname, '../../src')

const FORBIDDEN_PATTERNS = [
  /api\.anthropic\.com/i,
  /api\.openai\.com/i,
  /generativelanguage\.googleapis\.com/i,
  /\bx-api-key\b/i,
  /ANTHROPIC_API_KEY/i,
  /OPENAI_API_KEY/i,
  /GEMINI_API_KEY/i,
]

function listSourceFiles(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      listSourceFiles(fullPath, acc)
      continue
    }
    if (/\.(js|jsx|ts|tsx)$/.test(entry.name)) {
      acc.push(fullPath)
    }
  }
  return acc
}

describe('HALFAPP_AI_ASSISTANT_PERMISSION_GATE_01', () => {
  it('defaults AI connection to OFF', () => {
    assert.equal(DEFAULT_AI_CONNECTION_STATE, AI_CONNECTION_STATES.OFF)
    assert.equal(canSendToModel(AI_CONNECTION_STATES.OFF), false)
    assert.equal(canSendToModel(AI_CONNECTION_STATES.LOCAL_CONTEXT_ONLY), false)
    assert.equal(canSendToModel(AI_CONNECTION_STATES.BACKEND_CONNECTED), true)
  })

  it('routes model calls through backend engineering-assistant paths only', () => {
    const statusUrl = resolveEngineeringAssistantUrl('/status')
    const chatUrl = resolveEngineeringAssistantUrl('/chat')
    assert.match(statusUrl, /engineering-assistant\/status$/)
    assert.match(chatUrl, /engineering-assistant\/chat$/)
    assert.doesNotMatch(statusUrl, /anthropic|openai|googleapis/i)
    assert.doesNotMatch(chatUrl, /anthropic|openai|googleapis/i)
  })

  it('driver-app source contains no direct provider URLs or API key handling', () => {
    const files = listSourceFiles(SRC_ROOT)
    assert.ok(files.length > 0)
    const violations = []
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf8')
      for (const pattern of FORBIDDEN_PATTERNS) {
        if (pattern.test(content)) {
          violations.push(`${path.relative(SRC_ROOT, file)}: ${pattern}`)
        }
      }
    }
    assert.deepEqual(violations, [])
  })

  it('HalfAppEngineerPanel source never fetches provider hosts directly', () => {
    const panelPath = path.join(SRC_ROOT, 'components/cockpit/HalfAppEngineerPanel.jsx')
    const apiPath = path.join(SRC_ROOT, 'services/engineeringAssistantApi.js')
    const panel = fs.readFileSync(panelPath, 'utf8')
    const api = fs.readFileSync(apiPath, 'utf8')
    assert.doesNotMatch(panel, /fetch\s*\(\s*['"`]https?:\/\/api\.(anthropic|openai)/i)
    assert.doesNotMatch(api, /api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com/i)
    assert.match(panel, /Connect AI Assistant/)
    assert.match(panel, /canSendToModel/)
  })
})
