"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
    Activity,
    AlertTriangle,
    Brain,
    CheckCircle,
    DollarSign,
    RefreshCw,
    XCircle
} from "lucide-react"
import { useEffect, useState } from "react"
import {
    Area,
    AreaChart,
    CartesianGrid,
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from "recharts"

interface AgentMetrics {
  agentType: string
  totalExecutions: number
  successRate: number
  averageTime: number
  cost: number
  status: "healthy" | "warning" | "error"
}

interface ExecutionTrend {
  time: string
  successful: number
  failed: number
  total: number
}

export function AgentPerformanceDashboard() {
  const [timeRange, setTimeRange] = useState("24h")
  const [selectedAgent, setSelectedAgent] = useState("all")
  const [isLoading, setIsLoading] = useState(true)
  const [metrics, setMetrics] = useState<AgentMetrics[]>([])
  const [executionTrends, setExecutionTrends] = useState<ExecutionTrend[]>([])

  useEffect(() => {
    loadAgentMetrics()
  }, [timeRange, selectedAgent])

  const loadAgentMetrics = async () => {
    setIsLoading(true)
    try {
      // TODO: Replace with actual API calls
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Mock data for demonstration
      setMetrics([
        {
          agentType: "Data Extraction",
          totalExecutions: 342,
          successRate: 96.2,
          averageTime: 1.8,
          cost: 45.67,
          status: "healthy"
        },
        {
          agentType: "Contract Generator",
          totalExecutions: 189,
          successRate: 94.7,
          averageTime: 3.2,
          cost: 78.23,
          status: "healthy"
        },
        {
          agentType: "Compliance Checker",
          totalExecutions: 156,
          successRate: 89.1,
          averageTime: 2.1,
          cost: 34.12,
          status: "warning"
        },
        {
          agentType: "Signature Tracker",
          totalExecutions: 298,
          successRate: 98.3,
          averageTime: 0.9,
          cost: 23.45,
          status: "healthy"
        },
        {
          agentType: "Summary Agent",
          totalExecutions: 234,
          successRate: 92.8,
          averageTime: 1.5,
          cost: 56.78,
          status: "healthy"
        },
        {
          agentType: "Help Agent",
          totalExecutions: 567,
          successRate: 97.1,
          averageTime: 0.7,
          cost: 89.34,
          status: "healthy"
        }
      ])

      setExecutionTrends([
        { time: "00:00", successful: 45, failed: 2, total: 47 },
        { time: "04:00", successful: 38, failed: 1, total: 39 },
        { time: "08:00", successful: 67, failed: 3, total: 70 },
        { time: "12:00", successful: 89, failed: 4, total: 93 },
        { time: "16:00", successful: 76, failed: 2, total: 78 },
        { time: "20:00", successful: 54, failed: 1, total: 55 }
      ])
    } catch (error) {
      console.error("Failed to load agent metrics:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy": return "text-green-600 bg-green-100 dark:bg-green-900/20"
      case "warning": return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20"
      case "error": return "text-red-600 bg-red-100 dark:bg-red-900/20"
      default: return "text-gray-600 bg-gray-100 dark:bg-gray-900/20"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy": return <CheckCircle className="w-4 h-4" />
      case "warning": return <AlertTriangle className="w-4 h-4" />
      case "error": return <XCircle className="w-4 h-4" />
      default: return <Activity className="w-4 h-4" />
    }
  }

  const pieChartData = metrics.map(metric => ({
    name: metric.agentType,
    value: metric.totalExecutions,
    successRate: metric.successRate
  }))

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D']

  const totalExecutions = metrics.reduce((sum, metric) => sum + metric.totalExecutions, 0)
  const averageSuccessRate = metrics.length > 0
    ? metrics.reduce((sum, metric) => sum + metric.successRate, 0) / metrics.length
    : 0
  const totalCost = metrics.reduce((sum, metric) => sum + metric.cost, 0)

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Agent Performance Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Monitor AI agent execution metrics and performance trends
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={selectedAgent} onValueChange={setSelectedAgent}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select agent type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Agents</SelectItem>
              <SelectItem value="data_extraction">Data Extraction</SelectItem>
              <SelectItem value="contract_generator">Contract Generator</SelectItem>
              <SelectItem value="compliance_checker">Compliance Checker</SelectItem>
              <SelectItem value="signature_tracker">Signature Tracker</SelectItem>
              <SelectItem value="summary_agent">Summary Agent</SelectItem>
              <SelectItem value="help_agent">Help Agent</SelectItem>
            </SelectContent>
          </Select>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">1 Hour</SelectItem>
              <SelectItem value="24h">24 Hours</SelectItem>
              <SelectItem value="7d">7 Days</SelectItem>
              <SelectItem value="30d">30 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={loadAgentMetrics}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Executions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalExecutions.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              +12.5% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{averageSuccessRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              +2.1% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalCost.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              +8.2% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.length}</div>
            <p className="text-xs text-muted-foreground">
              All systems operational
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Execution Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Execution Trends</CardTitle>
            <CardDescription>
              Agent execution success and failure rates over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={executionTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="successful"
                  stackId="1"
                  stroke="#10B981"
                  fill="#10B981"
                  fillOpacity={0.6}
                  name="Successful"
                />
                <Area
                  type="monotone"
                  dataKey="failed"
                  stackId="1"
                  stroke="#EF4444"
                  fill="#EF4444"
                  fillOpacity={0.6}
                  name="Failed"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Agent Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Execution Distribution</CardTitle>
            <CardDescription>
              Distribution of executions across different agent types
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieChartData.map((entry, index) => (
                    <Cell key={`agent-pie-${entry.name}-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Agent Details Table */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Performance Details</CardTitle>
          <CardDescription>
            Detailed performance metrics for each AI agent type
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {metrics.map((metric, index) => (
              <div
                key={`agent-metric-${metric.agentType}-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <Brain className="w-5 h-5 text-blue-600" />
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {metric.agentType}
                      </h4>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {metric.totalExecutions} executions
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {metric.successRate}%
                    </div>
                    <div className="text-xs text-gray-500">Success Rate</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {metric.averageTime}s
                    </div>
                    <div className="text-xs text-gray-500">Avg Time</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      ${metric.cost}
                    </div>
                    <div className="text-xs text-gray-500">Cost</div>
                  </div>
                  <Badge className={getStatusColor(metric.status)}>
                    {getStatusIcon(metric.status)}
                    <span className="ml-1 capitalize">{metric.status}</span>
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
