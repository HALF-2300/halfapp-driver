import React, { useEffect, useMemo, useRef } from 'react'

import L from 'leaflet'

import 'leaflet/dist/leaflet.css'

import {
  MAP_CENTER_SOURCES,
  mapLocationDiagnosticLabel,
} from '../utils/mapCenterPresentation.js'
import { getMapDisplayConfig, getRouteStyle } from '../services/mapProvider.js'



/**

 * Experimental driver cockpit map (Leaflet + OpenStreetMap).

 * Visualization only — never marketplace or dispatch truth.

 */



const mapDisplay = getMapDisplayConfig()
const TILE_URL = mapDisplay.tileUrl
const TILE_ATTRIBUTION = mapDisplay.attribution



const MARKER_COLORS = {
  driver: '#60a5fa',
  ride_pickup: '#34d399',
  ride_dropoff: '#fb7185',
  traffic_incident: '#fbbf24',
}

const ROUTE_LINE_STYLE = getRouteStyle()



function escapeHtml(value) {

  return String(value)

    .replace(/&/g, '&amp;')

    .replace(/</g, '&lt;')

    .replace(/>/g, '&gt;')

    .replace(/"/g, '&quot;')

}



function makePinIcon(color, label, kind = 'default') {
  const kindClass = kind === 'driver' ? 'halfapp-map-pin__wrap--driver' : ''
  return L.divIcon({
    className: 'halfapp-map-pin',
    html: `<div class="halfapp-map-pin__wrap ${kindClass}" style="--pin-color:${color}">
      <span class="halfapp-map-pin__dot"></span>
      <span class="halfapp-map-pin__label">${escapeHtml(label)}</span>
    </div>`,
    iconSize: [1, 1],
    iconAnchor: [14, 14],
  })
}



/**

 * @param {import('../utils/experimentalMapMarkers.js').ExperimentalMapMarker[]} markers

 */

function collectLatLngs(markers) {

  return markers.map((m) => [m.latitude, m.longitude])

}



/**

 * @param {import('../utils/experimentalMapMarkers.js').ExperimentalMapMarker[]} markers

 */

function buildVisualPolyline(markers) {

  const pickup = markers.find((m) => m.kind === 'ride_pickup')

  const dropoff = markers.find((m) => m.kind === 'ride_dropoff')

  if (!pickup || !dropoff) return []

  return [

    [pickup.latitude, pickup.longitude],

    [dropoff.latitude, dropoff.longitude],

  ]

}



function ExperimentalMapDisclaimer() {
  return (
    <p className="sr-only" data-testid="experimental-map-disclaimer">
      Experimental map visualization only. Dispatch and ride truth are backend-owned.
    </p>
  )
}

/** @param {L.Map | null | undefined} map */
function mapNodeIsReady(map) {
  if (!map) return false
  if (map._removed) return false
  const el = map.getContainer?.()
  return Boolean(el?.isConnected && el.offsetParent !== null)
}

function isValidLatLng(lat, lng) {
  const la = Number(lat)
  const ln = Number(lng)
  return (
    Number.isFinite(la) &&
    Number.isFinite(ln) &&
    la >= -90 &&
    la <= 90 &&
    ln >= -180 &&
    ln <= 180
  )
}

/** @returns {[number, number] | null} */
function toLatLngPair(lat, lng) {
  return isValidLatLng(lat, lng) ? [Number(lat), Number(lng)] : null
}



function MapLocatingOverlay() {

  return (

    <div

      className="map-locating-overlay absolute inset-0 z-[4] flex items-center justify-center"

      data-testid="map-locating-state"

      role="status"

      aria-live="polite"

    >

      <div className="map-locating-card rounded-2xl border border-white/10 bg-[rgba(7,12,26,0.92)] px-6 py-5 text-center shadow-2xl backdrop-blur-md">

        <div className="map-locating-spinner mx-auto mb-3 h-8 w-8 rounded-full border-2 border-slate-600 border-t-cyan-400" />

        <p className="text-sm font-medium text-slate-100">Finding your location...</p>

      </div>

    </div>

  )

}



/**

 * @param {Object} props

 * @param {import('../utils/experimentalMapMarkers.js').ExperimentalMapMarker[]} props.markers

 * @param {{ lat: number, lng: number, zoom: number } | null} [props.mapCenter]

 * @param {import('../utils/mapCenterPresentation.js').MapCenterSource} [props.centerSource]

 * @param {boolean} [props.locating]

 * @param {boolean} [props.showMapCanvas]

 * @param {import('../utils/mapLocationSurface.js').MapSurfaceMode} [props.surfaceMode]
 * @param {import('../utils/mapRouteFoundation.js').ReturnType<import('../utils/mapRouteFoundation.js').resolveMapRouteFoundation>} [props.routeFoundation]

 */

export default function MapView({
  markers = [],
  mapCenter = null,
  centerSource = MAP_CENTER_SOURCES.NONE,
  locating = false,
  showMapCanvas = false,
  surfaceMode = 'neutral',
  routeFoundation = null,
  className = '',
  onMapReady = null,
}) {

  const containerRef = useRef(null)

  const mapRef = useRef(null)

  const leafletMarkersRef = useRef([])

  const polylineRef = useRef(null)



  const boundsPoints = useMemo(() => collectLatLngs(markers), [markers])

  const polylineLatLngs = useMemo(() => buildVisualPolyline(markers), [markers])

  const hasDeviceMarker = markers.some(

    (m) => m.id === 'device-driver' || m.id === 'dev-fallback-driver'

  )

  const showDevFallbackLabel = centerSource === MAP_CENTER_SOURCES.DEV_FALLBACK



  const validBoundsPoints = useMemo(
    () =>
      boundsPoints.filter((pair) => isValidLatLng(pair[0], pair[1])),
    [boundsPoints]
  )

  const validPolylineLatLngs = useMemo(
    () =>
      polylineLatLngs.filter((pair) => isValidLatLng(pair[0], pair[1])),
    [polylineLatLngs]
  )

  useEffect(() => {
    if (!showMapCanvas) {
      if (mapRef.current) {
        try {
          mapRef.current.remove()
        } catch {
          /* map may already be torn down */
        }
        mapRef.current = null
        leafletMarkersRef.current = []
        polylineRef.current = null
      }
      return undefined
    }

    if (!containerRef.current || mapRef.current) return undefined

    const centerPair = mapCenter
      ? toLatLngPair(mapCenter.lat, mapCenter.lng)
      : validBoundsPoints[0] ?? null
    if (!centerPair) return undefined

    const initialZoom = mapCenter?.zoom ?? 13

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    })
    map.setView(centerPair, initialZoom)

    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTRIBUTION,
      maxZoom: 19,
    }).addTo(map)

    mapRef.current = map
    onMapReady?.(map)

    const resizeObserver = new ResizeObserver(() => {
      const active = mapRef.current
      if (!mapNodeIsReady(active)) return
      try {
        active.invalidateSize()
      } catch {
        /* ignore mid-layout */
      }
    })
    resizeObserver.observe(containerRef.current)

    const resizeTimer = window.setTimeout(() => {
      const active = mapRef.current
      if (!mapNodeIsReady(active)) return
      try {
        active.invalidateSize()
      } catch {
        /* ignore */
      }
    }, 50)

    return () => {
      window.clearTimeout(resizeTimer)
      resizeObserver.disconnect()
      onMapReady?.(null)
      try {
        map.remove()
      } catch {
        /* ignore */
      }
      mapRef.current = null
      leafletMarkersRef.current = []
      polylineRef.current = null
    }
  }, [showMapCanvas, mapCenter?.lat, mapCenter?.lng, mapCenter?.zoom, onMapReady])

  useEffect(() => {
    const map = mapRef.current
    if (!mapNodeIsReady(map) || !showMapCanvas || !mapCenter) return
    const centerPair = toLatLngPair(mapCenter.lat, mapCenter.lng)
    if (!centerPair) return
    try {
      map.setView(centerPair, mapCenter.zoom ?? map.getZoom())
    } catch {
      /* map may be mid-teardown */
    }
  }, [showMapCanvas, mapCenter?.lat, mapCenter?.lng, mapCenter?.zoom])

  useEffect(() => {
    if (!showMapCanvas) return undefined

    const frame = requestAnimationFrame(() => {
      const map = mapRef.current
      if (!mapNodeIsReady(map)) return

      try {
        for (const marker of leafletMarkersRef.current) {
          try {
            marker.remove()
          } catch {
            /* marker may already be detached */
          }
        }
        leafletMarkersRef.current = []

        for (const marker of markers) {
          const pair = toLatLngPair(marker.latitude, marker.longitude)
          if (!pair) continue
          const color = MARKER_COLORS[marker.kind] || '#94a3b8'
          leafletMarkersRef.current.push(
            L.marker(pair, {
              icon: makePinIcon(color, marker.label, marker.kind),
            }).addTo(map)
          )
        }

        if (polylineRef.current) {
          try {
            polylineRef.current.remove()
          } catch {
            /* ignore */
          }
          polylineRef.current = null
        }

        if (validPolylineLatLngs.length >= 2) {
          polylineRef.current = L.polyline(validPolylineLatLngs, ROUTE_LINE_STYLE).addTo(map)
        }

        if (validBoundsPoints.length >= 2) {
          map.fitBounds(validBoundsPoints, {
            paddingTopLeft: [40, 40],
            paddingBottomRight: [220, 48],
            maxZoom: 15,
          })
        } else if (validBoundsPoints.length === 1 && !mapCenter) {
          map.setView(validBoundsPoints[0], 14)
        }

        if (mapNodeIsReady(map)) {
          try {
            map.invalidateSize()
          } catch {
            /* ignore */
          }
        }
      } catch {
        /* Leaflet can throw if the map is torn down mid-update */
      }
    })

    return () => window.cancelAnimationFrame(frame)
  }, [showMapCanvas, validBoundsPoints, validPolylineLatLngs, markers, mapCenter])



  const diagnosticSourceNote = useMemo(
    () => mapLocationDiagnosticLabel(centerSource, markers),
    [centerSource, markers]
  )



  const showLocatingOverlay = locating || surfaceMode === 'locating'

  const shellClassName = [

    'map-cockpit-shell relative h-full w-full overflow-hidden',

    showLocatingOverlay && showMapCanvas ? 'map-cockpit-shell--locating-blur' : '',

    !showMapCanvas ? 'map-cockpit-shell--neutral' : '',

    className,

  ]

    .filter(Boolean)

    .join(' ')



  return (

    <div

      className={shellClassName}

      data-testid="map-view"

      data-map-surface={surfaceMode}

      data-map-center-source={centerSource}

      data-map-center-lat={mapCenter?.lat ?? ''}

      data-map-center-lng={mapCenter?.lng ?? ''}

      data-map-center-zoom={mapCenter?.zoom ?? ''}

      data-map-locating={showLocatingOverlay ? 'true' : 'false'}
      data-route-provider={routeFoundation?.routeProvider ?? ''}
      data-traffic-provider={routeFoundation?.trafficProvider ?? ''}
      data-traffic-aware={routeFoundation?.trafficAware ? 'true' : 'false'}
      data-traffic-signal-aware={routeFoundation?.trafficSignalAware ? 'true' : 'false'}
      data-route-confidence={routeFoundation?.routeConfidence ?? ''}
      data-route-calculated-at={routeFoundation?.routeCalculatedAt ?? ''}
      data-google-fallback={routeFoundation?.googleMapsFallbackEnabled ? 'true' : 'false'}
      data-mapbox-traffic={routeFoundation?.mapboxTrafficEnabled ? 'true' : 'false'}
    >

      {surfaceMode === 'active_map' && mapCenter && (

        <span

          className="sr-only"

          data-testid="map-surface-active"

          data-map-lat={mapCenter.lat}

          data-map-lng={mapCenter.lng}

        >

          Active map centered on device or ride visualization

        </span>

      )}


      {showMapCanvas ? (

        <div ref={containerRef} className="absolute inset-0 z-0" aria-label="Experimental driver map" />

      ) : (

        <div className="map-neutral-backdrop absolute inset-0 z-0" aria-hidden="true" />

      )}

      <ExperimentalMapDisclaimer />

      {showLocatingOverlay && <MapLocatingOverlay />}

      {hasDeviceMarker && !showLocatingOverlay && (

        <span className="sr-only" data-testid="map-device-location-marker">

          Device location marker on map

        </span>

      )}

      {showDevFallbackLabel && (
        <span className="sr-only" data-testid="map-dev-fallback-label">
          DEV FALLBACK LOCATION — not real driver GPS
        </span>
      )}

      <span className="sr-only" data-testid="map-location-source-label">
        {diagnosticSourceNote}
      </span>

    </div>

  )

}


