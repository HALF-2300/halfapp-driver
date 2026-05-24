/** Web-only notification sounds (no push). Uses Web Audio when no asset is present. */

let audioCtx

function beep(frequency = 880, durationMs = 120) {
  if (typeof window === 'undefined') return
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return
    if (!audioCtx) audioCtx = new Ctx()
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.frequency.value = frequency
    gain.gain.value = 0.08
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.start()
    setTimeout(() => {
      try {
        osc.stop()
      } catch {
        /* ignore */
      }
    }, durationMs)
  } catch {
    /* ignore */
  }
}

export function playOfferSound(enabled) {
  if (!enabled) return
  if (typeof window === 'undefined') return
  try {
    const audio = new Audio('/sounds/offer.mp3')
    audio.volume = 0.35
    audio.currentTime = 0
    const played = audio.play()
    if (played && typeof played.catch === 'function') {
      played.catch(() => beep())
    }
  } catch {
    beep()
  }
}
