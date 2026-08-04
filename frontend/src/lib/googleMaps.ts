/**
 * Lazy loader for the Google Maps JS API.
 *
 * The bootstrap script is only injected when a customer actually reaches the
 * address field, so browsing the menu costs nothing. Every helper here is
 * optional by design: checkout must still work when the key is missing or the
 * network call fails, so callers fall back to a plain typed address.
 */

/** Minimal shapes for the few Maps APIs this app touches. */
export interface LatLngLiteral {
  lat: number
  lng: number
}

export interface PlaceResult {
  address: string
  latitude: number
  longitude: number
  placeId?: string
}

interface PlacePrediction {
  placeId: string
  text: { toString: () => string }
  mainText?: { toString: () => string }
  secondaryText?: { toString: () => string }
  toPlace: () => {
    fetchFields: (options: { fields: string[] }) => Promise<unknown>
    id?: string
    formattedAddress?: string | null
    location?: { lat: () => number; lng: () => number } | null
  }
}

export interface AddressSuggestion {
  placeId: string
  primary: string
  secondary: string
  prediction: PlacePrediction
}

type ImportLibrary = (name: string) => Promise<Record<string, unknown>>

declare global {
  interface Window {
    google?: { maps?: { importLibrary?: ImportLibrary } }
  }
}

/** Central Accra — used to bias results when the branch has no coordinates. */
export const ACCRA_CENTER: LatLngLiteral = { lat: 5.6037, lng: -0.187 }

export const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ''

/** False when no key is configured — callers then render the plain text field. */
export const mapsConfigured = Boolean(googleMapsApiKey)

const CALLBACK_NAME = '__foodOrderingMapsReady'

let bootstrapPromise: Promise<ImportLibrary> | null = null

/** Injects the bootstrap script once and resolves with `importLibrary`. */
export function loadGoogleMaps(): Promise<ImportLibrary> {
  if (!mapsConfigured) {
    return Promise.reject(new Error('Google Maps key is not configured'))
  }
  const existing = window.google?.maps?.importLibrary
  if (existing) return Promise.resolve(existing)
  if (bootstrapPromise) return bootstrapPromise

  bootstrapPromise = new Promise<ImportLibrary>((resolve, reject) => {
    const globalWindow = window as unknown as Record<string, unknown>
    globalWindow[CALLBACK_NAME] = () => {
      const importLibrary = window.google?.maps?.importLibrary
      if (importLibrary) resolve(importLibrary)
      else reject(new Error('Google Maps loaded without importLibrary'))
    }

    const script = document.createElement('script')
    script.src =
      'https://maps.googleapis.com/maps/api/js' +
      `?key=${encodeURIComponent(googleMapsApiKey)}` +
      '&libraries=places,geocoding' +
      '&loading=async' +
      `&callback=${CALLBACK_NAME}`
    script.async = true
    script.onerror = () => {
      bootstrapPromise = null
      reject(new Error('Google Maps failed to load'))
    }
    document.head.appendChild(script)
  })

  return bootstrapPromise
}

async function importLibrary(name: string): Promise<Record<string, unknown>> {
  const load = await loadGoogleMaps()
  return load(name)
}

/* eslint-disable @typescript-eslint/no-explicit-any */

let sessionToken: unknown = null

/** Starts a fresh billing session — call after a place is picked. */
export function resetAutocompleteSession() {
  sessionToken = null
}

/**
 * Address predictions for `input`, biased towards `center`, restricted to
 * Ghana. Returns an empty list rather than throwing on an empty query.
 */
export async function fetchAddressSuggestions(
  input: string,
  center: LatLngLiteral
): Promise<AddressSuggestion[]> {
  const query = input.trim()
  if (query.length < 3) return []

  const places = (await importLibrary('places')) as any
  if (!sessionToken) sessionToken = new places.AutocompleteSessionToken()

  const { suggestions } = await places.AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input: query,
    sessionToken,
    includedRegionCodes: ['gh'],
    locationBias: { center, radius: 40000 },
  })

  return (suggestions || [])
    .map((suggestion: any) => suggestion.placePrediction)
    .filter(Boolean)
    .map((prediction: any) => ({
      placeId: prediction.placeId,
      primary: prediction.mainText?.toString() || prediction.text?.toString() || '',
      secondary: prediction.secondaryText?.toString() || '',
      prediction,
    }))
}

/** Resolves a prediction into a confirmed address with coordinates. */
export async function resolveSuggestion(
  suggestion: AddressSuggestion
): Promise<PlaceResult | null> {
  const place = suggestion.prediction.toPlace() as any
  await place.fetchFields({ fields: ['formattedAddress', 'location', 'displayName'] })
  resetAutocompleteSession()

  const location = place.location
  if (!location) return null

  const formatted = place.formattedAddress || suggestion.primary
  const label = suggestion.primary && !formatted.startsWith(suggestion.primary)
    ? `${suggestion.primary}, ${formatted}`
    : formatted

  return {
    address: label,
    latitude: location.lat(),
    longitude: location.lng(),
    placeId: place.id || suggestion.placeId,
  }
}

/** Best-effort street address for a pair of coordinates. */
export async function reverseGeocode(point: LatLngLiteral): Promise<PlaceResult | null> {
  const geocoding = (await importLibrary('geocoding')) as any
  const geocoder = new geocoding.Geocoder()
  const { results } = await geocoder.geocode({ location: point })
  const best = results?.[0]
  if (!best) return null

  return {
    address: best.formatted_address,
    latitude: point.lat,
    longitude: point.lng,
    placeId: best.place_id,
  }
}

/** Wraps `navigator.geolocation` in a promise with a sane timeout. */
export function getBrowserLocation(): Promise<LatLngLiteral> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('This browser cannot share your location'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      position =>
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        }),
      error => {
        reject(
          new Error(
            error.code === error.PERMISSION_DENIED
              ? 'Location permission was blocked. Search for your address instead.'
              : 'We could not read your location. Search for your address instead.'
          )
        )
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    )
  })
}

/**
 * Renders a small confirmation map centred on `point`. The caller overlays a
 * fixed pin, so panning the map re-picks the drop point — no marker library
 * and no Map ID required.
 */
export async function createConfirmationMap(
  container: HTMLElement,
  point: LatLngLiteral,
  onCenterChanged: (next: LatLngLiteral) => void
): Promise<{ setCenter: (next: LatLngLiteral) => void }> {
  const maps = (await importLibrary('maps')) as any
  const map = new maps.Map(container, {
    center: point,
    zoom: 17,
    disableDefaultUI: true,
    gestureHandling: 'greedy',
    clickableIcons: false,
  })

  map.addListener('idle', () => {
    const center = map.getCenter()
    if (!center) return
    onCenterChanged({ lat: center.lat(), lng: center.lng() })
  })

  return {
    setCenter: (next: LatLngLiteral) => map.setCenter(next),
  }
}
