import React, { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  ENGINEERING_INTELLIGENCE_MODE,
  QUICK_ACTION_LIST,
  REPORT_ID,
  STATUS_CHIPS,
  selectQuickAction,
} from '../utils/engineeringIntelligenceContext.js'

import './HalfAppEngineeringIntelligence.css'

function GuidanceDetail({ guidance }) {
  if (!guidance) {
    return (
      <p className="halfapp-ei__placeholder" data-testid="ei-guidance-placeholder">
        Select a quick action to expand local guidance from Report 03. No network calls are made.
      </p>
    )
  }

  return (
    <div className="halfapp-ei__detail" data-testid="ei-guidance-detail">
      <h3>{guidance.label}</h3>
      <section>
        <h4>Recommended files</h4>
        <ul>
          {guidance.files.map((file) => (
            <li key={file}>{file}</li>
          ))}
        </ul>
      </section>
      <section>
        <h4>Implementation direction</h4>
        <p>{guidance.direction}</p>
      </section>
      <section>
        <h4>Forbidden claims</h4>
        <ul>
          {guidance.forbiddenClaims.map((claim) => (
            <li key={claim}>{claim}</li>
          ))}
        </ul>
      </section>
      <section>
        <h4>Proof commands</h4>
        <pre>{guidance.proofCommands.join('\n')}</pre>
      </section>
      <section>
        <h4>Expected verdict language</h4>
        <p className="halfapp-ei__verdict">{guidance.expectedVerdict}</p>
      </section>
    </div>
  )
}

export default function HalfAppEngineeringIntelligence() {
  const [selectedId, setSelectedId] = useState(null)

  const guidance = useMemo(
    () => (selectedId ? selectQuickAction(selectedId) : null),
    [selectedId]
  )

  const onQuickAction = useCallback((actionId) => {
    setSelectedId(actionId)
  }, [])

  return (
    <div className="halfapp-ei" data-testid="engineering-intelligence-shell">
      <header className="halfapp-ei__header">
        <Link to="/driver" className="halfapp-ei__back">
          ← Back to cockpit
        </Link>
        <h1 className="halfapp-ei__title">HalfApp Engineering Intelligence</h1>
        <p className="halfapp-ei__subtitle">
          Developer/operator shell — governance brain from {REPORT_ID}. Not ride product AI. Not
          dispatch ML. Local static context only.
        </p>
        <div className="halfapp-ei__mode" data-testid="ei-mode">
          {ENGINEERING_INTELLIGENCE_MODE}
        </div>
        <div className="halfapp-ei__chips" data-testid="ei-status-chips">
          {STATUS_CHIPS.map((chip) => (
            <span
              key={chip.id}
              className={`halfapp-ei__chip halfapp-ei__chip--${chip.tone}`}
              data-testid={`ei-chip-${chip.id}`}
            >
              {chip.label}
            </span>
          ))}
        </div>
        <p className="halfapp-ei__status-note" data-testid="ei-ai-status">
          AI connection OFF — no external provider calls from this panel.
        </p>
      </header>

      <div className="halfapp-ei__layout">
        <div className="halfapp-ei__panel">
          <h2 className="halfapp-ei__panel-title">Quick actions (local only)</h2>
          <div className="halfapp-ei__actions" data-testid="ei-quick-actions">
            {QUICK_ACTION_LIST.map((action) => (
              <button
                key={action.id}
                type="button"
                className={`halfapp-ei__action-btn${selectedId === action.id ? ' halfapp-ei__action-btn--active' : ''}`}
                data-testid={`ei-action-${action.id}`}
                onClick={() => onQuickAction(action.id)}
              >
                {action.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="halfapp-ei__ai-btn"
            disabled
            data-testid="ei-ai-connect-btn"
            title="Backend proxy not implemented"
          >
            Connect AI — Backend proxy not implemented
          </button>
        </div>

        <div className="halfapp-ei__panel">
          <h2 className="halfapp-ei__panel-title">Guidance</h2>
          <GuidanceDetail guidance={guidance} />
        </div>
      </div>
    </div>
  )
}
