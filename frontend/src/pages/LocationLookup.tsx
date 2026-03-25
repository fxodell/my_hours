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

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  })

  const { data: locations, isLoading } = useQuery({
    queryKey: ['locations', clientId],
    queryFn: () => api.getLocations(clientId),
    enabled: !!clientId,
  })

  const sorted = useMemo(() => {
    if (!locations?.length) return []
    return [...locations].sort((a, b) => locationLabel(a).localeCompare(locationLabel(b)))
  }, [locations])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">Location lookup</h2>
      <p className="text-sm text-gray-600">
        Choose a client to browse locations, job codes, and open directions in Google Maps.
      </p>

      <div>
        <label className="label">Client</label>
        <select
          className="input"
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
        >
          <option value="">Select a client</option>
          {clients?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {!clientId && (
        <p className="text-sm text-gray-500">Select a client to load locations.</p>
      )}

      {clientId && isLoading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      )}

      {clientId && !isLoading && sorted.length === 0 && (
        <p className="text-sm text-gray-500">No active locations for this client.</p>
      )}

      {sorted.length > 0 && (
        <ul className="space-y-3">
          {sorted.map((loc) => {
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
                    Job codes: <span className="font-mono">{codes}</span>
                  </p>
                )}
                {!codes && (
                  <p className="text-xs text-gray-400">No job codes on file for this location.</p>
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
      )}
    </div>
  )
}
