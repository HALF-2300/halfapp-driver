import React from 'react'

const CAPABILITIES = [
  {
    id: 'map',
    title: 'Map-first cockpit',
    body: 'Your workday starts from the map, not from a dashboard.',
  },
  {
    id: 'availability',
    title: 'Backend-owned availability',
    body: 'Your online state is stored by the backend and survives refresh.',
  },
  {
    id: 'visibility',
    title: 'Ride visibility controls',
    body: 'See opportunities, hide them for your account, and keep the marketplace state auditable.',
  },
  {
    id: 'flow',
    title: 'Transparent driver flow',
    body: 'Truth labels and diagnostics stay available without cluttering the main cockpit.',
  },
]

export default function DriverPortalCapabilities() {
  return (
    <section className="dp-capabilities" id="how" data-testid="driver-portal-capabilities">
      <div className="dp-section-head">
        <p className="dp-eyebrow">Built for drivers</p>
        <h2>Everything you need before you go online</h2>
      </div>
      <div className="dp-capabilities__grid">
        {CAPABILITIES.map((item) => (
          <article key={item.id} className="dp-cap-card dp-animate-in">
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
