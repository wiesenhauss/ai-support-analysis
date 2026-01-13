import { useCallback } from 'react'
import { useApi } from './useApi'
import api from '@/api/client'

interface Insight {
  type: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  description: string
  metric_name: string
  current_value: number
  previous_value: number
  change_percent: number
  period_start: string
  period_end: string
  recommendations: string[]
}

interface InsightsSummary {
  total: number
  critical: number
  warning: number
  info: number
  top_concerns: Array<{ title: string; severity: string; change: number }>
  positive_trends: Array<{ title: string; change: number }>
}

interface InsightsResponse {
  insights: Insight[]
  summary: InsightsSummary
}

export function useWeeklyInsights() {
  const fetchInsights = useCallback(
    () => api.insights.getWeekly() as Promise<InsightsResponse>,
    []
  )

  return useApi(fetchInsights)
}

export function useMonthlyInsights() {
  const fetchInsights = useCallback(
    () => api.insights.getMonthly() as Promise<InsightsResponse>,
    []
  )

  return useApi(fetchInsights)
}

interface AnomaliesResponse {
  anomalies: Insight[]
  period: { start: string; end: string }
  comparison_period: { start: string; end: string }
}

export function useAnomalies(startDate?: string, endDate?: string) {
  const fetchAnomalies = useCallback(
    () => api.insights.getAnomalies(startDate, endDate) as Promise<AnomaliesResponse>,
    [startDate, endDate]
  )

  return useApi(fetchAnomalies)
}

interface EmergingInsight {
  product_area: string
  growth_pct: number
  ticket_count: number
  negative_pct: number
  impact_score: number
}

export function useEmergingTopics(days = 14) {
  const fetchEmergingTopics = useCallback(
    () => api.insights.getEmergingTopics(days) as Promise<EmergingInsight[]>,
    [days]
  )

  return useApi(fetchEmergingTopics)
}
