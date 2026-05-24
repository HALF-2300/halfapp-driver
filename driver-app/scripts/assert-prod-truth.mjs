const truthViolations = []

if (process.env.VITE_ALLOW_OFFLINE_MOCK === 'true') {
  truthViolations.push('VITE_ALLOW_OFFLINE_MOCK=true')
}

if (process.env.VITE_USE_MOCK === 'true') {
  truthViolations.push('VITE_USE_MOCK=true')
}

if (process.env.VITE_ENABLE_RIDE_SIMULATION === 'true') {
  truthViolations.push('VITE_ENABLE_RIDE_SIMULATION=true')
}

if (process.env.VITE_ENABLE_GUARD_BYPASS === 'true') {
  truthViolations.push('VITE_ENABLE_GUARD_BYPASS=true')
}

if (truthViolations.length > 0) {
  console.error(
    `Production build blocked: unsafe truth bypass is enabled (${truthViolations.join(', ')}).`,
  )
  process.exit(1)
}
