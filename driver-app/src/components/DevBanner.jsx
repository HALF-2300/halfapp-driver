import React from 'react'

export default function DevBanner() {
  if (!import.meta.env.DEV) return null
  const hasHash = typeof window !== 'undefined' && window.location.hash.startsWith('#/')
  return (
    <div
      data-testid="dev-banner"
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-3 py-1 text-xs font-medium bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-sm"
      style={{letterSpacing:'.5px'}}
    >
      <span>DEV MODE</span>
      <span className="opacity-80">{hasHash ? 'Hash routing active' : 'Normalizing route → hash'}</span>
    </div>
  )
}
