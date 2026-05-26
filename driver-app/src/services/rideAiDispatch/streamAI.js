/**
 * Advisory AI stream session — AbortController + streamId guard.
 * Does not mutate dispatch state.
 */

let activeController = null
let activeStreamId = null

export function getActiveStreamId() {
  return activeStreamId
}

export function abortActiveStream() {
  if (activeController) {
    activeController.abort()
    activeController = null
  }
}

/**
 * @param {Object} options
 * @param {string} options.streamId
 * @param {(chunk: string, streamId: string) => void} [options.onChunk]
 * @param {(reply: string, streamId: string) => void} [options.onDone]
 * @param {(error: Error, streamId: string) => void} [options.onError]
 * @param {(args: { prompt: string, signal: AbortSignal }) => Promise<{ reply: string }>} options.fetchChat
 * @param {string} options.prompt
 * @returns {Promise<{ streamId: string, aborted: boolean, reply?: string }>}
 */
export async function streamAI({
  streamId,
  prompt,
  fetchChat,
  onChunk,
  onDone,
  onError,
}) {
  abortActiveStream()
  const controller = new AbortController()
  activeController = controller
  activeStreamId = streamId

  const isCurrent = () => activeStreamId === streamId && !controller.signal.aborted

  try {
    const result = await fetchChat({ prompt, signal: controller.signal })
    if (!isCurrent()) {
      return { streamId, aborted: true }
    }
    const reply = result?.reply || ''
    if (onChunk) {
      for (const char of reply) {
        if (!isCurrent()) return { streamId, aborted: true }
        onChunk(char, streamId)
      }
    }
    if (onDone) onDone(reply, streamId)
    if (isCurrent()) {
      activeController = null
      if (activeStreamId === streamId) activeStreamId = null
    }
    return { streamId, aborted: false, reply }
  } catch (err) {
    if (err?.name === 'AbortError') {
      return { streamId, aborted: true }
    }
    if (isCurrent() && onError) onError(err, streamId)
    return { streamId, aborted: !isCurrent() }
  }
}

/**
 * @param {string} streamId
 * @param {string} expectedStreamId
 * @returns {boolean}
 */
export function shouldApplyStreamUpdate(streamId, expectedStreamId) {
  return streamId === expectedStreamId && activeStreamId === expectedStreamId
}
