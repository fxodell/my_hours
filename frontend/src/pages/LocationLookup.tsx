import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as api from '../services/api'
import { googleMapsDirectionsUrl, parseCoord } from '../utils/maps'
import type { Location } from '../types'

function locationLabel(loc: Location): string {
  const parts: string[] = []
  if (loc.site_code) parts.push(`[${loc.site_code}]`)
  if (loc.region) parts.push(loc.region)
  parts.push(loc.site_name)
  return parts.join(' — ')
}

export default function LocationLookup() {
  const [clientId, setClientId] = useState('')
  const [search, setSearch] = useState('')

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  })

  const { data: locations, isLoading } = useQuery({
    queryKey: ['locations', clientId],
    queryFn: () => api.getLocations(clientId),
    enabled: !!clientId,
  })

  const filtered = useMemo(() => {
    if (!locations?.length) return []
    const q = search.trim().toLowerCase()
    const list = q
      ? locations.filter((loc) => {
          const label = locationLabel(loc).toLowerCase()
          const codes = loc.job_codes?.map((j) => j.code.toLowerCase()).join(' ') || ''
          return label.includes(q) || codes.includes(q)
        })
      : locations
    return [...list].sort((a, b) => locationLabel(a).localeCompare(locationLabel(b)))
  }, [locations, search])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">Location lookup</h2>
      <p className="text-sm text-gray-600">
        Choose a client to browse locations, site codes, and open directions in Google Maps.
      </p>

      <div>
        <label className="label">Client</label>
        <select
          className="input"
          value={clientId}
          onChange={(e) => { setClientId(e.target.value); setSearch('') }}
        >
          <option value="">Select a client</option>
          {clients?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {clientId && locations && locations.length > 0 && (
        <div>
          <input
            type="text"
            className="input"
            placeholder="Search by site name, region, or site code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      )}

      {!clientId && (
        <p className="text-sm text-gray-500">Select a client to load locations.</p>
      )}

      {clientId && isLoading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      )}

      {clientId && !isLoading && filtered.length === 0 && !search && (
        <p className="text-sm text-gray-500">No active locations for this client.</p>
      )}

      {clientId && !isLoading && filtered.length === 0 && search && (
        <p className="text-sm text-gray-500">No locations match "{search}".</p>
      )}

      {filtered.length > 0 && (
        <>
        <p className="text-xs text-gray-400">{filtered.length} location{filtered.length !== 1 ? 's' : ''}{search ? ' matching' : ''}</p>
        <ul className="space-y-3">
          {filtered.map((loc) => {
            const lat = parseCoord(loc.latitude)
            const lng = parseCoord(loc.longitude)
            const mapsUrl =
              lat !== null && lng !== null ? googleMapsDirectionsUrl(lat, lng) : null
            const codes = loc.job_codes?.length
              ? loc.job_codes.map((j) => j.code).join(', ')
              : null
            return (
              <li
                key={loc.id}
                className="bg-white rounded-xl border border-gray-200 p-4 space-y-2"
              >
                <div className="font-medium text-gray-900">{locationLabel(loc)}</div>
                {loc.site_code && (
                  <p className="text-xs text-gray-500">
                    Site code: <span className="font-mono">{loc.site_code}</span>
                  </p>
                )}
                {codes && (
                  <p className="text-sm text-gray-700">
                    Site codes: <span className="font-mono">{codes}</span>
                  </p>
                )}
                {!codes && (
                  <p className="text-xs text-gray-400">No site codes on file for this location.</p>
                )}
                {lat !== null && lng !== null && (
                  <p className="text-xs text-gray-500 font-mono">
                    GPS: {lat}, {lng}
                  </p>
                )}
                {mapsUrl ? (
                  <a
                    href={mapsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-primary-600 font-medium"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                    </svg>
                    Directions in Google Maps
                  </a>
                ) : (
                  <p className="text-xs text-amber-700">No GPS coordinates on file yet.</p>
                )}
              </li>
            )
          })}
        </ul>
        </>
      )}
    </div>
  )
}
