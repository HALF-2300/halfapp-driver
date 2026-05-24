import React, { useCallback, useEffect, useRef, useState } from 'react'
import driverAPI from '../../utils/api.js'

export default function RideChatPanel({ rideId }) {
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const listRef = useRef(null)

  const load = useCallback(async () => {
    if (!rideId) return
    try {
      const data = await driverAPI.getRideMessages(rideId)
      setItems(Array.isArray(data?.items) ? data.items : [])
      setError(null)
    } catch (err) {
      setError(err?.message || 'Could not load messages')
    } finally {
      setLoading(false)
    }
  }, [rideId])

  useEffect(() => {
    load()
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') load()
    }, 5000)
    return () => window.clearInterval(timer)
  }, [load])

  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [items])

  const send = async () => {
    const body = text.trim()
    if (!body) return
    setText('')
    try {
      await driverAPI.sendRideMessage(rideId, body)
      await load()
    } catch (err) {
      setError(err?.message || 'Could not send message')
    }
  }

  return (
    <div className="ha-card p-3" data-testid="ride-chat-panel">
      <div className="text-sm font-semibold">Ride messages</div>
      <p className="text-xs ha-truth-note mt-1">
        Stored for this trip. Rider delivery requires a rider client (not in this build).
      </p>
      {loading ? <p className="text-xs mt-2 ha-truth-note">Loading…</p> : null}
      {error ? <p className="text-xs mt-2 text-amber-300">{error}</p> : null}
      <div
        ref={listRef}
        className="mt-2 max-h-40 overflow-y-auto space-y-2 rounded-lg border border-white/10 p-2"
        data-testid="ride-chat-list"
      >
        {items.length === 0 && !loading ? (
          <p className="text-xs ha-truth-note">No messages yet.</p>
        ) : null}
        {items.map((m) => (
          <div key={m.id}>
            <div className="text-[10px] ha-truth-note">
              {m.sender_role} · {m.created_at ? new Date(m.created_at).toLocaleTimeString() : ''}
            </div>
            <div className="text-sm">{m.body}</div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        <input
          className="flex-1 text-sm rounded-lg px-2 py-2"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Message rider…"
          data-testid="ride-chat-input"
        />
        <button
          type="button"
          className="ha-btn ha-btn--primary shrink-0"
          onClick={send}
          data-testid="ride-chat-send"
        >
          Send
        </button>
      </div>
    </div>
  )
}
