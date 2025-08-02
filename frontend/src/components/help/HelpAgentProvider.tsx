"use client"

import { useAssistantAgentStore } from '@/stores/helpAgentStore'
import { usePathname } from 'next/navigation'
import { useEffect } from 'react'

interface HelpAgentProviderProps {
  children: React.ReactNode
}

// Map pathnames to readable page names
const getPageNameFromPath = (pathname: string): string => {
  if (pathname === '/' || pathname === '/login') return 'Homepage'
  if (pathname === '/dashboard') return 'Dashboard'
  if (pathname === '/documents') return 'Document Intake'
  if (pathname === '/contracts') return 'Contract Generator'
  if (pathname === '/signatures') return 'Signature Tracker'
  if (pathname === '/review') return 'Contract Review'
  if (pathname === '/admin') return 'Admin Panel'

  // Handle dynamic routes
  if (pathname.startsWith('/contracts/')) return 'Contract Details'
  if (pathname.startsWith('/documents/')) return 'Document Details'
  if (pathname.startsWith('/signatures/')) return 'Signature Details'

  return 'Application'
}

export function HelpAgentProvider({ children }: HelpAgentProviderProps) {
  const pathname = usePathname()
  const updateContext = useAssistantAgentStore((state) => state.updateContext)

  useEffect(() => {
    const pageName = getPageNameFromPath(pathname)

    // Mock available files and contracts based on page
    const getContextualData = (page: string) => {
      const baseContext = {
        page: pageName,
        availableFiles: ['Johnson_Property_Disclosure.pdf', 'Johnson_Financial_Info.pdf', 'Property_Inspection_Report.pdf'],
        availableContracts: ['Residential Purchase Agreement', 'Listing Agreement', 'Property Disclosure Form']
      }

      // Add page-specific context
      switch (page) {
        case 'Document Intake':
          return {
            ...baseContext,
            availableFiles: [...baseContext.availableFiles, 'Smith_Documents.pdf', 'Property_Photos.zip']
          }
        case 'Contract Generator':
          return {
            ...baseContext,
            availableContracts: [...baseContext.availableContracts, 'Amendment Form', 'Addendum Template']
          }
        default:
          return baseContext
      }
    }

    // Update context when page changes
    updateContext(getContextualData(pageName))
  }, [pathname, updateContext])

  return <>{children}</>
}
