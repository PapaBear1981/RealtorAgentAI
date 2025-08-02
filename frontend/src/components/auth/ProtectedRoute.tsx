"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/stores/auth"

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: 'admin' | 'agent' | 'tc' | 'signer'
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, checkAuth } = useAuthStore()

  useEffect(() => {
    // Check authentication status on mount
    if (!isAuthenticated && !isLoading) {
      checkAuth()
    }
  }, [isAuthenticated, isLoading, checkAuth])

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isLoading && !isAuthenticated) {
      router.push("/login")
      return
    }

    // Check role-based access if required
    if (requiredRole && user && user.role !== requiredRole) {
      // For now, just redirect to dashboard
      // In a real app, you might show an unauthorized page
      router.push("/dashboard")
      return
    }
  }, [isAuthenticated, isLoading, user, requiredRole, router])

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Don't render children if not authenticated
  if (!isAuthenticated || !user) {
    return null
  }

  // Check role access
  if (requiredRole && user.role !== requiredRole) {
    return null
  }

  return <>{children}</>
}
