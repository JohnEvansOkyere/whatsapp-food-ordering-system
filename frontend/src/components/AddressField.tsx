import { useCallback, useEffect, useRef, useState } from 'react'
import { Crosshair, Loader2, MapPin, Pencil, Search } from 'lucide-react'
import {
  ACCRA_CENTER,
  AddressSuggestion,
  LatLngLiteral,
  createConfirmationMap,
  fetchAddressSuggestions,
  getBrowserLocation,
  mapsConfigured,
  resetAutocompleteSession,
  resolveSuggestion,
  reverseGeocode,
} from '@/lib/googleMaps'

export interface DeliveryLocation {
  address: string
  latitude?: number
  longitude?: number
  placeId?: string
  /** How the address was captured — surfaced to staff as "pinned" or not. */
  source: 'search' | 'gps' | 'map' | 'typed'
}

interface AddressFieldProps {
  value: DeliveryLocation | null
  onChange: (next: DeliveryLocation | null) => void
  /** Biases predictions towards the branch the customer is ordering from. */
  center?: LatLngLiteral
}

const DEBOUNCE_MS = 300

/** Rough metres between two points — good enough to ignore idle jitter. */
function metresBetween(a: LatLngLiteral, b: LatLngLiteral): number {
  const dLat = (a.lat - b.lat) * 111320
  const dLng = (a.lng - b.lng) * 111320 * Math.cos((a.lat * Math.PI) / 180)
  return Math.sqrt(dLat * dLat + dLng * dLng)
}

export default function AddressField({ value, onChange, center }: AddressFieldProps) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [searching, setSearching] = useState(false)
  const [locating, setLocating] = useState(false)
  const [notice, setNotice] = useState('')
  const [mapsDown, setMapsDown] = useState(!mapsConfigured)

  const mapRef = useRef<HTMLDivElement | null>(null)
  const mapHandle = useRef<{ setCenter: (next: LatLngLiteral) => void } | null>(null)
  const pinnedPoint = useRef<LatLngLiteral | null>(null)
  const panTimer = useRef<number | null>(null)

  const bias = center || ACCRA_CENTER
  const pinned = Boolean(value?.latitude && value?.longitude)

  /* ── Predictions ─────────────────────────────────────────────────────── */
  useEffect(() => {
    if (mapsDown || pinned || query.trim().length < 3) {
      setSuggestions([])
      return
    }
    let cancelled = false
    setSearching(true)
    const timer = window.setTimeout(async () => {
      try {
        const results = await fetchAddressSuggestions(query, bias)
        if (!cancelled) setSuggestions(results)
      } catch {
        // A failed lookup must never block checkout — fall back to typing.
        if (!cancelled) {
          setSuggestions([])
          setMapsDown(true)
          setNotice('Address search is unavailable. Type your address instead.')
        }
      } finally {
        if (!cancelled) setSearching(false)
      }
    }, DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [query, bias, mapsDown, pinned])

  /* ── Confirmation map ────────────────────────────────────────────────── */
  const handlePan = useCallback(
    (next: LatLngLiteral) => {
      const previous = pinnedPoint.current
      // The map fires `idle` once on load, and again for sub-metre jitter.
      if (previous && metresBetween(previous, next) < 20) return
      pinnedPoint.current = next

      if (panTimer.current) window.clearTimeout(panTimer.current)
      panTimer.current = window.setTimeout(async () => {
        try {
          const resolved = await reverseGeocode(next)
          onChange({
            address: resolved?.address || value?.address || '',
            latitude: next.lat,
            longitude: next.lng,
            placeId: resolved?.placeId,
            source: 'map',
          })
        } catch {
          // Keep the pin the customer chose even if the label lookup fails.
          onChange({
            address: value?.address || '',
            latitude: next.lat,
            longitude: next.lng,
            source: 'map',
          })
        }
      }, 500)
    },
    [onChange, value?.address]
  )

  useEffect(() => {
    if (!pinned || mapsDown || !mapRef.current) return
    const point = { lat: value!.latitude!, lng: value!.longitude! }

    if (mapHandle.current) {
      // Only recentre when the change came from outside the map itself.
      const current = pinnedPoint.current
      if (!current || metresBetween(current, point) > 20) {
        pinnedPoint.current = point
        mapHandle.current.setCenter(point)
      }
      return
    }

    let cancelled = false
    pinnedPoint.current = point
    createConfirmationMap(mapRef.current, point, handlePan)
      .then(handle => {
        if (cancelled) return
        mapHandle.current = handle
      })
      .catch(() => {
        if (!cancelled) setMapsDown(true)
      })

    return () => {
      cancelled = true
    }
  }, [pinned, mapsDown, value, handlePan])

  useEffect(() => {
    if (!pinned) mapHandle.current = null
  }, [pinned])

  /* ── Actions ─────────────────────────────────────────────────────────── */
  const pickSuggestion = async (suggestion: AddressSuggestion) => {
    setSearching(true)
    setNotice('')
    try {
      const resolved = await resolveSuggestion(suggestion)
      if (!resolved) throw new Error('No location for that place')
      setSuggestions([])
      setQuery('')
      onChange({ ...resolved, source: 'search' })
    } catch {
      setNotice('We could not place that address. Try another or use your location.')
    } finally {
      setSearching(false)
    }
  }

  const useMyLocation = async () => {
    setLocating(true)
    setNotice('')
    try {
      const point = await getBrowserLocation()
      let address = ''
      let placeId: string | undefined
      try {
        const resolved = await reverseGeocode(point)
        address = resolved?.address || ''
        placeId = resolved?.placeId
      } catch {
        setNotice('We pinned your location but could not name the street. Adjust the map if needed.')
      }
      setSuggestions([])
      setQuery('')
      resetAutocompleteSession()
      onChange({ address, latitude: point.lat, longitude: point.lng, placeId, source: 'gps' })
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'We could not read your location.')
    } finally {
      setLocating(false)
    }
  }

  const useTypedAddress = () => {
    const typed = query.trim()
    if (typed.length < 3) return
    setSuggestions([])
    onChange({ address: typed, source: 'typed' })
  }

  const clearSelection = () => {
    setQuery(value?.address || '')
    pinnedPoint.current = null
    mapHandle.current = null
    resetAutocompleteSession()
    onChange(null)
  }

  const labelClass = 'mb-1.5 block text-xs font-bold uppercase tracking-wider text-white/70'

  /* ── Confirmed state ─────────────────────────────────────────────────── */
  if (value) {
    return (
      <div>
        <label className={labelClass}>Delivery Address *</label>
        <div className="overflow-hidden rounded-xl border border-white/10 bg-white/5">
          {pinned && !mapsDown && (
            <div className="relative h-32 w-full bg-white/5">
              <div ref={mapRef} className="h-full w-full" />
              {/* Fixed centre pin: panning the map moves the drop point. */}
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center pb-4">
                <MapPin size={26} className="drop-shadow-lg" fill="#f7b32b" color="#1a0a00" />
              </div>
              <p className="pointer-events-none absolute bottom-1 left-0 right-0 text-center text-[10px] font-semibold text-white drop-shadow">
                Drag the map to move the pin
              </p>
            </div>
          )}
          <div className="flex items-start gap-2.5 px-3 py-2.5">
            <MapPin size={15} className="mt-0.5 flex-shrink-0 text-[#f7b32b]" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold leading-snug text-white">
                {value.address || 'Pinned location'}
              </p>
              <p className="mt-0.5 text-[10px] text-white/60">
                {pinned ? 'Pinned on the map' : 'Not on the map — the rider will call you'}
              </p>
            </div>
            <button
              type="button"
              onClick={clearSelection}
              className="flex flex-shrink-0 items-center gap-1 rounded-lg bg-white/10 px-2 py-1 text-[10px] font-bold text-white/80 transition hover:bg-white/20"
            >
              <Pencil size={11} />
              Change
            </button>
          </div>
        </div>
        {notice && <p className="mt-1.5 text-[11px] text-[#f7b32b]">{notice}</p>}
      </div>
    )
  }

  /* ── Search state ────────────────────────────────────────────────────── */
  return (
    <div>
      <label className={labelClass} htmlFor="delivery-address">
        Delivery Address *
      </label>
      <div className="relative">
        <Search
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/40"
        />
        <input
          id="delivery-address"
          type="text"
          autoComplete="street-address"
          value={query}
          maxLength={500}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') {
              e.preventDefault()
              if (suggestions.length > 0) pickSuggestion(suggestions[0])
              else useTypedAddress()
            }
          }}
          placeholder={mapsDown ? 'Where should we deliver?' : 'Search your street, area or landmark'}
          className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-9 pr-9 text-sm text-white placeholder-white/50 outline-none transition focus:border-[#f7b32b] focus:ring-1 focus:ring-[#f7b32b]"
        />
        {searching && (
          <Loader2
            size={14}
            className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-[#f7b32b]"
          />
        )}
      </div>

      {suggestions.length > 0 && (
        <ul className="mt-1.5 overflow-hidden rounded-xl border border-white/10 bg-[#222]">
          {suggestions.slice(0, 5).map(suggestion => (
            <li key={suggestion.placeId}>
              <button
                type="button"
                onClick={() => pickSuggestion(suggestion)}
                className="flex w-full items-start gap-2.5 border-b border-white/5 px-3 py-2.5 text-left transition last:border-0 hover:bg-white/10"
              >
                <MapPin size={13} className="mt-0.5 flex-shrink-0 text-white/50" />
                <span className="min-w-0">
                  <span className="block truncate text-sm text-white">{suggestion.primary}</span>
                  {suggestion.secondary && (
                    <span className="block truncate text-[11px] text-white/55">
                      {suggestion.secondary}
                    </span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={useMyLocation}
          disabled={locating}
          className="flex items-center gap-1.5 rounded-xl border border-[#f7b32b]/40 bg-[#f7b32b]/10 px-3 py-2 text-xs font-bold text-[#f7b32b] transition hover:bg-[#f7b32b]/20 disabled:opacity-60"
        >
          {locating ? <Loader2 size={13} className="animate-spin" /> : <Crosshair size={13} />}
          {locating ? 'Finding you…' : 'Use my location'}
        </button>
        {query.trim().length >= 3 && (
          <button
            type="button"
            onClick={useTypedAddress}
            className="rounded-xl border border-white/10 px-3 py-2 text-xs font-bold text-white/70 transition hover:border-white/25 hover:text-white"
          >
            Use “{query.trim().slice(0, 24)}{query.trim().length > 24 ? '…' : ''}”
          </button>
        )}
      </div>

      {notice && <p className="mt-1.5 text-[11px] text-[#f7b32b]">{notice}</p>}
    </div>
  )
}
