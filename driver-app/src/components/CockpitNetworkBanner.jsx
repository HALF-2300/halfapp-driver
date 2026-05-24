import { useEffect, useRef, useState } from 'react'

export default function CockpitNetworkBanner({ degraded = false, onRetry }) {
  const [online, setOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  )
  const wasOfflineRef = useRef(!online)

  useEffect(() => {
    const onOnline = () => {
      const wasOffline = wasOfflineRef.current
      wasOfflineRef.current = false
      setOnline(true)
      if (wasOffline && typeof onRetry === 'function') {
        onRetry()
      }
    }
    const onOffline = () => {
      wasOfflineRef.current = true
      setOnline(false)
    }
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [onRetry])

  if (!online) {
    return (
      <div
        className="mx-3 mt-2 rounded-xl border border-amber-500/40 bg-amber-950/80 px-3 py-2 text-xs text-amber-100"
        data-testid="cockpit-offline-banner"
      >
        Offline — ride actions are paused until connection returns.
      </div>
    )
  }

  if (degraded) {
    return (
      <div
        className="mx-3 mt-2 rounded-xl border border-orange-500/40 bg-orange-950/80 px-3 py-2 text-xs text-orange-100"
        data-testid="cockpit-degraded-banner"
      >
        <div className="flex items-center justify-between gap-2">
          <span>Connection degraded — retrying safe actions.</span>
          {typeof onRetry === 'function' ? (
            <button
              type="button"
              className="shrink-0 rounded-md border border-orange-400/50 px-2 py-0.5 text-[10px] font-semibold text-orange-100"
              data-testid="cockpit-network-retry"
              onClick={() => onRetry()}
            >
              Retry
            </button>
          ) : null}
        </div>
      </div>
    )
  }

  return null
}
