import { useCallback, useState } from 'react'
import {
  AI_CONNECTION_STATES,
  DEFAULT_AI_CONNECTION_STATE,
  canSendToModel,
} from '../utils/aiConnectionState.js'
import { fetchAssistantStatus, sendAssistantChat } from '../services/engineeringAssistantApi.js'

/**
 * Manages explicit AI connection — default OFF; model calls only after BACKEND_CONNECTED.
 */
export function useAiConnection({ token } = {}) {
  const [connectionState, setConnectionState] = useState(DEFAULT_AI_CONNECTION_STATE)
  const [errorMessage, setErrorMessage] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [sending, setSending] = useState(false)

  const enableLocalContextOnly = useCallback(() => {
    setErrorMessage('')
    setConnectionState(AI_CONNECTION_STATES.LOCAL_CONTEXT_ONLY)
  }, [])

  const disconnect = useCallback(() => {
    setErrorMessage('')
    setConnectionState(AI_CONNECTION_STATES.OFF)
  }, [])

  const connectToBackend = useCallback(async () => {
    if (!token) {
      setConnectionState(AI_CONNECTION_STATES.ERROR)
      setErrorMessage('Sign in required before connecting the assistant.')
      return false
    }
    setConnecting(true)
    setErrorMessage('')
    try {
      const status = await fetchAssistantStatus(token)
      if (!status?.configured) {
        setConnectionState(AI_CONNECTION_STATES.ERROR)
        setErrorMessage('Backend AI provider is not configured. No model connection was made.')
        return false
      }
      setConnectionState(AI_CONNECTION_STATES.BACKEND_CONNECTED)
      return true
    } catch (err) {
      setConnectionState(AI_CONNECTION_STATES.ERROR)
      setErrorMessage(err?.message || 'Failed to connect to engineering assistant.')
      return false
    } finally {
      setConnecting(false)
    }
  }, [token])

  const sendChat = useCallback(
    async ({ messages, prompt }) => {
      if (!canSendToModel(connectionState)) {
        throw new Error('Model connection is not active. Connect AI Assistant first.')
      }
      if (!token) {
        throw new Error('Sign in required to send messages.')
      }
      setSending(true)
      try {
        return await sendAssistantChat(token, { messages, prompt })
      } finally {
        setSending(false)
      }
    },
    [connectionState, token],
  )

  return {
    connectionState,
    errorMessage,
    connecting,
    sending,
    canSendToModel: canSendToModel(connectionState),
    enableLocalContextOnly,
    disconnect,
    connectToBackend,
    sendChat,
  }
}
