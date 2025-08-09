"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/hooks/use-toast"
import { analyticsService } from "@/services/analyticsService"
import {
    Activity,
    AlertTriangle,
    CheckCircle,
    DollarSign,
    FileText,
    Target,
    TrendingDown,
    TrendingUp,
    Users
} from "lucide-react"
import { useEffect, useState } from "react"
import {
    CartesianGrid,
    Legend,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from "recharts"

interface KPI {
  name: string
  value: string
  target: string
  progress: number
  trend: "up" | "down" | "stable"
  trendValue: string
  status: "on-track" | "at-risk" | "behind"
}

interface Alert {
  id: string
  type: "warning" | "error" | "info"
  title: string
  description: string
  timestamp: string
}

export function ExecutiveSummaryDashboard() {
  const [isLoading, setIsLoading] = useState(true)
  const [kpis, setKpis] = useState<KPI[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [performanceTrends, setPerformanceTrends] = useState<any[]>([])
  const { toast } = useToast()

  useEffect(() => {
    loadExecutiveSummary()
  }, [])

  const loadExecutiveSummary = async () => {
    setIsLoading(true)
    try {
      // Load real executive summary data
      const executiveSummary = await analyticsService.getExecutiveSummary(24)

      setKpis(executiveSummary.kpis)
      setAlerts(executiveSummary.alerts)

      // Generate performance trends from KPI data
      const trends = executiveSummary.kpis.map((kpi, index) => ({
        month: new Date().toLocaleDateString('en-US', { month: 'short' }),
        revenue: kpi.name === 'Monthly Revenue' ? parseFloat(kpi.value.replace(/[$,]/g, '')) : 0,
        contracts: kpi.name === 'Contract Processing' ? parseInt(kpi.value.replace(/,/g, '')) : 0,
        satisfaction: kpi.name === 'Customer Satisfaction' ? parseFloat(kpi.value.replace('%', '')) : 0,
      }))
      setPerformanceTrends(trends)
    } catch (error) {
      console.error("Failed to load executive summary:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "on-track": return "text-green-600 bg-green-100 dark:bg-green-900/20"
      case "at-risk": return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20"
      case "behind": return "text-red-600 bg-red-100 dark:bg-red-900/20"
      default: return "text-gray-600 bg-gray-100 dark:bg-gray-900/20"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "on-track": return <CheckCircle className="w-4 h-4" />
      case "at-risk": return <AlertTriangle className="w-4 h-4" />
      case "behind": return <TrendingDown className="w-4 h-4" />
      default: return <Activity className="w-4 h-4" />
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case "up": return <TrendingUp className="w-4 h-4 text-green-600" />
      case "down": return <TrendingDown className="w-4 h-4 text-red-600" />
      default: return <Activity className="w-4 h-4 text-gray-600" />
    }
  }

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "warning": return <AlertTriangle className="w-4 h-4 text-yellow-600" />
      case "error": return <AlertTriangle className="w-4 h-4 text-red-600" />
      case "info": return <CheckCircle className="w-4 h-4 text-blue-600" />
      default: return <Activity className="w-4 h-4 text-gray-600" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Executive Summary
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            High-level business metrics and key performance indicators
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-green-600 border-green-600">
            <CheckCircle className="w-3 h-3 mr-1" />
            Overall Healthy
          </Badge>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {kpis.map((kpi, index) => (
          <Card key={index} className="hover:shadow-lg transition-shadow duration-200">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  {kpi.name}
                </CardTitle>
                <Badge className={getStatusColor(kpi.status)}>
                  {getStatusIcon(kpi.status)}
                  <span className="ml-1 capitalize">{kpi.status.replace("-", " ")}</span>
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {kpi.value}
                </div>
                <div className="flex items-center space-x-1">
                  {getTrendIcon(kpi.trend)}
                  <span className={`text-sm font-medium ${
                    kpi.trend === "up" ? "text-green-600" :
                    kpi.trend === "down" ? "text-red-600" : "text-gray-600"
                  }`}>
                    {kpi.trendValue}
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Target: {kpi.target}</span>
                  <span className="text-gray-900 dark:text-white font-medium">
                    {kpi.progress}%
                  </span>
                </div>
                <Progress value={kpi.progress} className="h-2" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts and Alerts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Performance Trends */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Performance Trends</CardTitle>
            <CardDescription>
              Key business metrics over the last 5 months
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="revenue"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  name="Revenue ($)"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="contracts"
                  stroke="#10B981"
                  strokeWidth={2}
                  name="Contracts"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="satisfaction"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  name="Satisfaction (%)"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recent Alerts */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
            <CardDescription>
              System notifications and important updates
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-start space-x-3 p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {getAlertIcon(alert.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                      {alert.title}
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {alert.description}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      {alert.timestamp}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common executive actions and reports
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <FileText className="w-6 h-6 text-blue-600" />
              <span className="text-sm font-medium">Monthly Report</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <DollarSign className="w-6 h-6 text-green-600" />
              <span className="text-sm font-medium">Cost Analysis</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <Users className="w-6 h-6 text-purple-600" />
              <span className="text-sm font-medium">User Insights</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <Target className="w-6 h-6 text-orange-600" />
              <span className="text-sm font-medium">Goal Tracking</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
