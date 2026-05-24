import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  BUSY_LAYER_LABEL,
  ROUTE_LABEL_FALLBACK,
  SLOW_LAYER_LABEL,
} from '../../src/utils/streetIntelligenceLabels.js'

describe('streetIntelligenceLabels', () => {
  it('busy layer disclaimer is exact', () => {
    assert.equal(
      BUSY_LAYER_LABEL,
      'Estimated busy areas (based on recent in-app requests/offers). Not official demand.'
    )
  })

  it('slow layer disclaimer is exact', () => {
    assert.equal(
      SLOW_LAYER_LABEL,
      'Fleet-estimated slow areas (based on recent driver speeds). Not official live traffic.'
    )
  })

  it('fallback route label states not road-accurate', () => {
    assert.match(ROUTE_LABEL_FALLBACK, /not road-accurate/i)
  })
})
