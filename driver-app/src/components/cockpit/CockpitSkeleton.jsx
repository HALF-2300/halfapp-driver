import React from 'react'

/** Shown while active-ride recovery is in flight — avoids empty-cockpit flash on refresh. */
export default function CockpitSkeleton() {
  return (
    <div
      className="marketplace-bottom-sheet marketplace-bottom-sheet--expanded pointer-events-auto px-4 py-5"
      data-testid="cockpit-skeleton"
      aria-busy="true"
      aria-label="Loading your ride"
    >
      <div className="animate-pulse space-y-3">
        <div className="h-3 w-24 rounded bg-white/10" />
        <div className="h-6 w-48 rounded bg-white/15" />
        <div className="h-4 w-full rounded bg-white/10" />
        <div className="h-12 w-full rounded-xl bg-white/10" />
      </div>
    </div>
  )
}
