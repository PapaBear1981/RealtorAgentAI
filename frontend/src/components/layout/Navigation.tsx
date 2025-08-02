"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/stores/auth"
import { useToast } from "@/hooks/use-toast"

interface NavigationProps {
  className?: string
}

export function Navigation({ className }: NavigationProps) {
  const router = useRouter()
  const { toast } = useToast()
  const { user, isAuthenticated, logout } = useAuthStore()

  const handleLogout = async () => {
    logout()
    toast({
      title: "Logged out",
      description: "You have been logged out successfully.",
    })
    router.push("/login")
  }

  if (!isAuthenticated || !user) {
    return null
  }

  const navigationItems = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/documents", label: "Documents" },
    { href: "/contracts", label: "Contracts" },
    { href: "/signatures", label: "Signatures" },
  ]

  // Add admin-only items
  if (user.role === 'admin') {
    navigationItems.push({ href: "/admin", label: "Admin" })
  }

  return (
    <nav className={`bg-white shadow ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          {/* Logo and Brand */}
          <div className="flex items-center">
            <Link href="/dashboard" className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">RealtorAgentAI</h1>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-8">
            {navigationItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-700">
              Welcome, {user.name}
            </span>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {user.role}
            </span>
            <Button onClick={handleLogout} variant="outline" size="sm">
              Logout
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden">
        <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 border-t">
          {navigationItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-gray-700 hover:text-gray-900 block px-3 py-2 rounded-md text-base font-medium"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}
