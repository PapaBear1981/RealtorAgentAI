"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer
} from "recharts"
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  DollarSign, 
  Users, 
  FileText, 
  Activity,
  Target,
  Award,
  Clock,
  Zap
} from "lucide-react"

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

  useEffect(() => {
    loadExecutiveSummary()
  }, [])

  const loadExecutiveSummary = async () => {
    setIsLoading(true)
    try {
      // TODO: Replace with actual API calls
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Mock data for demonstration
      setKpis([
        {
          name: "Monthly Revenue",
          value: "$124,567",
          target: "$150,000",
          progress: 83,
          trend: "up",
          trendValue: "+12.5%",
          status: "on-track"
        },
        {
          name: "Contract Processing",
          value: "1,247",
          target: "1,500",
          progress: 83,
          trend: "up",
          trendValue: "+8.3%",
          status: "on-track"
        },
        {
          name: "Customer Satisfaction",
          value: "94.2%",
          target: "95%",
          progress: 99,
          trend: "up",
          trendValue: "+2.1%",
          status: "on-track"
        },
        {
          name: "System Uptime",
          value: "99.8%",
          target: "99.9%",
          progress: 99,
          trend: "stable",
          trendValue: "0%",
          status: "at-risk"
        },
        {
          name: "Cost Efficiency",
          value: "$0.23",
          target: "$0.20",
          progress: 87,
          trend: "down",
          trendValue: "-5.2%",
          status: "behind"
        },
        {
          name: "User Adoption",
          value: "78%",
          target: "85%",
          progress: 92,
          trend: "up",
          trendValue: "+15.3%",
          status: "on-track"
        }
      ])

      setAlerts([
        {
          id: "1",
          type: "warning",
          title: "High API Costs",
          description: "OpenAI API costs are 15% above budget this month",
          timestamp: "2 hours ago"
        },
        {
          id: "2",
          type: "info",
          title: "New Feature Deployment",
          description: "Predictive analytics module deployed successfully",
          timestamp: "4 hours ago"
        },
        {
          id: "3",
          type: "error",
          title: "Agent Performance Issue",
          description: "Compliance checker agent showing increased error rate",
          timestamp: "6 hours ago"
        }
      ])

      setPerformanceTrends([
        { month: "Jan", revenue: 98000, contracts: 890, satisfaction: 92.1 },
        { month: "Feb", revenue: 105000, contracts: 945, satisfaction: 93.2 },
        { month: "Mar", revenue: 112000, contracts: 1020, satisfaction: 93.8 },
        { month: "Apr", revenue: 118000, contracts: 1150, satisfaction: 94.1 },
        { month: "May", revenue: 124567, contracts: 1247, satisfaction: 94.2 }
      ])
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
