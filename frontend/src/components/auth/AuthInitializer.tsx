"use client"

import { useAuthStore } from '@/stores/auth'
import { useEffect } from 'react'

export function AuthInitializer() {
  const { checkAuth, isLoading, isAuthenticated } = useAuthStore()

  useEffect(() => {
    // Initialize authentication state on app startup
    // This will restore the session from localStorage if it exists
    // We need to call checkAuth regardless of current state to restore from localStorage
    console.log('AuthInitializer: Calling checkAuth on startup')
    checkAuth()
  }, [checkAuth])

  // This component doesn't render anything
  return null
}
