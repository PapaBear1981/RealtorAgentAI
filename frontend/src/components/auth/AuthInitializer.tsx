"use client"

import { useEffect } from 'react'
import { useAuthStore } from '@/stores/auth'

export function AuthInitializer() {
  const { checkAuth, isLoading } = useAuthStore()

  useEffect(() => {
    // Initialize authentication state on app startup
    // This will restore the session from localStorage if it exists
    if (!isLoading) {
      checkAuth()
    }
  }, [checkAuth, isLoading])

  // This component doesn't render anything
  return null
}
