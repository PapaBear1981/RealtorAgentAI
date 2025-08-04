"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
    AlertTriangle,
    Award,
    Brain,
    CheckCircle,
    RefreshCw,
    Target,
    Zap
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

export function PredictiveAnalyticsDashboard() {
  const [timeRange, setTimeRange] = useState("30d")
  const [selectedModel, setSelectedModel] = useState("all")
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadPredictiveMetrics()
  }, [timeRange, selectedModel])

  const loadPredictiveMetrics = async () => {
    setIsLoading(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 1000))
    } catch (error) {
      console.error("Failed to load predictive metrics:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // Mock data
  const modelPerformance = [
    {
      name: "Contract Success Predictor",
      accuracy: 94.2,
      precision: 92.8,
      recall: 95.1,
      f1Score: 93.9,
      status: "active",
      predictions: 1247
    },
    {
      name: "Risk Assessment Model",
      accuracy: 89.7,
      precision: 87.3,
      recall: 91.2,
      f1Score: 89.2,
      status: "active",
      predictions: 892
    },
    {
      name: "Processing Time Predictor",
      accuracy: 91.5,
      precision: 90.1,
      recall: 92.8,
      f1Score: 91.4,
      status: "training",
      predictions: 0
    },
    {
      name: "User Churn Predictor",
      accuracy: 87.3,
      precision: 85.9,
      recall: 88.7,
      f1Score: 87.3,
      status: "active",
      predictions: 567
    }
  ]

  const predictionTrends = [
    { date: "Week 1", successful: 89, risky: 23, neutral: 45 },
    { date: "Week 2", successful: 94, risky: 18, neutral: 52 },
    { date: "Week 3", successful: 87, risky: 28, neutral: 38 },
    { date: "Week 4", successful: 92, risky: 21, neutral: 47 }
  ]

  const riskAssessments = [
    { contract: "Purchase Agreement #1247", riskScore: 85, factors: ["Missing documentation", "High value"], status: "high" },
    { contract: "Lease Agreement #1248", riskScore: 45, factors: ["Standard terms"], status: "low" },
    { contract: "Commercial Lease #1249", riskScore: 72, factors: ["Complex terms", "Multiple parties"], status: "medium" },
    { contract: "Residential Sale #1250", riskScore: 28, factors: ["Standard process"], status: "low" },
    { contract: "Investment Property #1251", riskScore: 91, factors: ["High value", "Financing contingency"], status: "high" }
  ]

  const successPredictions = [
    { timeframe: "Next 7 days", predicted: 156, confidence: 94.2 },
    { timeframe: "Next 30 days", predicted: 678, confidence: 89.7 },
    { timeframe: "Next 90 days", predicted: 1847, confidence: 82.3 }
  ]

  const getRiskColor = (status: string) => {
    switch (status) {
      case "low": return "text-green-600 bg-green-100 dark:bg-green-900/20"
      case "medium": return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20"
      case "high": return "text-red-600 bg-red-100 dark:bg-red-900/20"
      default: return "text-gray-600 bg-gray-100 dark:bg-gray-900/20"
    }
  }

  const getRiskIcon = (status: string) => {
    switch (status) {
      case "low": return <CheckCircle className="w-4 h-4" />
      case "medium": return <AlertTriangle className="w-4 h-4" />
      case "high": return <AlertTriangle className="w-4 h-4" />
      default: return <Target className="w-4 h-4" />
    }
  }

  const getModelStatusColor = (status: string) => {
    switch (status) {
      case "active": return "text-green-600 bg-green-100 dark:bg-green-900/20"
      case "training": return "text-blue-600 bg-blue-100 dark:bg-blue-900/20"
      case "inactive": return "text-gray-600 bg-gray-100 dark:bg-gray-900/20"
      default: return "text-gray-600 bg-gray-100 dark:bg-gray-900/20"
    }
  }

  const averageAccuracy = modelPerformance.reduce((sum, model) => sum + model.accuracy, 0) / modelPerformance.length
  const totalPredictions = modelPerformance.reduce((sum, model) => sum + model.predictions, 0)
  const activeModels = modelPerformance.filter(model => model.status === "active").length

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Predictive Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            AI-powered predictions for contract outcomes and risk assessment
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Models</SelectItem>
              <SelectItem value="success">Contract Success</SelectItem>
              <SelectItem value="risk">Risk Assessment</SelectItem>
              <SelectItem value="processing">Processing Time</SelectItem>
              <SelectItem value="churn">User Churn</SelectItem>
            </SelectContent>
          </Select>
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
          <Button variant="outline" size="sm" onClick={loadPredictiveMetrics}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Models</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeModels}</div>
            <p className="text-xs text-muted-foreground">
              {modelPerformance.length} total models
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Accuracy</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{averageAccuracy.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              +2.3% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Predictions</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalPredictions.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              +15.7% from last period
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Model Performance</CardTitle>
            <Award className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Excellent</div>
            <p className="text-xs text-muted-foreground">
              All models performing well
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Prediction Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Prediction Trends</CardTitle>
            <CardDescription>
              Weekly breakdown of contract outcome predictions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={predictionTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
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
                  dataKey="neutral"
                  stackId="1"
                  stroke="#F59E0B"
                  fill="#F59E0B"
                  fillOpacity={0.6}
                  name="Neutral"
                />
                <Area
                  type="monotone"
                  dataKey="risky"
                  stackId="1"
                  stroke="#EF4444"
                  fill="#EF4444"
                  fillOpacity={0.6}
                  name="Risky"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Success Predictions */}
        <Card>
          <CardHeader>
            <CardTitle>Success Predictions</CardTitle>
            <CardDescription>
              Predicted contract completions with confidence levels
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {successPredictions.map((prediction, index) => (
                <div key={`prediction-${prediction.timeframe}-${index}`} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{prediction.timeframe}</span>
                    <div className="flex items-center space-x-2">
                      <span className="text-lg font-bold text-gray-900 dark:text-white">
                        {prediction.predicted}
                      </span>
                      <span className="text-sm text-gray-500">contracts</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>Confidence</span>
                      <span>{prediction.confidence}%</span>
                    </div>
                    <Progress value={prediction.confidence} className="h-2" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Model Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle>Model Performance</CardTitle>
          <CardDescription>
            Detailed performance metrics for each predictive model
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {modelPerformance.map((model, index) => (
              <div
                key={`model-${model.name}-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <Brain className="w-5 h-5 text-purple-600" />
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {model.name}
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {model.predictions.toLocaleString()} predictions made
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {model.accuracy}%
                    </div>
                    <div className="text-xs text-gray-500">Accuracy</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {model.precision}%
                    </div>
                    <div className="text-xs text-gray-500">Precision</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {model.f1Score}%
                    </div>
                    <div className="text-xs text-gray-500">F1 Score</div>
                  </div>
                  <Badge className={getModelStatusColor(model.status)}>
                    <span className="capitalize">{model.status}</span>
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Risk Assessments */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Risk Assessments</CardTitle>
          <CardDescription>
            AI-powered risk analysis for recent contracts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {riskAssessments.map((assessment, index) => (
              <div
                key={`risk-${assessment.contractType}-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <Target className="w-5 h-5 text-blue-600" />
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {assessment.contract}
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Risk factors: {assessment.factors.join(", ")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {assessment.riskScore}
                    </div>
                    <div className="text-xs text-gray-500">Risk Score</div>
                  </div>
                  <Badge className={getRiskColor(assessment.status)}>
                    {getRiskIcon(assessment.status)}
                    <span className="ml-1 capitalize">{assessment.status} Risk</span>
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
