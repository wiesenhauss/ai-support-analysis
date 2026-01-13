import { useCallback } from 'react'
import { useApi } from './useApi'
import api from '@/api/client'

interface SummaryStats {
  ticket_count: number
  sentiment: {
    positive: number
    neutral: number
    negative: number
    positive_pct: number
    neutral_pct: number
    negative_pct: number
    total: number
  }
  resolution: {
    resolved: number
    unresolved: number
    resolution_rate: number
    total: number
  }
  csat: {
    good: number
    bad: number
    satisfaction_rate: number
    response_rate: number
    total: number
  }
  top_topics: Array<{
    topic: string
    count: number
    percentage: number
  }>
  product_related: number
  service_related: number
}

interface SentimentTrendPoint {
  period: string
  positive: number
  neutral: number
  negative: number
  positive_pct: number
  neutral_pct: number
  negative_pct: number
}

interface CSATTrendPoint {
  period: string
  good: number
  bad: number
  satisfaction_rate: number
}

export function useDashboardStats(startDate?: string, endDate?: string) {
  const fetchStats = useCallback(
    () => api.analytics.getSummary(startDate, endDate) as Promise<SummaryStats>,
    [startDate, endDate]
  )

  return useApi(fetchStats)
}

export function useSentimentTrend(
  granularity = 'week',
  startDate?: string,
  endDate?: string
) {
  const fetchTrend = useCallback(
    () =>
      api.analytics.getSentimentTrend(granularity, startDate, endDate) as Promise<
        SentimentTrendPoint[]
      >,
    [granularity, startDate, endDate]
  )

  return useApi(fetchTrend)
}

export function useCSATTrend(
  granularity = 'week',
  startDate?: string,
  endDate?: string
) {
  const fetchTrend = useCallback(
    () =>
      api.analytics.getCSATTrend(granularity, startDate, endDate) as Promise<
        CSATTrendPoint[]
      >,
    [granularity, startDate, endDate]
  )

  return useApi(fetchTrend)
}

export function useTopicDistribution(
  startDate?: string,
  endDate?: string,
  topN = 10
) {
  const fetchTopics = useCallback(
    () =>
      api.analytics.getTopicDistribution(startDate, endDate, topN) as Promise<
        Array<{ topic: string; count: number; percentage: number }>
      >,
    [startDate, endDate, topN]
  )

  return useApi(fetchTopics)
}
