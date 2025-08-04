"use client"

import { useState, useEffect } from "react"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  Activity, 
  BarChart3, 
  DollarSign, 
  Users, 
  Brain, 
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap
} from "lucide-react"

import { AgentPerformanceDashboard } from "@/components/analytics/AgentPerformanceDashboard"
import { ContractProcessingDashboard } from "@/components/analytics/ContractProcessingDashboard"
import { CostAnalysisDashboard } from "@/components/analytics/CostAnalysisDashboard"
import { UserBehaviorDashboard } from "@/components/analytics/UserBehaviorDashboard"
import { PredictiveAnalyticsDashboard } from "@/components/analytics/PredictiveAnalyticsDashboard"
import { ExecutiveSummaryDashboard } from "@/components/analytics/ExecutiveSummaryDashboard"

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState("overview")
  const [isLoading, setIsLoading] = useState(true)
  const [dashboardData, setDashboardData] = useState<any>(null)

  useEffect(() => {
    // Simulate loading dashboard data
    const loadDashboardData = async () => {
      setIsLoading(true)
      try {
        // TODO: Replace with actual API calls
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // Mock data for demonstration
        setDashboardData({
          overview: {
            totalAgentExecutions: 1247,
            successRate: 94.2,
            averageProcessingTime: 2.3,
            totalCost: 1234.56,
            activeUsers: 23,
            contractsProcessed: 89
          }
        })
      } catch (error) {
        console.error("Failed to load dashboard data:", error)
      } finally {
        setIsLoading(false)
      }
    }

    loadDashboardData()
  }, [])

  const overviewMetrics = [
    {
      title: "Agent Executions",
      value: dashboardData?.overview?.totalAgentExecutions || 0,
      change: "+12.5%",
      changeType: "positive" as const,
      icon: Activity,
      description: "Total AI agent executions this month"
    },
    {
      title: "Success Rate",
      value: `${dashboardData?.overview?.successRate || 0}%`,
      change: "+2.1%",
      changeType: "positive" as const,
      icon: CheckCircle,
      description: "Agent execution success rate"
    },
    {
      title: "Avg Processing Time",
      value: `${dashboardData?.overview?.averageProcessingTime || 0}s`,
      change: "-0.3s",
      changeType: "positive" as const,
      icon: Clock,
      description: "Average contract processing time"
    },
    {
      title: "Total Cost",
      value: `$${dashboardData?.overview?.totalCost || 0}`,
      change: "+8.2%",
      changeType: "negative" as const,
      icon: DollarSign,
      description: "Total operational costs this month"
    },
    {
      title: "Active Users",
      value: dashboardData?.overview?.activeUsers || 0,
      change: "+5",
      changeType: "positive" as const,
      icon: Users,
      description: "Active users this week"
    },
    {
      title: "Contracts Processed",
      value: dashboardData?.overview?.contractsProcessed || 0,
      change: "+15.3%",
      changeType: "positive" as const,
      icon: BarChart3,
      description: "Contracts processed this month"
    }
  ]

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        
        {/* Page Header */}
        <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                    Analytics & Reporting
                  </h1>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Comprehensive insights into system performance and business metrics
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <Badge variant="outline" className="text-green-600 border-green-600">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    System Healthy
                  </Badge>
                  <Button variant="outline" size="sm">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Export Report
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <TabsList className="grid w-full grid-cols-6 lg:w-auto lg:grid-cols-6">
                <TabsTrigger value="overview" className="flex items-center space-x-2">
                  <BarChart3 className="w-4 h-4" />
                  <span className="hidden sm:inline">Overview</span>
                </TabsTrigger>
                <TabsTrigger value="agents" className="flex items-center space-x-2">
                  <Activity className="w-4 h-4" />
                  <span className="hidden sm:inline">Agents</span>
                </TabsTrigger>
                <TabsTrigger value="contracts" className="flex items-center space-x-2">
                  <BarChart3 className="w-4 h-4" />
                  <span className="hidden sm:inline">Contracts</span>
                </TabsTrigger>
                <TabsTrigger value="costs" className="flex items-center space-x-2">
                  <DollarSign className="w-4 h-4" />
                  <span className="hidden sm:inline">Costs</span>
                </TabsTrigger>
                <TabsTrigger value="users" className="flex items-center space-x-2">
                  <Users className="w-4 h-4" />
                  <span className="hidden sm:inline">Users</span>
                </TabsTrigger>
                <TabsTrigger value="predictive" className="flex items-center space-x-2">
                  <Brain className="w-4 h-4" />
                  <span className="hidden sm:inline">Predictive</span>
                </TabsTrigger>
              </TabsList>

              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-6">
                {/* Key Metrics Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {overviewMetrics.map((metric, index) => (
                    <Card key={index} className="hover:shadow-lg transition-shadow duration-200">
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                          {metric.title}
                        </CardTitle>
                        <metric.icon className="h-4 w-4 text-gray-400" />
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">
                          {isLoading ? (
                            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                          ) : (
                            metric.value
                          )}
                        </div>
                        <div className="flex items-center space-x-2 mt-2">
                          <Badge 
                            variant={metric.changeType === "positive" ? "default" : "destructive"}
                            className="text-xs"
                          >
                            {metric.change}
                          </Badge>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {metric.description}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Executive Summary */}
                <ExecutiveSummaryDashboard />
              </TabsContent>

              {/* Agent Performance Tab */}
              <TabsContent value="agents" className="space-y-6">
                <AgentPerformanceDashboard />
              </TabsContent>

              {/* Contract Processing Tab */}
              <TabsContent value="contracts" className="space-y-6">
                <ContractProcessingDashboard />
              </TabsContent>

              {/* Cost Analysis Tab */}
              <TabsContent value="costs" className="space-y-6">
                <CostAnalysisDashboard />
              </TabsContent>

              {/* User Behavior Tab */}
              <TabsContent value="users" className="space-y-6">
                <UserBehaviorDashboard />
              </TabsContent>

              {/* Predictive Analytics Tab */}
              <TabsContent value="predictive" className="space-y-6">
                <PredictiveAnalyticsDashboard />
              </TabsContent>
            </Tabs>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
