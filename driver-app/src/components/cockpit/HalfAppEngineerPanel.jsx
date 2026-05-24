import React, { useCallback, useMemo, useState } from 'react'
import { AI_CONNECTION_STATES, connectionStateLabel } from '../../utils/aiConnectionState.js'
import {
  LOCAL_RESEARCH_SNIPPETS,
  QUICK_ACTION_PROMPTS,
} from '../../utils/engineeringAssistantResearch.js'
import { useAiConnection } from '../../hooks/useAiConnection.js'

/**
 * HalfApp Engineer — local research and optional backend-proxied model chat.
 * Never calls provider APIs from the browser.
 */
export default function HalfAppEngineerPanel({ authToken }) {
  const {
    connectionState,
    errorMessage,
    connecting,
    sending,
    canSendToModel,
    enableLocalContextOnly,
    disconnect,
    connectToBackend,
    sendChat,
  } = useAiConnection({ token: authToken })

  const [prompt, setPrompt] = useState('')
  const [localContext, setLocalContext] = useState('')
  const [messages, setMessages] = useState([])
  const [chatError, setChatError] = useState('')

  const applyQuickAction = useCallback((key) => {
    const text = QUICK_ACTION_PROMPTS[key] || ''
    setPrompt(text)
    setChatError('')
  }, [])

  const loadLocalResearch = useCallback((key) => {
    const snippet = LOCAL_RESEARCH_SNIPPETS[key] || ''
    setLocalContext(snippet)
    if (connectionState === AI_CONNECTION_STATES.OFF) {
      enableLocalContextOnly()
    }
    setChatError('')
  }, [connectionState, enableLocalContextOnly])

  const handleConnect = useCallback(async () => {
    setChatError('')
    await connectToBackend()
  }, [connectToBackend])

  const handleSend = useCallback(async () => {
    const trimmed = prompt.trim()
    if (!trimmed) return
    if (!canSendToModel) {
      setChatError('Connect AI Assistant before sending to a model.')
      return
    }
    setChatError('')
    try {
      const result = await sendChat({
        messages,
        prompt: localContext ? `${localContext}\n\n---\n\n${trimmed}` : trimmed,
      })
      const userMessage = { role: 'user', content: trimmed }
      const assistantMessage = { role: 'assistant', content: result.reply }
      setMessages((prev) => [...prev, userMessage, assistantMessage])
      setPrompt('')
    } catch (err) {
      setChatError(err?.message || 'Failed to send message.')
    }
  }, [canSendToModel, localContext, messages, prompt, sendChat])

  const statusLine = useMemo(() => connectionStateLabel(connectionState), [connectionState])

  if (!import.meta.env.DEV) return null

  return (
    <section
      className="mt-4 rounded-[16px] border border-cyan-400/30 bg-cyan-950/25 p-3"
      data-testid="halfapp-engineer-panel"
      data-ai-connection-state={connectionState}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-cyan-200">
          HalfApp Engineer
        </p>
        <span
          className="rounded-full border border-white/10 bg-black/40 px-2 py-0.5 text-[10px] text-[#AAB6C8]"
          data-testid="ai-connection-status"
        >
          {statusLine}
        </span>
      </div>
      <p className="mt-1 text-[10px] text-[#AAB6C8]">
        Local research fills prompts only. Model calls go through the backend after you connect.
      </p>

      <div className="mt-2 flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={enableLocalContextOnly}
          data-testid="enable-local-context-btn"
          className="cockpit-pressable rounded-full border border-white/10 bg-white/[0.06] px-2.5 py-1 text-[10px] text-[#F8FAFC]"
        >
          Local context only
        </button>
        <button
          type="button"
          onClick={handleConnect}
          disabled={connecting}
          data-testid="connect-ai-assistant-btn"
          className="cockpit-pressable rounded-full border border-cyan-400/40 bg-cyan-500/20 px-2.5 py-1 text-[10px] font-medium text-cyan-100 disabled:opacity-50"
        >
          {connecting ? 'Connecting…' : 'Connect AI Assistant'}
        </button>
        {connectionState !== AI_CONNECTION_STATES.OFF && (
          <button
            type="button"
            onClick={disconnect}
            data-testid="disconnect-ai-assistant-btn"
            className="cockpit-pressable rounded-full border border-white/10 px-2.5 py-1 text-[10px] text-[#AAB6C8]"
          >
            Disconnect
          </button>
        )}
      </div>

      {errorMessage && (
        <p className="mt-2 text-[10px] text-amber-300" data-testid="ai-connection-error">
          {errorMessage}
        </p>
      )}

      <div className="mt-2 flex flex-wrap gap-1" data-testid="engineer-quick-actions">
        {Object.keys(QUICK_ACTION_PROMPTS).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => applyQuickAction(key)}
            data-testid={`quick-action-${key}`}
            className="cockpit-pressable rounded-full border border-white/10 px-2 py-0.5 text-[9px] text-[#AAB6C8]"
          >
            {key.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <div className="mt-2 flex flex-wrap gap-1" data-testid="engineer-local-research">
        {Object.keys(LOCAL_RESEARCH_SNIPPETS).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => loadLocalResearch(key)}
            data-testid={`local-research-${key}`}
            className="cockpit-pressable rounded-full border border-white/10 px-2 py-0.5 text-[9px] text-[#AAB6C8]"
          >
            Load {key.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {localContext && (
        <pre
          className="mt-2 max-h-[80px] overflow-y-auto rounded-lg border border-white/5 bg-black/50 p-2 text-[9px] text-[#AAB6C8] whitespace-pre-wrap"
          data-testid="engineer-local-context"
        >
          {localContext}
        </pre>
      )}

      <label className="mt-2 block text-[10px] text-[#AAB6C8]" htmlFor="engineer-prompt">
        Prompt
      </label>
      <textarea
        id="engineer-prompt"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
        data-testid="engineer-prompt-input"
        className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-2 py-1.5 text-[11px] text-[#F8FAFC]"
      />

      <button
        type="button"
        onClick={handleSend}
        disabled={!canSendToModel || sending || !prompt.trim()}
        data-testid="engineer-send-btn"
        className="cockpit-pressable mt-2 rounded-full border border-cyan-400/40 bg-cyan-500/25 px-3 py-1.5 text-[11px] font-medium text-cyan-100 disabled:opacity-50"
      >
        {sending ? 'Sending…' : 'Send to model (backend)'}
      </button>

      {chatError && (
        <p className="mt-2 text-[10px] text-amber-300" data-testid="engineer-chat-error">
          {chatError}
        </p>
      )}

      {messages.length > 0 && (
        <ul className="mt-2 max-h-[120px] space-y-1 overflow-y-auto text-[10px] text-[#AAB6C8]" data-testid="engineer-chat-log">
          {messages.map((msg, index) => (
            <li key={`${msg.role}-${index}`}>
              <strong>{msg.role}:</strong> {msg.content.slice(0, 200)}
              {msg.content.length > 200 ? '…' : ''}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
