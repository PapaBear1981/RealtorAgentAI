/**
 * Analytics service for dashboard metrics and reporting.
 * 
 * This service handles all analytics-related API calls including:
 * - Dashboard metrics and KPIs
 * - Agent performance analytics
 * - Contract processing statistics
 * - Cost analysis and tracking
 * - User behavior analytics
 * - Predictive analytics data
 */

import { apiClient } from './apiClient'

export interface DashboardOverview {
  totalAgentExecutions: number
  successRate: number
  averageProcessingTime: number
  totalCost: number
  activeUsers: number
  contractsProcessed: number
  dealsInProgress: number
  pendingSignatures: number
  complianceAlerts: number
  recentUploads: number
}

export interface AgentMetrics {
  agentType: string
  totalExecutions: number
  successRate: number
  averageTime: number
  cost: number
  status: 'healthy' | 'warning' | 'error'
}

export interface ContractMetrics {
  totalContracts: number
  contractsByStatus: Record<string, number>
  averageProcessingTime: number
  completionRate: number
  monthlyTrend: Array<{ date: string; count: number }>
}

export interface CostMetrics {
  totalCost: number
  costByCategory: Array<{ name: string; value: number; percentage: number }>
  costByService: Array<{ 
    service: string
    cost: number
    usage: string
    trend: 'up' | 'down' | 'stable'
    change: string
  }>
  monthlyTrend: Array<{ date: string; cost: number }>
}

export interface UserBehaviorMetrics {
  activeUsers: number
  userActivityTrends: Array<{
    date: string
    pageViews: number
    uniqueUsers: number
    sessions: number
  }>
  featureUsage: Array<{ feature: string; usage: number; trend: string }>
  userRetention: number
}

export interface PredictiveMetrics {
  modelPerformance: Array<{
    name: string
    accuracy: number
    precision: number
    recall: number
    f1Score: number
    status: 'active' | 'training' | 'inactive'
    predictions: number
  }>
  predictions: Array<{
    type: string
    prediction: string
    confidence: number
    impact: 'high' | 'medium' | 'low'
  }>
}

export interface ExecutiveSummary {
  kpis: Array<{
    name: string
    value: string
    target: string
    progress: number
    trend: 'up' | 'down' | 'stable'
    trendValue: string
    status: 'on-track' | 'at-risk' | 'behind'
  }>
  alerts: Array<{
    id: string
    type: 'info' | 'warning' | 'error'
    title: string
    description: string
    timestamp: string
  }>
}

class AnalyticsService {
  /**
   * Get dashboard overview metrics
   */
  async getDashboardOverview(periodHours: number = 24): Promise<DashboardOverview> {
    const response = await apiClient.get<DashboardOverview>(`/analytics/dashboard/overview?period_hours=${periodHours}`)
    return response.data
  }

  /**
   * Get agent performance metrics
   */
  async getAgentPerformanceMetrics(periodHours: number = 24): Promise<AgentMetrics[]> {
    const response = await apiClient.get<{ agent_metrics: Record<string, any> }>(`/analytics/dashboard/agent-performance?period_hours=${periodHours}`)
    
    // Transform backend response to frontend format
    const agentMetrics: AgentMetrics[] = Object.entries(response.data.agent_metrics).map(([agentType, metrics]: [string, any]) => ({
      agentType: agentType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
      totalExecutions: metrics.total_executions || 0,
      successRate: metrics.success_rate || 0,
      averageTime: metrics.average_execution_time || 0,
      cost: metrics.total_cost || 0,
      status: this.getAgentStatus(metrics.success_rate || 0)
    }))

    return agentMetrics
  }

  /**
   * Get contract processing metrics
   */
  async getContractMetrics(periodHours: number = 24): Promise<ContractMetrics> {
    const response = await apiClient.get<any>(`/analytics/dashboard/contract-processing?period_hours=${periodHours}`)
    
    return {
      totalContracts: response.data.total_contracts || 0,
      contractsByStatus: response.data.contracts_by_status || {},
      averageProcessingTime: response.data.average_processing_time || 0,
      completionRate: response.data.completion_rate || 0,
      monthlyTrend: response.data.monthly_trend || []
    }
  }

  /**
   * Get cost analysis metrics
   */
  async getCostMetrics(periodHours: number = 24): Promise<CostMetrics> {
    const response = await apiClient.get<any>(`/analytics/dashboard/cost-analysis?period_hours=${periodHours}`)
    
    return {
      totalCost: response.data.total_cost || 0,
      costByCategory: response.data.cost_by_category || [],
      costByService: response.data.cost_by_service || [],
      monthlyTrend: response.data.monthly_trend || []
    }
  }

  /**
   * Get user behavior metrics
   */
  async getUserBehaviorMetrics(periodHours: number = 24): Promise<UserBehaviorMetrics> {
    const response = await apiClient.get<any>(`/analytics/dashboard/user-behavior?period_hours=${periodHours}`)
    
    return {
      activeUsers: response.data.active_users || 0,
      userActivityTrends: response.data.activity_trends || [],
      featureUsage: response.data.feature_usage || [],
      userRetention: response.data.user_retention || 0
    }
  }

  /**
   * Get predictive analytics metrics
   */
  async getPredictiveMetrics(): Promise<PredictiveMetrics> {
    const response = await apiClient.get<any>('/analytics/dashboard/predictive-analytics')
    
    return {
      modelPerformance: response.data.model_performance || [],
      predictions: response.data.predictions || []
    }
  }

  /**
   * Get executive summary
   */
  async getExecutiveSummary(periodHours: number = 24): Promise<ExecutiveSummary> {
    const response = await apiClient.get<any>(`/analytics/dashboard/executive-summary?period_hours=${periodHours}`)
    
    return {
      kpis: response.data.kpis || [],
      alerts: response.data.alerts || []
    }
  }

  /**
   * Get real-time metrics (for WebSocket updates)
   */
  async getRealTimeMetrics(): Promise<{
    activeAgents: number
    processingJobs: number
    systemLoad: number
    errorRate: number
  }> {
    const response = await apiClient.get<any>('/analytics/real-time')
    return response.data
  }

  /**
   * Get deal metrics for dashboard
   */
  async getDealMetrics(): Promise<{
    totalDeals: number
    dealsInProgress: number
    completedDeals: number
    dealsByStatus: Record<string, number>
  }> {
    const response = await apiClient.get<any>('/analytics/deals')
    return response.data
  }

  /**
   * Get file upload metrics
   */
  async getFileMetrics(): Promise<{
    totalUploads: number
    recentUploads: number
    processingQueue: number
    storageUsed: number
  }> {
    const response = await apiClient.get<any>('/analytics/files')
    return response.data
  }

  /**
   * Helper method to determine agent status based on success rate
   */
  private getAgentStatus(successRate: number): 'healthy' | 'warning' | 'error' {
    if (successRate >= 95) return 'healthy'
    if (successRate >= 85) return 'warning'
    return 'error'
  }

  /**
   * Format currency values
   */
  formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value)
  }

  /**
   * Format percentage values
   */
  formatPercentage(value: number): string {
    return `${value.toFixed(1)}%`
  }

  /**
   * Format time duration
   */
  formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`
    return `${(seconds / 3600).toFixed(1)}h`
  }

  /**
   * Calculate trend direction and percentage
   */
  calculateTrend(current: number, previous: number): { direction: 'up' | 'down' | 'stable'; percentage: string } {
    if (previous === 0) return { direction: 'stable', percentage: '0%' }
    
    const change = ((current - previous) / previous) * 100
    const direction = change > 1 ? 'up' : change < -1 ? 'down' : 'stable'
    const percentage = `${change > 0 ? '+' : ''}${change.toFixed(1)}%`
    
    return { direction, percentage }
  }
}

export const analyticsService = new AnalyticsService()
export default analyticsService
