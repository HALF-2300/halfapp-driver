/** Apply persisted driver theme to document root (HALFAPP_DRIVER_GAP_FILL_SLICE_01). */

export function applyTheme(theme) {
  const root = document.documentElement
  const value = (theme || 'system').trim().toLowerCase()

  if (!value || value === 'system') {
    root.removeAttribute('data-theme')
    return
  }

  root.setAttribute('data-theme', value)
}

export function resolveSystemTheme() {
  if (typeof window === 'undefined' || !window.matchMedia) return 'dark'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}
