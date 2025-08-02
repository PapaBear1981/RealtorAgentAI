"use client"

import { useAuthStore } from '@/stores/auth'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { HelpAgentProvider } from './HelpAgentProvider'
import { HelpAgentSlideOut } from './HelpAgentSlideOut'

export function AuthenticatedAssistantAgent() {
  const pathname = usePathname()
  const { isAuthenticated } = useAuthStore()
  const [shouldShow, setShouldShow] = useState(false)

  useEffect(() => {
    // Only show the assistant agent for authenticated users
    // and not on the landing page or login page
    const isPublicPage = pathname === '/' || pathname === '/login'
    setShouldShow(isAuthenticated && !isPublicPage)
  }, [isAuthenticated, pathname])

  // Don't render anything if user is not authenticated or on public pages
  if (!shouldShow) {
    return null
  }

  return (
    <HelpAgentProvider>
      <HelpAgentSlideOut />
    </HelpAgentProvider>
  )
}
