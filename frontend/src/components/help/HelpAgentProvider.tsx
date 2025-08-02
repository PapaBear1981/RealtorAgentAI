"use client"

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { useHelpAgentStore } from '@/stores/helpAgentStore'

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
  const updateContext = useHelpAgentStore((state) => state.updateContext)

  useEffect(() => {
    const pageName = getPageNameFromPath(pathname)
    
    // Update context when page changes
    updateContext({
      page: pageName,
      // You can add more context based on the current page
      // For example, extract IDs from the pathname for dynamic routes
    })
  }, [pathname, updateContext])

  return <>{children}</>
}
