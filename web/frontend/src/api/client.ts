/**
 * API Client for the AI Support Analyzer backend
 */

const API_BASE = '/api'

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message)
    this.name = 'APIError'
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new APIError(
      error.detail || `HTTP ${response.status}`,
      response.status,
      error.detail
    )
  }
  return response.json()
}

export const api = {
  // Analytics endpoints
  analytics: {
    getSummary: async (startDate?: string, endDate?: string) => {
      const params = new URLSearchParams()
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      const url = `${API_BASE}/analytics/summary?${params}`
      return handleResponse(await fetch(url))
    },

    getSentimentTrend: async (granularity = 'week', startDate?: string, endDate?: string) => {
      const params = new URLSearchParams({ granularity })
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      return handleResponse(await fetch(`${API_BASE}/analytics/sentiment-trend?${params}`))
    },

    getTopicDistribution: async (startDate?: string, endDate?: string, topN = 10) => {
      const params = new URLSearchParams({ top_n: String(topN) })
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      return handleResponse(await fetch(`${API_BASE}/analytics/topic-distribution?${params}`))
    },

    getCSATTrend: async (granularity = 'week', startDate?: string, endDate?: string) => {
      const params = new URLSearchParams({ granularity })
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      return handleResponse(await fetch(`${API_BASE}/analytics/csat-trend?${params}`))
    },

    getResolutionTrend: async (granularity = 'week', startDate?: string, endDate?: string) => {
      const params = new URLSearchParams({ granularity })
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      return handleResponse(await fetch(`${API_BASE}/analytics/resolution-trend?${params}`))
    },

    comparePeriods: async (
      period1Start: string,
      period1End: string,
      period2Start: string,
      period2End: string
    ) => {
      const params = new URLSearchParams({
        period1_start: period1Start,
        period1_end: period1End,
        period2_start: period2Start,
        period2_end: period2End,
      })
      return handleResponse(await fetch(`${API_BASE}/analytics/compare-periods?${params}`))
    },
  },

  // Insights endpoints
  insights: {
    getWeekly: async () => {
      return handleResponse(await fetch(`${API_BASE}/insights/weekly`))
    },

    getMonthly: async () => {
      return handleResponse(await fetch(`${API_BASE}/insights/monthly`))
    },

    getEmergingTopics: async (days = 14) => {
      return handleResponse(await fetch(`${API_BASE}/insights/emerging-topics?days=${days}`))
    },

    getAnomalies: async (startDate?: string, endDate?: string) => {
      const params = new URLSearchParams()
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      return handleResponse(await fetch(`${API_BASE}/insights/anomalies?${params}`))
    },
  },

  // Data management endpoints
  data: {
    getStats: async () => {
      return handleResponse(await fetch(`${API_BASE}/data/stats`))
    },

    getBatches: async () => {
      return handleResponse(await fetch(`${API_BASE}/data/batches`))
    },

    deleteBatch: async (batchId: number) => {
      return handleResponse(
        await fetch(`${API_BASE}/data/batches/${batchId}`, { method: 'DELETE' })
      )
    },

    importCSV: async (file: File, notes?: string) => {
      const formData = new FormData()
      formData.append('file', file)
      if (notes) formData.append('notes', notes)
      return handleResponse(
        await fetch(`${API_BASE}/data/import`, {
          method: 'POST',
          body: formData,
        })
      )
    },

    getTickets: async (filters: Record<string, string | number | boolean | undefined>) => {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value))
        }
      })
      return handleResponse(await fetch(`${API_BASE}/data/tickets?${params}`))
    },

    getDateRange: async () => {
      return handleResponse(await fetch(`${API_BASE}/data/date-range`))
    },

    getTopics: async () => {
      return handleResponse(await fetch(`${API_BASE}/data/topics`))
    },

    getProductAreas: async () => {
      return handleResponse(await fetch(`${API_BASE}/data/product-areas`))
    },
  },

  // Analysis endpoints
  analysis: {
    start: async (file: File, options: Record<string, unknown>) => {
      const formData = new FormData()
      formData.append('file', file)
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(key, String(value))
        }
      })
      return handleResponse(
        await fetch(`${API_BASE}/analysis/start`, {
          method: 'POST',
          body: formData,
        })
      )
    },

    getStatus: async (jobId: string) => {
      return handleResponse(await fetch(`${API_BASE}/analysis/${jobId}/status`))
    },

    cancel: async (jobId: string) => {
      return handleResponse(
        await fetch(`${API_BASE}/analysis/${jobId}`, { method: 'DELETE' })
      )
    },

    list: async () => {
      return handleResponse(await fetch(`${API_BASE}/analysis/`))
    },

    getLogs: async (jobId: string, lastN = 100) => {
      return handleResponse(await fetch(`${API_BASE}/analysis/${jobId}/logs?last_n=${lastN}`))
    },
  },

  // Talk to Data endpoints
  talk: {
    askQuestion: async (question: string, columns?: string[], isFollowUp = false) => {
      return handleResponse(
        await fetch(`${API_BASE}/talk/question`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, columns, is_follow_up: isFollowUp }),
        })
      )
    },

    getColumns: async () => {
      return handleResponse(await fetch(`${API_BASE}/talk/columns`))
    },

    reset: async () => {
      return handleResponse(
        await fetch(`${API_BASE}/talk/reset`, { method: 'POST' })
      )
    },
  },
}

export default api
