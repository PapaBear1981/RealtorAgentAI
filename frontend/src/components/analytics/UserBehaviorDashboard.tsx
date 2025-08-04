"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
    ArrowRight,
    Clock,
    Eye,
    Filter,
    RefreshCw,
    TrendingUp,
    Users
} from "lucide-react"
import { useEffect, useState } from "react"
import {
    Area,
    AreaChart,
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from "recharts"

export function UserBehaviorDashboard() {
  const [timeRange, setTimeRange] = useState("7d")
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadUserBehaviorMetrics()
  }, [timeRange])

  const loadUserBehaviorMetrics = async () => {
    setIsLoading(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 1000))
    } catch (error) {
      console.error("Failed to load user behavior metrics:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // Mock data
  const userActivityTrends = [
    { date: "Mon", pageViews: 1247, uniqueUsers: 89, sessions: 156 },
    { date: "Tue", pageViews: 1356, uniqueUsers: 94, sessions: 167 },
    { date: "Wed", pageViews: 1189, uniqueUsers: 87, sessions: 145 },
    { date: "Thu", pageViews: 1423, uniqueUsers: 102, sessions: 178 },
    { date: "Fri", pageViews: 1567, uniqueUsers: 112, sessions: 189 },
    { date: "Sat", pageViews: 987, uniqueUsers: 67, sessions: 123 },
    { date: "Sun", pageViews: 1098, uniqueUsers: 78, sessions: 134 }
  ]

  const conversionFunnel = [
    { name: "Landing Page", value: 1000, fill: "#3B82F6" },
    { name: "Document Upload", value: 750, fill: "#10B981" },
    { name: "Contract Creation", value: 450, fill: "#F59E0B" },
    { name: "Review & Edit", value: 380, fill: "#EF4444" },
    { name: "Signature Request", value: 320, fill: "#8B5CF6" },
    { name: "Completed", value: 280, fill: "#06B6D4" }
  ]

  const topPages = [
    { page: "/dashboard", views: 3456, avgTime: "2:34", bounceRate: 23.4 },
    { page: "/contracts/create", views: 2789, avgTime: "4:12", bounceRate: 18.7 },
    { page: "/analytics", views: 1987, avgTime: "3:45", bounceRate: 31.2 },
    { page: "/templates", views: 1654, avgTime: "2:18", bounceRate: 28.9 },
    { page: "/signatures", views: 1432, avgTime: "1:56", bounceRate: 35.6 }
  ]

  const workflowBottlenecks = [
    { step: "Document Upload", avgTime: "45s", dropOffRate: 12.3, issue: "File size limits" },
    { step: "Template Selection", avgTime: "1m 23s", dropOffRate: 8.7, issue: "Too many options" },
    { step: "Contract Review", avgTime: "3m 45s", dropOffRate: 15.6, issue: "Complex interface" },
    { step: "Signature Setup", avgTime: "2m 12s", dropOffRate: 22.1, issue: "Email configuration" }
  ]

  const totalPageViews = userActivityTrends.reduce((sum, day) => sum + day.pageViews, 0)
  const totalUniqueUsers = Math.max(...userActivityTrends.map(day => day.uniqueUsers))
  const conversionRate = ((conversionFunnel[conversionFunnel.length - 1].value / conversionFunnel[0].value) * 100)

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            User Behavior Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Understand user interactions and optimize workflows
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">24 Hours</SelectItem>
              <SelectItem value="7d">7 Days</SelectItem>
              <SelectItem value="30d">30 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={loadUserBehaviorMetrics}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Page Views</CardTitle>
            <Eye className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalPageViews.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              +12.5% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unique Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalUniqueUsers}</div>
            <p className="text-xs text-muted-foreground">
              +8.3% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{conversionRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              +2.1% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Session Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">4m 23s</div>
            <p className="text-xs text-muted-foreground">
              +15s from last period
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Activity Trends */}
        <Card>
          <CardHeader>
            <CardTitle>User Activity Trends</CardTitle>
            <CardDescription>
              Daily page views, unique users, and sessions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={userActivityTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="pageViews"
                  stroke="#3B82F6"
                  fill="#3B82F6"
                  fillOpacity={0.3}
                  name="Page Views"
                />
                <Area
                  type="monotone"
                  dataKey="uniqueUsers"
                  stroke="#10B981"
                  fill="#10B981"
                  fillOpacity={0.3}
                  name="Unique Users"
                />
                <Area
                  type="monotone"
                  dataKey="sessions"
                  stroke="#F59E0B"
                  fill="#F59E0B"
                  fillOpacity={0.3}
                  name="Sessions"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Conversion Funnel */}
        <Card>
          <CardHeader>
            <CardTitle>User Journey Funnel</CardTitle>
            <CardDescription>
              Conversion rates through the contract creation process
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {conversionFunnel.map((step, index) => {
                const percentage = index === 0 ? 100 : (step.value / conversionFunnel[0].value) * 100
                const dropOff = index > 0 ? conversionFunnel[index - 1].value - step.value : 0

                return (
                  <div key={step.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{step.name}</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-600">{step.value.toLocaleString()}</span>
                        <span className="text-xs text-gray-500">({percentage.toFixed(1)}%)</span>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${percentage}%`,
                          backgroundColor: step.fill
                        }}
                      />
                    </div>
                    {index > 0 && dropOff > 0 && (
                      <p className="text-xs text-red-600">
                        -{dropOff} users dropped off ({((dropOff / conversionFunnel[index - 1].value) * 100).toFixed(1)}%)
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Pages */}
      <Card>
        <CardHeader>
          <CardTitle>Top Pages</CardTitle>
          <CardDescription>
            Most visited pages and their performance metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {topPages.map((page, index) => (
              <div
                key={`top-page-${page.page}-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <Eye className="w-5 h-5 text-blue-600" />
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {page.page}
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {page.views.toLocaleString()} views
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {page.avgTime}
                    </div>
                    <div className="text-xs text-gray-500">Avg Time</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {page.bounceRate}%
                    </div>
                    <div className="text-xs text-gray-500">Bounce Rate</div>
                  </div>
                  <Badge variant={page.bounceRate < 30 ? "default" : "secondary"}>
                    {page.bounceRate < 30 ? "Good" : "Needs Attention"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Workflow Bottlenecks */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Bottlenecks</CardTitle>
          <CardDescription>
            Identified issues in user workflows that need optimization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {workflowBottlenecks.map((bottleneck, index) => (
              <div
                key={`bottleneck-${bottleneck.step}-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg bg-yellow-50 dark:bg-yellow-900/10 border-yellow-200"
              >
                <div className="flex items-center space-x-4">
                  <Filter className="w-5 h-5 text-yellow-600" />
                  <div>
                    <h4 className="font-medium text-yellow-900 dark:text-yellow-100">
                      {bottleneck.step}
                    </h4>
                    <p className="text-sm text-yellow-700 dark:text-yellow-300">
                      Issue: {bottleneck.issue}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                      {bottleneck.avgTime}
                    </div>
                    <div className="text-xs text-yellow-700 dark:text-yellow-300">Avg Time</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                      {bottleneck.dropOffRate}%
                    </div>
                    <div className="text-xs text-yellow-700 dark:text-yellow-300">Drop-off Rate</div>
                  </div>
                  <Button variant="outline" size="sm">
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Optimize
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
