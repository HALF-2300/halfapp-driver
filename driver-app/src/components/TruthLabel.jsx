import React from 'react'

/** @typedef {'BACKEND_OWNED' | 'DEVICE_LOCATION' | 'DEV_FIXTURE' | 'UNAVAILABLE' | 'EXPERIMENTAL' | 'NO_ROUTE_SNAPSHOT' | 'NO_FARE_QUOTE' | 'DISPATCH_BACKEND_OWNED'} TruthLabelKind */

const LABEL_COPY = {
  BACKEND_OWNED: 'Backend-owned',
  DEVICE_LOCATION: 'Device location',
  DEV_FIXTURE: 'Dev fixture',
  UNAVAILABLE: 'Unavailable',
  EXPERIMENTAL: 'Experimental map',
  NO_ROUTE_SNAPSHOT: 'No route guarantee',
  NO_FARE_QUOTE: 'No fare quote',
  DISPATCH_BACKEND_OWNED: 'Dispatch truth: backend-owned',
}

const LABEL_TONE = {
  BACKEND_OWNED: 'border-emerald-400/40 bg-emerald-950/80 text-emerald-100',
  DEVICE_LOCATION: 'border-sky-400/40 bg-sky-950/80 text-sky-100',
  DEV_FIXTURE: 'border-amber-400/40 bg-amber-950/85 text-amber-100',
  UNAVAILABLE: 'border-slate-600 bg-slate-900/90 text-slate-300',
  EXPERIMENTAL: 'border-amber-400/35 bg-amber-950/85 text-amber-100',
  NO_ROUTE_SNAPSHOT: 'border-slate-600 bg-slate-900/90 text-slate-300',
  NO_FARE_QUOTE: 'border-slate-600 bg-slate-900/90 text-slate-300',
  DISPATCH_BACKEND_OWNED: 'border-blue-400/40 bg-blue-950/80 text-blue-100',
}

/**
 * Small UI chip marking what kind of truth a surface represents.
 *
 * @param {{ kind: TruthLabelKind, children?: React.ReactNode, className?: string }} props
 */
export default function TruthLabel({ kind, children, className = '' }) {
  const text = children ?? (kind ? LABEL_COPY[kind] : null) ?? kind ?? 'Truth'
  const tone = (kind && LABEL_TONE[kind]) ?? LABEL_TONE.UNAVAILABLE
  const testId = kind ? `truth-label-${String(kind).toLowerCase()}` : 'truth-label-text'
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide backdrop-blur ${tone} ${className}`}
    >
      {text}
    </span>
  )
}

export { LABEL_COPY }
