"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
    CheckCircle,
    Clock,
    Download,
    FileText,
    RefreshCw,
    TrendingUp
} from "lucide-react"
import { useEffect, useState } from "react"
import {
    Bar,
    BarChart,
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

export function ContractProcessingDashboard() {
  const [timeRange, setTimeRange] = useState("30d")
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadContractMetrics()
  }, [timeRange])

  const loadContractMetrics = async () => {
    setIsLoading(true)
    try {
      // TODO: Replace with actual API calls
      await new Promise(resolve => setTimeout(resolve, 1000))
    } catch (error) {
      console.error("Failed to load contract metrics:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // Mock data
  const processingTrends = [
    { date: "2024-01-01", created: 45, completed: 42, failed: 3 },
    { date: "2024-01-02", created: 52, completed: 48, failed: 4 },
    { date: "2024-01-03", created: 38, completed: 36, failed: 2 },
    { date: "2024-01-04", created: 61, completed: 58, failed: 3 },
    { date: "2024-01-05", created: 49, completed: 46, failed: 3 },
    { date: "2024-01-06", created: 55, completed: 52, failed: 3 },
    { date: "2024-01-07", created: 43, completed: 41, failed: 2 }
  ]

  const templateUsage = [
    { name: "Purchase Agreement", value: 342, percentage: 35 },
    { name: "Lease Agreement", value: 234, percentage: 24 },
    { name: "Listing Agreement", value: 189, percentage: 19 },
    { name: "Disclosure Form", value: 156, percentage: 16 },
    { name: "Other", value: 67, percentage: 6 }
  ]

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Contract Processing Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Monitor contract generation, processing times, and template usage
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">7 Days</SelectItem>
              <SelectItem value="30d">30 Days</SelectItem>
              <SelectItem value="90d">90 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={loadContractMetrics}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Contracts Created</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,247</div>
            <p className="text-xs text-muted-foreground">
              +15.3% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">94.7%</div>
            <p className="text-xs text-muted-foreground">
              +2.1% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.3s</div>
            <p className="text-xs text-muted-foreground">
              -0.4s from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Templates Used</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">
              +3 new templates
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Processing Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Contract Processing Trends</CardTitle>
            <CardDescription>
              Daily contract creation and completion rates
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={processingTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="created" fill="#3B82F6" name="Created" />
                <Bar dataKey="completed" fill="#10B981" name="Completed" />
                <Bar dataKey="failed" fill="#EF4444" name="Failed" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Template Usage */}
        <Card>
          <CardHeader>
            <CardTitle>Template Usage Distribution</CardTitle>
            <CardDescription>
              Most frequently used contract templates
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={templateUsage}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percentage }) => `${name} ${percentage}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {templateUsage.map((entry, index) => (
                    <Cell key={`template-pie-${entry.name}-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Template Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle>Template Performance</CardTitle>
          <CardDescription>
            Detailed performance metrics for each contract template
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {templateUsage.map((template, index) => (
              <div
                key={`template-usage-${template.name}-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <FileText className="w-5 h-5 text-blue-600" />
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {template.name}
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {template.value} contracts generated
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {template.percentage}%
                    </div>
                    <div className="text-xs text-gray-500">Usage</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      96.2%
                    </div>
                    <div className="text-xs text-gray-500">Success Rate</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      1.8s
                    </div>
                    <div className="text-xs text-gray-500">Avg Time</div>
                  </div>
                  <Badge className="text-green-600 bg-green-100 dark:bg-green-900/20">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Active
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
