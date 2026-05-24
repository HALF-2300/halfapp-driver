import React, { memo, useMemo } from 'react'

/**
 * Simple bar chart for recent trip earnings (no external chart library).
 */
const EarningsChart = memo(({ data = [] }) => {
  const points = useMemo(() => {
    const list = Array.isArray(data) ? data : []
    return list
      .map((row, index) => {
        const earnings = Number(row.earnings ?? row.fare_amount ?? row.amount ?? 0)
        const label = row.label ?? row.date ?? `#${index + 1}`
        return { label, earnings: Number.isFinite(earnings) ? earnings : 0 }
      })
      .slice(-12)
  }, [data])

  const max = useMemo(
    () => Math.max(1, ...points.map((p) => p.earnings)),
    [points]
  )

  if (!points.length) {
    return (
      <div className="ha-card ha-empty text-sm" data-testid="earnings-chart-empty">
        No chart data yet — complete trips to see trends.
      </div>
    )
  }

  return (
    <div className="ha-card p-4" data-testid="earnings-chart">
      <h3 className="ha-section-title text-sm mb-3">Recent trip earnings</h3>
      <div className="flex items-end gap-2 h-40" role="img" aria-label="Recent earnings bars">
        {points.map((point) => (
          <div key={point.label} className="flex flex-1 flex-col items-center gap-1 min-w-0">
            <div
              className="w-full rounded-t-md"
              style={{
                height: `${Math.max(8, (point.earnings / max) * 100)}%`,
                background: 'var(--ha-green)',
                minHeight: 8,
              }}
              title={`$${point.earnings.toFixed(2)}`}
            />
            <span className="text-[9px] ha-truth-note truncate w-full text-center">{point.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
})

EarningsChart.displayName = 'EarningsChart'

export default EarningsChart
