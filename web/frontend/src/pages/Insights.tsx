import { useState, useEffect } from 'react'
import { useWeeklyInsights, useMonthlyInsights, useEmergingTopics, useAnomalies } from '@/hooks/useInsights'
import { Card, CardHeader } from '@/components/Card'
import { PageLoader } from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import EmptyState from '@/components/EmptyState'
import DateRangePicker from '@/components/DateRangePicker'
import { cn, formatPercent } from '@/lib/utils'
import { AlertTriangle, TrendingUp, Lightbulb, ArrowUpRight, ArrowDownRight, Calendar } from 'lucide-react'

type TimeRange = 'weekly' | 'monthly' | 'custom'

interface DateRange {
  startDate: string | undefined
  endDate: string | undefined
}

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

export default function Insights() {
  const [timeRange, setTimeRange] = useState<TimeRange>('weekly')
  const [dateRange, setDateRange] = useState<DateRange>({
    startDate: undefined,
    endDate: undefined,
  })
  
  // Calculate days for emerging topics from date range
  const getEmergingDays = () => {
    if (!dateRange.startDate || !dateRange.endDate) return 14
    const start = new Date(dateRange.startDate)
    const end = new Date(dateRange.endDate)
    const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1
    return Math.max(7, Math.min(90, days)) // Clamp between 7-90 days
  }
  
  const weeklyData = useWeeklyInsights()
  const monthlyData = useMonthlyInsights()
  const anomaliesData = useAnomalies(dateRange.startDate, dateRange.endDate)
  const emergingData = useEmergingTopics(getEmergingDays())
  
  // Determine which data to show
  const getActiveData = () => {
    if (timeRange === 'custom') {
      return {
        data: anomaliesData.data ? {
          insights: anomaliesData.data.anomalies,
          summary: {
            total: anomaliesData.data.anomalies.length,
            critical: anomaliesData.data.anomalies.filter((a: Insight) => a.severity === 'critical').length,
            warning: anomaliesData.data.anomalies.filter((a: Insight) => a.severity === 'warning').length,
            info: anomaliesData.data.anomalies.filter((a: Insight) => a.severity === 'info').length,
          }
        } : null,
        loading: anomaliesData.loading,
        error: anomaliesData.error,
      }
    }
    return timeRange === 'weekly' ? weeklyData : monthlyData
  }

  const { data, loading, error } = getActiveData()

  // When date range changes to a custom range, switch to custom mode
  useEffect(() => {
    if (dateRange.startDate || dateRange.endDate) {
      setTimeRange('custom')
    }
  }, [dateRange])

  const handleTimeRangeChange = (range: TimeRange) => {
    setTimeRange(range)
    if (range !== 'custom') {
      setDateRange({ startDate: undefined, endDate: undefined })
    }
  }

  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-l-danger-500 bg-danger-50'
      case 'warning':
        return 'border-l-warning-500 bg-warning-50'
      default:
        return 'border-l-primary-500 bg-primary-50'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-5 h-5 text-danger-500" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-warning-500" />
      default:
        return <Lightbulb className="w-5 h-5 text-primary-500" />
    }
  }

  const getChangeIcon = (change: number) => {
    if (change > 0) {
      return <ArrowUpRight className="w-4 h-4 text-success-500" />
    } else if (change < 0) {
      return <ArrowDownRight className="w-4 h-4 text-danger-500" />
    }
    return null
  }

  if (loading) {
    return <PageLoader />
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto mt-8">
        <Alert variant="error" title="Error loading insights">
          {error.message}
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Insights</h1>
            <p className="text-gray-500 mt-1">
              AI-powered insights and anomaly detection
            </p>
          </div>
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </div>
        
        {/* Time Range Tabs */}
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-gray-200 overflow-hidden">
            <button
              onClick={() => handleTimeRangeChange('weekly')}
              className={cn(
                'px-4 py-2 text-sm font-medium',
                timeRange === 'weekly'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              )}
            >
              Weekly
            </button>
            <button
              onClick={() => handleTimeRangeChange('monthly')}
              className={cn(
                'px-4 py-2 text-sm font-medium',
                timeRange === 'monthly'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              )}
            >
              Monthly
            </button>
            <button
              onClick={() => handleTimeRangeChange('custom')}
              className={cn(
                'px-4 py-2 text-sm font-medium flex items-center gap-1',
                timeRange === 'custom'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              )}
            >
              <Calendar className="w-4 h-4" />
              Custom
            </button>
          </div>
          {timeRange === 'custom' && anomaliesData.data && (
            <span className="text-sm text-gray-500">
              Comparing {anomaliesData.data.period.start} to {anomaliesData.data.period.end}
            </span>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      {data?.summary && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="card p-4 text-center">
            <p className="text-3xl font-bold text-gray-900">{data.summary.total}</p>
            <p className="text-sm text-gray-500">Total Insights</p>
          </div>
          <div className="card p-4 text-center border-l-4 border-l-danger-500">
            <p className="text-3xl font-bold text-danger-600">{data.summary.critical}</p>
            <p className="text-sm text-gray-500">Critical</p>
          </div>
          <div className="card p-4 text-center border-l-4 border-l-warning-500">
            <p className="text-3xl font-bold text-warning-600">{data.summary.warning}</p>
            <p className="text-sm text-gray-500">Warnings</p>
          </div>
          <div className="card p-4 text-center border-l-4 border-l-primary-500">
            <p className="text-3xl font-bold text-primary-600">{data.summary.info}</p>
            <p className="text-sm text-gray-500">Informational</p>
          </div>
        </div>
      )}

      {/* Insights List */}
      {data?.insights && data.insights.length > 0 ? (
        <div className="space-y-4">
          {data.insights.map((insight: Insight, index: number) => (
            <Card
              key={index}
              className={cn('border-l-4 p-0', getSeverityStyles(insight.severity))}
            >
              <div className="p-6">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 mt-1">
                    {getSeverityIcon(insight.severity)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900">{insight.title}</h3>
                      <span className={cn(
                        'px-2 py-0.5 text-xs font-medium rounded-full uppercase',
                        insight.severity === 'critical' && 'bg-danger-100 text-danger-700',
                        insight.severity === 'warning' && 'bg-warning-100 text-warning-700',
                        insight.severity === 'info' && 'bg-primary-100 text-primary-700'
                      )}>
                        {insight.severity}
                      </span>
                    </div>
                    <p className="text-gray-600 mb-4">{insight.description}</p>
                    
                    {/* Metrics */}
                    <div className="flex flex-wrap gap-6 mb-4">
                      <div>
                        <p className="text-xs text-gray-500 uppercase">Current</p>
                        <p className="text-lg font-semibold">{formatPercent(insight.current_value)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase">Previous</p>
                        <p className="text-lg font-semibold">{formatPercent(insight.previous_value)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase">Change</p>
                        <div className="flex items-center gap-1">
                          {getChangeIcon(insight.change_percent)}
                          <p className={cn(
                            'text-lg font-semibold',
                            insight.change_percent > 0 ? 'text-success-600' : 'text-danger-600'
                          )}>
                            {insight.change_percent > 0 ? '+' : ''}{formatPercent(insight.change_percent)}
                          </p>
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase">Period</p>
                        <p className="text-sm text-gray-700">
                          {new Date(insight.period_start).toLocaleDateString()} - {new Date(insight.period_end).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    {/* Recommendations */}
                    {insight.recommendations.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-2">Recommendations:</p>
                        <ul className="space-y-1">
                          {insight.recommendations.map((rec, i) => (
                            <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                              <span className="text-primary-500 mt-1">•</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Lightbulb className="w-12 h-12 text-gray-300" />}
          title="No insights found"
          description={
            timeRange === 'custom'
              ? "No significant anomalies detected in the selected date range. Try adjusting the dates."
              : "No significant changes detected in the selected time period. Check back later!"
          }
        />
      )}

      {/* Emerging Topics */}
      {emergingData.data && emergingData.data.length > 0 && (
        <Card>
          <CardHeader
            title="Emerging Product Areas"
            description={`Product areas with increasing ticket volume (last ${getEmergingDays()} days)`}
          />
          <div className="space-y-3">
            {emergingData.data.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-warning-500" />
                  <div>
                    <p className="font-medium text-gray-900">{item.product_area}</p>
                    <p className="text-sm text-gray-500">{item.ticket_count} tickets</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-warning-600">
                    +{formatPercent(item.growth_pct)} growth
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatPercent(item.negative_pct)} negative
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
