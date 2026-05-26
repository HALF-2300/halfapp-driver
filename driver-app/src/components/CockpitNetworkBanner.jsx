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
        className="mx-3 mt-2 rounded-xl border px-3 py-2.5 text-xs"
        style={{
          borderColor: 'rgba(245,158,11,0.4)',
          background: 'rgba(120,53,15,0.6)',
          color: '#fcd34d',
        }}
        data-testid="cockpit-offline-banner"
      >
        <span className="font-semibold">No connection</span>
        {' — '}ride actions paused until network returns.
      </div>
    )
  }

  if (degraded) {
    return (
      <div
        className="mx-3 mt-2 rounded-xl border px-3 py-2.5 text-xs"
        style={{
          borderColor: 'rgba(249,115,22,0.4)',
          background: 'rgba(124,45,18,0.55)',
          color: '#fdba74',
        }}
        data-testid="cockpit-degraded-banner"
      >
        <div className="flex items-center justify-between gap-2">
          <span>
            <span className="font-semibold">Connection degraded</span>
            {' — '}retrying safe actions.
          </span>
          {typeof onRetry === 'function' ? (
            <button
              type="button"
              className="shrink-0 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold"
              style={{ borderColor: 'rgba(249,115,22,0.5)', color: '#fdba74' }}
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
