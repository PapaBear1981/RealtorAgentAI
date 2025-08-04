"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
    AlertTriangle,
    DollarSign,
    RefreshCw,
    Target,
    TrendingDown,
    TrendingUp,
    Zap
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

export function CostAnalysisDashboard() {
  const [timeRange, setTimeRange] = useState("30d")
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadCostMetrics()
  }, [timeRange])

  const loadCostMetrics = async () => {
    setIsLoading(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 1000))
    } catch (error) {
      console.error("Failed to load cost metrics:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // Mock data
  const costTrends = [
    { date: "Week 1", apiCosts: 234, compute: 156, storage: 45, total: 435 },
    { date: "Week 2", apiCosts: 267, compute: 178, storage: 48, total: 493 },
    { date: "Week 3", apiCosts: 298, compute: 189, storage: 52, total: 539 },
    { date: "Week 4", apiCosts: 312, compute: 201, storage: 55, total: 568 }
  ]

  const costByCategory = [
    { name: "API Calls", value: 1247, percentage: 55 },
    { name: "Compute", value: 724, percentage: 32 },
    { name: "Storage", value: 200, percentage: 9 },
    { name: "Bandwidth", value: 89, percentage: 4 }
  ]

  const costByService = [
    { service: "OpenAI GPT-4", cost: 567.89, usage: "2.3M tokens", trend: "up", change: "+12%" },
    { service: "AWS Lambda", cost: 234.56, usage: "1.2M requests", trend: "stable", change: "0%" },
    { service: "AWS S3", cost: 89.34, usage: "500GB", trend: "up", change: "+5%" },
    { service: "Redis Cache", cost: 45.67, usage: "100GB", trend: "down", change: "-3%" },
    { service: "PostgreSQL", cost: 123.45, usage: "50GB", trend: "up", change: "+8%" }
  ]

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042']

  const totalCost = costByCategory.reduce((sum, item) => sum + item.value, 0)
  const budgetLimit = 3000
  const budgetUsed = (totalCost / budgetLimit) * 100

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Cost Analysis & Optimization
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Track operational costs and identify optimization opportunities
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
          <Button variant="outline" size="sm" onClick={loadCostMetrics}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalCost.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              +8.2% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Budget Used</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{budgetUsed.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              ${budgetLimit - totalCost} remaining
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cost per Contract</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$1.89</div>
            <p className="text-xs text-muted-foreground">
              -$0.12 from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Optimization Potential</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$234</div>
            <p className="text-xs text-muted-foreground">
              Potential monthly savings
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Budget Alert */}
      {budgetUsed > 80 && (
        <Card className="border-yellow-200 bg-yellow-50 dark:bg-yellow-900/10">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
              <div>
                <h4 className="font-medium text-yellow-800 dark:text-yellow-200">
                  Budget Alert
                </h4>
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  You've used {budgetUsed.toFixed(1)}% of your monthly budget. Consider reviewing cost optimization recommendations.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Cost Trends</CardTitle>
            <CardDescription>
              Weekly cost breakdown by category
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={costTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="apiCosts"
                  stackId="1"
                  stroke="#3B82F6"
                  fill="#3B82F6"
                  fillOpacity={0.6}
                  name="API Costs"
                />
                <Area
                  type="monotone"
                  dataKey="compute"
                  stackId="1"
                  stroke="#10B981"
                  fill="#10B981"
                  fillOpacity={0.6}
                  name="Compute"
                />
                <Area
                  type="monotone"
                  dataKey="storage"
                  stackId="1"
                  stroke="#F59E0B"
                  fill="#F59E0B"
                  fillOpacity={0.6}
                  name="Storage"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Cost Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Cost Distribution</CardTitle>
            <CardDescription>
              Breakdown of costs by category
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={costByCategory}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percentage }) => `${name} ${percentage}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {costByCategory.map((entry, index) => (
                    <Cell key={`cost-pie-${entry.name}-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Service Costs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Service Cost Breakdown</CardTitle>
          <CardDescription>
            Detailed cost analysis by service provider
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {costByService.map((service, index) => (
              <div
                key={`cost-service-${service.name}-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <DollarSign className="w-5 h-5 text-green-600" />
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {service.service}
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {service.usage}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      ${service.cost}
                    </div>
                    <div className="text-xs text-gray-500">Monthly Cost</div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {service.trend === "up" && <TrendingUp className="w-4 h-4 text-red-600" />}
                    {service.trend === "down" && <TrendingDown className="w-4 h-4 text-green-600" />}
                    {service.trend === "stable" && <div className="w-4 h-4" />}
                    <span className={`text-sm font-medium ${
                      service.trend === "up" ? "text-red-600" :
                      service.trend === "down" ? "text-green-600" : "text-gray-600"
                    }`}>
                      {service.change}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Optimization Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Cost Optimization Recommendations</CardTitle>
          <CardDescription>
            AI-powered suggestions to reduce operational costs
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start space-x-3 p-4 border rounded-lg bg-blue-50 dark:bg-blue-900/10">
              <Zap className="w-5 h-5 text-blue-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-blue-900 dark:text-blue-100">
                  Optimize API Token Usage
                </h4>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  Implement response caching for similar queries. Potential savings: $89/month
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3 p-4 border rounded-lg bg-green-50 dark:bg-green-900/10">
              <Target className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-green-900 dark:text-green-100">
                  Right-size Compute Resources
                </h4>
                <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                  Scale down Lambda memory allocation during low-traffic periods. Potential savings: $67/month
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3 p-4 border rounded-lg bg-yellow-50 dark:bg-yellow-900/10">
              <TrendingDown className="w-5 h-5 text-yellow-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-yellow-900 dark:text-yellow-100">
                  Storage Lifecycle Management
                </h4>
                <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                  Archive old documents to cheaper storage tiers. Potential savings: $78/month
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
