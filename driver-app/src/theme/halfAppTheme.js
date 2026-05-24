/** HalfApp driver cockpit visual tokens */
export const halfAppTheme = {
  background: '#050814',
  surface: 'rgba(8, 13, 28, 0.72)',
  surfaceStrong: 'rgba(10, 16, 34, 0.88)',
  border: 'rgba(255,255,255,0.10)',
  textPrimary: '#F8FAFC',
  textSecondary: '#AAB6C8',
  accent: '#3B82F6',
  accentGreen: '#34D399',
  warning: '#F59E0B',
  danger: '#EF4444',
  radiusLarge: '28px',
  radiusMedium: '18px',
  blur: 'blur(18px)',
}

export function formatCurrency(n) {
  const num = Number(n)
  if (!Number.isFinite(num)) return '—'
  return `$${num.toFixed(2)}`
}
