/**
 * API Client for the AI Support Analyzer backend
 */

const API_BASE = '/api'

// ============== Type Definitions ==============

export interface CustomTicketAnalysis {
  name: string
  prompt: string
  result_type: 'boolean' | 'string'
  description: string
  columns: string[]
  enabled?: boolean
}

export interface CustomPrompt {
  name: string
  prompt: string
  columns: string[]
  created?: string
  last_used?: string
}

export interface ColumnMatchInfo {
  expected_name: string
  matched_column: string | null
  required: boolean
  description: string
}

export interface ReportImpact {
  report: string
  impact: string
  missing_column: string
}

export interface ValidateColumnsResponse {
  all_required_matched: boolean
  columns: ColumnMatchInfo[]
  available_columns: string[]
  report_impacts: ReportImpact[]
}

export interface AdvancedSettings {
  api_timeout: number
  max_retries: number
  batch_size: number
  concurrent_threads: number
}

export interface OutputFile {
  name: string
  path: string
  size_mb: number
  modified: number
}

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

    getTopicTrend: async (topic: string, granularity = 'week', startDate?: string, endDate?: string) => {
      const params = new URLSearchParams({ topic, granularity })
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      return handleResponse(await fetch(`${API_BASE}/analytics/topic-trend?${params}`))
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

    // Database Export/Import
    exportDatabase: async () => {
      const response = await fetch(`${API_BASE}/data/export-database`)
      if (!response.ok) {
        throw new APIError('Export failed', response.status)
      }
      const blob = await response.blob()
      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics_export_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.db`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    },

    importDatabase: async (file: File): Promise<{
      message: string
      backup_path: string | null
      imported_tickets: number
      imported_batches: number
    }> => {
      const formData = new FormData()
      formData.append('file', file)
      return handleResponse(
        await fetch(`${API_BASE}/data/import-database`, {
          method: 'POST',
          body: formData,
        })
      )
    },
  },

  // Analysis endpoints
  analysis: {
    validateColumns: async (columns: string[]): Promise<ValidateColumnsResponse> => {
      return handleResponse(
        await fetch(`${API_BASE}/analysis/validate-columns`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ columns }),
        })
      )
    },

    start: async (file: File, options: Record<string, unknown>) => {
      const formData = new FormData()
      formData.append('file', file)
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (key === 'column_mapping' && typeof value === 'object') {
            formData.append(key, JSON.stringify(value))
          } else {
            formData.append(key, String(value))
          }
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

    getFiles: async (jobId: string): Promise<{ files: OutputFile[] }> => {
      return handleResponse(await fetch(`${API_BASE}/analysis/${jobId}/files`))
    },

    downloadFile: async (jobId: string, filename: string) => {
      const response = await fetch(`${API_BASE}/analysis/${jobId}/files/${encodeURIComponent(filename)}`)
      if (!response.ok) {
        throw new APIError('Download failed', response.status)
      }
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
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

  // Settings endpoints
  settings: {
    get: async () => {
      return handleResponse(await fetch(`${API_BASE}/settings/`))
    },

    getApiKeyStatus: async () => {
      return handleResponse(await fetch(`${API_BASE}/settings/api-key/status`))
    },

    setApiKey: async (apiKey: string) => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/api-key`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey }),
        })
      )
    },

    deleteApiKey: async () => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/api-key`, { method: 'DELETE' })
      )
    },

    validateApiKey: async (apiKey: string) => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/api-key/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey }),
        })
      )
    },

    // Custom Per-Ticket Analyses
    getCustomTicketAnalyses: async (): Promise<{ analyses: CustomTicketAnalysis[] }> => {
      return handleResponse(await fetch(`${API_BASE}/settings/custom-ticket-analyses`))
    },

    saveCustomTicketAnalyses: async (analyses: CustomTicketAnalysis[]) => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/custom-ticket-analyses`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ analyses }),
        })
      )
    },

    deleteCustomTicketAnalysis: async (name: string) => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/custom-ticket-analyses/${encodeURIComponent(name)}`, {
          method: 'DELETE',
        })
      )
    },

    // Custom Prompts
    getCustomPrompts: async (): Promise<{ prompts: Record<string, CustomPrompt> }> => {
      return handleResponse(await fetch(`${API_BASE}/settings/custom-prompts`))
    },

    saveCustomPrompt: async (name: string, prompt: CustomPrompt) => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/custom-prompts/${encodeURIComponent(name)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(prompt),
        })
      )
    },

    deleteCustomPrompt: async (name: string) => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/custom-prompts/${encodeURIComponent(name)}`, {
          method: 'DELETE',
        })
      )
    },

    // Advanced Settings
    getAdvancedSettings: async (): Promise<AdvancedSettings> => {
      return handleResponse(await fetch(`${API_BASE}/settings/advanced`))
    },

    saveAdvancedSettings: async (settings: AdvancedSettings) => {
      return handleResponse(
        await fetch(`${API_BASE}/settings/advanced`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(settings),
        })
      )
    },
  },
}

export default api
