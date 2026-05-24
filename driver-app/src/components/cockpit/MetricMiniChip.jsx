import React from 'react'

export default function MetricMiniChip({ label, value, testId }) {
  return (
    <div
      data-testid={testId}
      className="flex min-w-0 flex-1 flex-col rounded-[18px] border border-white/10 bg-white/[0.04] px-3 py-2"
    >
      <span className="text-[10px] uppercase tracking-wide text-[#AAB6C8]">{label}</span>
      <span className="truncate text-[15px] font-semibold text-[#F8FAFC]">{value}</span>
    </div>
  )
}
