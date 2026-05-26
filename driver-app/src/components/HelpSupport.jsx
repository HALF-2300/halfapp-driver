import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AppShellLayout from './AppShellLayout.jsx'

function FaqCard({ q, a, testId }) {
  return (
    <div className="ha-card p-3" data-testid={testId}>
      <div className="text-sm font-semibold" style={{ color: 'var(--ha-text)' }}>{q}</div>
      <p className="text-xs mt-1 ha-truth-note">{a}</p>
    </div>
  )
}

export default function HelpSupport() {
  const navigate = useNavigate()

  const headerAction = (
    <button type="button" className="ha-btn ha-btn--ghost" onClick={() => navigate('/driver')}>
      Cockpit
    </button>
  )

  return (
    <AppShellLayout
      testId="help-support-screen"
      title="Help & support"
      subtitle="How HalfApp Driver works, and how to get help during an internal test run."
      headerAction={headerAction}
    >
      <section className="ha-section">
        <h2 className="ha-section-title">Getting around</h2>
        <div className="space-y-2">
          <FaqCard
            testId="help-faq-online"
            q="How do I go online to accept jobs?"
            a="From the map cockpit, tap Go online. The state badge in the corner will switch from Offline to Online and the heartbeat will start every 30 seconds."
          />
          <FaqCard
            testId="help-faq-incoming"
            q="What does the incoming-job sheet show?"
            a="An open-board offer visible to all eligible drivers. First claim wins — once you tap Accept, the backend assigns the job to you and other drivers stop seeing it."
          />
          <FaqCard
            testId="help-faq-lifecycle"
            q="What is the lifecycle of a job?"
            a="requested → accepted → driver_arrived → in_progress → completed. The cockpit gives you a single advance button at each stage."
          />
          <FaqCard
            testId="help-faq-finish-before-offline"
            q="Can I go offline mid-trip?"
            a="Finish the active job from the cockpit first. The settings screen reminds you to use the cockpit to finish a job before going offline."
          />
        </div>
      </section>

      <section className="ha-section">
        <h2 className="ha-section-title">Recovery</h2>
        <div className="space-y-2">
          <FaqCard
            testId="help-faq-refresh"
            q="I refreshed during a job. Did I lose state?"
            a="No. The backend tracks the active job. The cockpit calls GET /drivers/me/active-ride on load and resumes your sheet automatically — look for the blue Resumed active ride notice."
          />
          <FaqCard
            testId="help-faq-stale-presence"
            q="What does the orange stale-heartbeat banner mean?"
            a="Your last heartbeat to the backend is older than 45 seconds. You may appear offline to dispatch. Check your network and refresh."
          />
        </div>
      </section>

      <section className="ha-section">
        <h2 className="ha-section-title">Money truth</h2>
        <div className="space-y-2">
          <FaqCard
            testId="help-faq-earnings"
            q="Is the Earnings screen real money?"
            a="No. Amounts shown are calculation records from the backend pricing ledger — not payouts. No bank deposit has happened. This is internal-test framing only."
          />
          <FaqCard
            testId="help-faq-payment-execution"
            q={'What does "payment execution" mean in the audit?'}
            a="It is the reconciliation view of any provider-side payment activity that may exist behind the PAYMENTS_ENABLED flag. The driver UI does not claim funds have reached your bank."
          />
        </div>
      </section>

      <section className="ha-section">
        <h2 className="ha-section-title">Get help</h2>
        <div className="ha-card p-3 space-y-2" data-testid="help-contact-card">
          <p className="text-xs ha-truth-note">
            HalfApp does not run a live support hotline. Issues are routed to the owner / ops review
            queue.
          </p>
          <ul className="text-sm space-y-1" style={{ color: 'var(--ha-text)' }}>
            <li>
              <strong>Trip-specific issue:</strong> open the trip from the Trips screen and use the
              "Report an issue" form on the audit receipt. The ticket goes to ops.
            </li>
            <li>
              <strong>Account or login issue:</strong> use Sign out / Sign out all devices from{' '}
              <Link to="/driver/settings" className="font-semibold" style={{ color: 'var(--ha-green)' }}>
                Settings
              </Link>
              , then sign in again.
            </li>
            <li>
              <strong>Emergency on the road:</strong> HalfApp does not provide emergency response.
              Stop driving safely and call your local emergency number.
            </li>
          </ul>
        </div>
      </section>

      <section className="ha-section">
        <p className="text-xs ha-truth-note">
          This build is internal-test mode. Public service guarantees (insurance, payouts, road-network
          routing) are not in scope. See <code>docs/HALFAPP_REALITY_REPORT_01.md</code> for the full
          scope statement.
        </p>
      </section>
    </AppShellLayout>
  )
}
