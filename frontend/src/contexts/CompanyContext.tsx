import { createContext, useContext, useState, useMemo } from 'react'
import { useAuth } from './AuthContext'
import type { Company } from '../types'

interface CompanyContextType {
  /** The company currently selected for viewing. null = own company. */
  selectedCompany: Company | null
  /** Set a company to view, or null to return to own company. */
  setSelectedCompany: (company: Company | null) => void
  /** The company_id query param to pass to API calls. undefined = use default (own company). */
  companyParam: string | undefined
  /** Whether the user is a super-admin who can switch companies. */
  canSwitchCompany: boolean
}

const CompanyContext = createContext<CompanyContextType | undefined>(undefined)

export function CompanyProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)

  const canSwitchCompany = !!user?.is_super_admin

  const companyParam = useMemo(
    () => canSwitchCompany && selectedCompany ? selectedCompany.id : undefined,
    [canSwitchCompany, selectedCompany]
  )

  return (
    <CompanyContext.Provider value={{ selectedCompany, setSelectedCompany, companyParam, canSwitchCompany }}>
      {children}
    </CompanyContext.Provider>
  )
}

export function useCompany() {
  const context = useContext(CompanyContext)
  if (!context) {
    throw new Error('useCompany must be used within a CompanyProvider')
  }
  return context
}
