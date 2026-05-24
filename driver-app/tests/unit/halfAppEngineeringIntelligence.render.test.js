import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  ENGINEERING_INTELLIGENCE_MODE,
  QUICK_ACTION_LIST,
  selectQuickAction,
} from '../../src/utils/engineeringIntelligenceContext.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const COMPONENT_PATH = path.resolve(
  __dirname,
  '../../src/components/HalfAppEngineeringIntelligence.jsx'
)

describe('HalfAppEngineeringIntelligence shell render contract', () => {
  it('component source renders LOCAL_CONTEXT_ONLY and AI connection OFF markers', () => {
    const source = readFileSync(COMPONENT_PATH, 'utf8')
    assert.ok(source.includes('HalfApp Engineering Intelligence'))
    assert.ok(source.includes('data-testid="ei-mode"'))
    assert.ok(source.includes('{ENGINEERING_INTELLIGENCE_MODE}'))
    assert.ok(source.includes('AI connection OFF'))
    assert.ok(source.includes('Backend proxy not implemented'))
    assert.equal(source.includes('fetch('), false)
    assert.equal(ENGINEERING_INTELLIGENCE_MODE, 'LOCAL_CONTEXT_ONLY')
  })

  it('quick action click path uses local selectQuickAction only (no fetch)', () => {
    const originalFetch = globalThis.fetch
    let fetchCalled = false
    globalThis.fetch = () => {
      fetchCalled = true
      return Promise.reject(new Error('fetch should not run'))
    }

    try {
      for (const action of QUICK_ACTION_LIST) {
        const guidance = selectQuickAction(action.id)
        assert.ok(guidance?.label)
      }
      assert.equal(fetchCalled, false)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})
