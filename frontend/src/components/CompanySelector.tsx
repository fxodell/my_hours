import { useQuery } from '@tanstack/react-query'
import { useCompany } from '../contexts/CompanyContext'
import * as api from '../services/api'

/**
 * Company selector dropdown for super-admins.
 * Shows at the top of pages that support cross-company viewing.
 * Renders nothing for non-super-admins.
 */
export default function CompanySelector() {
  const { canSwitchCompany, selectedCompany, setSelectedCompany } = useCompany()

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.getCompanies(true),
    enabled: canSwitchCompany,
  })

  if (!canSwitchCompany) return null

  return (
    <div className="mb-4 flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-2">
      <label className="text-sm font-medium text-indigo-700 whitespace-nowrap">
        Viewing company:
      </label>
      <select
        value={selectedCompany?.id ?? ''}
        onChange={(e) => {
          if (e.target.value === '') {
            setSelectedCompany(null)
          } else {
            const co = companies.find(c => c.id === e.target.value)
            if (co) setSelectedCompany(co)
          }
        }}
        className="flex-1 rounded-md border-indigo-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
      >
        <option value="">My Company</option>
        {companies.map(co => (
          <option key={co.id} value={co.id}>{co.name}</option>
        ))}
      </select>
    </div>
  )
}
