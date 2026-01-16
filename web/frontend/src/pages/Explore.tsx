import { useState, useCallback, useEffect } from 'react'
import { Card, CardHeader } from '@/components/Card'
import { PageLoader } from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import EmptyState from '@/components/EmptyState'
import { cn, formatDate } from '@/lib/utils'
import api from '@/api/client'
import { Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react'

interface Ticket {
  id: number
  ticket_id: string | null
  created_date: string | null
  csat_rating: string | null
  sentiment: string | null
  issue_resolved: boolean | null
  main_topic: string | null
  customer_goal: string | null
  detail_summary: string | null
  product_area: string | null
}

interface TicketsResponse {
  tickets: Ticket[]
  total_count: number
  page: number
  page_size: number
}

interface Filters {
  [key: string]: string | number | boolean | undefined
  start_date: string
  end_date: string
  sentiment: string
  csat_rating: string
  main_topic: string
  product_area: string
  issue_resolved: string
  search: string
  page: number
  page_size: number
}

export default function Explore() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [topics, setTopics] = useState<string[]>([])
  const [productAreas, setProductAreas] = useState<string[]>([])
  const [showFilters, setShowFilters] = useState(false)
  
  const [filters, setFilters] = useState<Filters>({
    start_date: '',
    end_date: '',
    sentiment: '',
    csat_rating: '',
    main_topic: '',
    product_area: '',
    issue_resolved: '',
    search: '',
    page: 1,
    page_size: 25,
  })

  const fetchTickets = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.data.getTickets(filters) as TicketsResponse
      setTickets(response.tickets)
      setTotalCount(response.total_count)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tickets')
    } finally {
      setLoading(false)
    }
  }, [filters])

  const fetchFilterOptions = useCallback(async () => {
    try {
      const [topicsRes, areasRes] = await Promise.all([
        api.data.getTopics() as Promise<{ topics: string[] }>,
        api.data.getProductAreas() as Promise<{ product_areas: string[] }>,
      ])
      setTopics(topicsRes.topics)
      setProductAreas(areasRes.product_areas)
    } catch (err) {
      console.error('Failed to load filter options:', err)
    }
  }, [])

  useEffect(() => {
    fetchTickets()
  }, [fetchTickets])

  useEffect(() => {
    fetchFilterOptions()
  }, [fetchFilterOptions])

  const handleFilterChange = (key: keyof Filters, value: string | number) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      page: key !== 'page' ? 1 : (value as number),
    }))
  }

  const totalPages = Math.ceil(totalCount / filters.page_size)

  const getSentimentColor = (sentiment: string | null) => {
    switch (sentiment) {
      case 'Positive':
        return 'bg-success-50 text-success-600'
      case 'Negative':
        return 'bg-danger-50 text-danger-600'
      default:
        return 'bg-gray-100 text-gray-600'
    }
  }

  const getCSATColor = (csat: string | null) => {
    if (!csat) return 'bg-gray-100 text-gray-500'
    return csat.toLowerCase() === 'good'
      ? 'bg-success-50 text-success-600'
      : 'bg-danger-50 text-danger-600'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Explore Data</h1>
          <p className="text-gray-500 mt-1">
            Search and filter your support tickets
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'btn btn-secondary',
            showFilters && 'bg-primary-100 text-primary-700'
          )}
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
        </button>
      </div>

      {error && (
        <Alert variant="error">{error}</Alert>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          className="input pl-10"
          placeholder="Search tickets by summary or customer goal..."
          value={filters.search}
          onChange={(e) => handleFilterChange('search', e.target.value)}
        />
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardHeader title="Filters" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="label">Start Date</label>
              <input
                type="date"
                className="input"
                value={filters.start_date}
                onChange={(e) => handleFilterChange('start_date', e.target.value)}
              />
            </div>
            <div>
              <label className="label">End Date</label>
              <input
                type="date"
                className="input"
                value={filters.end_date}
                onChange={(e) => handleFilterChange('end_date', e.target.value)}
              />
            </div>
            <div>
              <label className="label">Sentiment</label>
              <select
                className="input"
                value={filters.sentiment}
                onChange={(e) => handleFilterChange('sentiment', e.target.value)}
              >
                <option value="">All</option>
                <option value="Positive">Positive</option>
                <option value="Neutral">Neutral</option>
                <option value="Negative">Negative</option>
              </select>
            </div>
            <div>
              <label className="label">CSAT Rating</label>
              <select
                className="input"
                value={filters.csat_rating}
                onChange={(e) => handleFilterChange('csat_rating', e.target.value)}
              >
                <option value="">All</option>
                <option value="good">Good</option>
                <option value="bad">Bad</option>
              </select>
            </div>
            <div>
              <label className="label">Topic</label>
              <select
                className="input"
                value={filters.main_topic}
                onChange={(e) => handleFilterChange('main_topic', e.target.value)}
              >
                <option value="">All Topics</option>
                {topics.map((topic) => (
                  <option key={topic} value={topic}>{topic}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Product Area</label>
              <select
                className="input"
                value={filters.product_area}
                onChange={(e) => handleFilterChange('product_area', e.target.value)}
              >
                <option value="">All Areas</option>
                {productAreas.map((area) => (
                  <option key={area} value={area}>{area}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Issue Resolved</label>
              <select
                className="input"
                value={filters.issue_resolved}
                onChange={(e) => handleFilterChange('issue_resolved', e.target.value)}
              >
                <option value="">All</option>
                <option value="true">Resolved</option>
                <option value="false">Unresolved</option>
              </select>
            </div>
            <div>
              <label className="label">Per Page</label>
              <select
                className="input"
                value={filters.page_size}
                onChange={(e) => handleFilterChange('page_size', parseInt(e.target.value))}
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>
        </Card>
      )}

      {/* Results */}
      <Card className="p-0">
        <div className="px-6 py-4 border-b border-gray-200">
          <p className="text-sm text-gray-500">
            Showing {tickets.length} of {totalCount.toLocaleString()} tickets
          </p>
        </div>

        {loading ? (
          <div className="p-8">
            <PageLoader />
          </div>
        ) : tickets.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No tickets found"
              description="Try adjusting your filters or search query"
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Summary
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Topic
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sentiment
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    CSAT
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Resolved
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {tickets.map((ticket) => (
                  <tr key={ticket.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {ticket.created_date ? formatDate(ticket.created_date) : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-md">
                      <p className="truncate" title={ticket.detail_summary || ''}>
                        {ticket.detail_summary || ticket.customer_goal || '-'}
                      </p>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {ticket.main_topic?.split(',')[0] || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={cn(
                        'px-2 py-1 text-xs font-medium rounded-full',
                        getSentimentColor(ticket.sentiment)
                      )}>
                        {ticket.sentiment || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={cn(
                        'px-2 py-1 text-xs font-medium rounded-full capitalize',
                        getCSATColor(ticket.csat_rating)
                      )}>
                        {ticket.csat_rating || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {ticket.issue_resolved === true && (
                        <span className="text-success-600">Yes</span>
                      )}
                      {ticket.issue_resolved === false && (
                        <span className="text-danger-600">No</span>
                      )}
                      {ticket.issue_resolved === null && (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Page {filters.page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => handleFilterChange('page', Math.max(1, filters.page - 1))}
                disabled={filters.page === 1}
                className="btn btn-secondary"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleFilterChange('page', Math.min(totalPages, filters.page + 1))}
                disabled={filters.page === totalPages}
                className="btn btn-secondary"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
