import React from 'react'

export default function DriverLocationChip({ message, geoState, title, compact = false }) {
  return (
    <div className="pointer-events-auto flex items-center justify-center">
      <span
        data-testid="location-status"
        data-geo-state={geoState}
        className={`max-w-[min(92vw,360px)] rounded-full border border-white/10 text-center font-medium text-[#E2E8F0] backdrop-blur-md ${
          compact
            ? 'bg-[rgba(7,12,26,0.55)] px-2.5 py-1 text-[11px] text-[#94A3B8]'
            : 'bg-[rgba(7,12,26,0.85)] px-3 py-1.5 text-[12px]'
        }`}
        title={title || undefined}
      >
        {message}
      </span>
    </div>
  )
}
