/** @vitest-environment node */
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  ENGINEERING_INTELLIGENCE_MODE,
  QUICK_ACTION_LIST,
  STATUS_CHIPS,
  buildShellViewModel,
  selectQuickAction,
} from '../../src/utils/engineeringIntelligenceContext.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC_ROOT = path.resolve(__dirname, '../../src')

function walkSourceFiles(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry)
    const stat = statSync(full)
    if (stat.isDirectory()) {
      walkSourceFiles(full, acc)
      continue
    }
    if (/\.(jsx?|tsx?|css)$/.test(entry)) {
      acc.push(full)
    }
  }
  return acc
}

describe('engineeringIntelligenceContext', () => {
  it('initial view model shows LOCAL_CONTEXT_ONLY and AI connection OFF', () => {
    const vm = buildShellViewModel()
    assert.equal(vm.mode, 'LOCAL_CONTEXT_ONLY')
    assert.equal(vm.aiConnectionEnabled, false)
    assert.equal(vm.externalProviderConfigured, false)
    assert.ok(vm.statusChips.some((c) => c.label.includes('AI connection OFF')))
  })

  it('status chips include Report 03 and governance warnings', () => {
    const labels = STATUS_CHIPS.map((c) => c.label)
    assert.ok(labels.includes('Report 03 loaded'))
    assert.ok(labels.includes('OSRM runtime NO_GO'))
    assert.ok(labels.includes('Dual spine risk'))
    assert.equal(ENGINEERING_INTELLIGENCE_MODE, 'LOCAL_CONTEXT_ONLY')
  })

  it('selectQuickAction is pure local lookup with required guidance fields', () => {
    const originalFetch = globalThis.fetch
  let fetchCalled = false
  globalThis.fetch = () => {
    fetchCalled = true
    return Promise.reject(new Error('fetch should not run'))
  }

    try {
      for (const action of QUICK_ACTION_LIST) {
        const guidance = selectQuickAction(action.id)
        assert.equal(guidance.label, action.label)
        assert.ok(Array.isArray(guidance.files) && guidance.files.length > 0)
        assert.ok(typeof guidance.direction === 'string' && guidance.direction.length > 0)
        assert.ok(Array.isArray(guidance.forbiddenClaims) && guidance.forbiddenClaims.length > 0)
        assert.ok(Array.isArray(guidance.proofCommands) && guidance.proofCommands.length > 0)
        assert.ok(typeof guidance.expectedVerdict === 'string' && guidance.expectedVerdict.length > 0)
      }
      assert.equal(fetchCalled, false)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('source tree has no external model provider URLs or x-api-key', () => {
    const files = walkSourceFiles(SRC_ROOT)
    const forbidden = ['api.anthropic.com', 'api.openai.com', 'x-api-key']
    for (const file of files) {
      const text = readFileSync(file, 'utf8')
      for (const needle of forbidden) {
        assert.equal(
          text.includes(needle),
          false,
          `${path.relative(SRC_ROOT, file)} must not contain ${needle}`
        )
      }
    }
  })
})
