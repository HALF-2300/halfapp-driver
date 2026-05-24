/**
 * Map overlay markers for official traffic signals (visual only).
 *
 * @param {Array<{ id?: string, title?: string, latitude: number, longitude: number, kind?: string, severity?: string }>} signals
 * @returns {import('./experimentalMapMarkers.js').ExperimentalMapMarker[]}
 */
export function trafficSignalsToMapMarkers(signals = []) {
  return signals
    .filter((s) => Number.isFinite(Number(s.latitude)) && Number.isFinite(Number(s.longitude)))
    .slice(0, 30)
    .map((s, idx) => ({
      id: `traffic-${s.id || idx}`,
      kind: 'traffic_incident',
      label: (s.title || 'Traffic alert').slice(0, 40),
      latitude: Number(s.latitude),
      longitude: Number(s.longitude),
      source: 'traffic_signal',
      severity: s.severity || 'medium',
    }))
}
