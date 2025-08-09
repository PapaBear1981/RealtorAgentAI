"use client"

import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/hooks/use-toast"
import { analyticsService, DashboardOverview } from "@/services/analyticsService"
import { useEffect, useState } from "react"

export default function DashboardPage() {
  const [dashboardData, setDashboardData] = useState<DashboardOverview | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setIsLoading(true)
        const data = await analyticsService.getDashboardOverview(24) // Last 24 hours
        setDashboardData(data)
      } catch (error) {
        console.error('Failed to load dashboard data:', error)
        toast({
          title: "Failed to load dashboard",
          description: "Could not load dashboard metrics. Please refresh the page.",
          variant: "destructive",
        })
      } finally {
        setIsLoading(false)
      }
    }

    loadDashboardData()
  }, [toast])

  if (isLoading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-background">
          <Navigation />
          <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <div className="px-4 py-6 sm:px-0">
              <div className="animate-pulse">
                <div className="h-8 bg-muted rounded w-1/4 mb-4"></div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-32 bg-muted rounded"></div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        {/* Navigation */}
        <Navigation />

        {/* Page Header */}
        <header className="bg-card shadow-sm border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Overview of your real estate contracts and activities
              </p>
            </div>
          </div>
        </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* My Deals Widget */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">My Deals</CardTitle>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-4 w-4 text-muted-foreground"
                >
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="m22 2-5 10-5-5-5 10" />
                </svg>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dashboardData?.dealsInProgress || 0}</div>
                <p className="text-xs text-muted-foreground">
                  Active deals in progress
                </p>
              </CardContent>
            </Card>

            {/* Pending Signatures Widget */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pending Signatures</CardTitle>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-4 w-4 text-muted-foreground"
                >
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dashboardData?.pendingSignatures || 0}</div>
                <p className="text-xs text-muted-foreground">
                  Awaiting signatures
                </p>
              </CardContent>
            </Card>

            {/* Compliance Alerts Widget */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Compliance Alerts</CardTitle>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-4 w-4 text-muted-foreground"
                >
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="m2 17 10 5 10-5" />
                  <path d="m2 12 10 5 10-5" />
                </svg>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dashboardData?.complianceAlerts || 0}</div>
                <p className="text-xs text-muted-foreground">
                  Compliance issues
                </p>
              </CardContent>
            </Card>

            {/* Recent Uploads Widget */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Recent Uploads</CardTitle>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-4 w-4 text-muted-foreground"
                >
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                  <polyline points="14,2 14,8 20,8" />
                </svg>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dashboardData?.recentUploads || 0}</div>
                <p className="text-xs text-muted-foreground">
                  Files uploaded today
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Document Intake</CardTitle>
                <CardDescription>
                  Upload and process real estate documents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full">Upload Documents</Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Contract Generator</CardTitle>
                <CardDescription>
                  Generate contracts from templates
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full">Create Contract</Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Signature Tracker</CardTitle>
                <CardDescription>
                  Track multi-party signatures
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full">View Signatures</Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
    </ProtectedRoute>
  )
}
