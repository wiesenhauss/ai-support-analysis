import { useDashboardStats, useSentimentTrend, useTopicDistribution } from '@/hooks/useDashboard'
import { useWeeklyInsights } from '@/hooks/useInsights'
import MetricCard from '@/components/MetricCard'
import { Card, CardHeader } from '@/components/Card'
import { PageLoader } from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import EmptyState from '@/components/EmptyState'
import { formatNumber, formatPercent } from '@/lib/utils'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { MessageSquare, ThumbsUp, CheckCircle, AlertTriangle } from 'lucide-react'

const COLORS = ['#22c55e', '#6b7280', '#ef4444']
const TOPIC_COLORS = ['#0ea5e9', '#8b5cf6', '#f59e0b', '#ef4444', '#10b981', '#6366f1', '#ec4899', '#14b8a6', '#f97316', '#84cc16']

export default function Dashboard() {
  const { data: stats, loading: statsLoading, error: statsError } = useDashboardStats()
  const { data: sentimentTrend, loading: trendLoading } = useSentimentTrend('week')
  const { data: topics, loading: topicsLoading } = useTopicDistribution()
  const { data: insights, loading: insightsLoading } = useWeeklyInsights()

  if (statsLoading) {
    return <PageLoader />
  }

  if (statsError) {
    return (
      <div className="max-w-2xl mx-auto mt-8">
        <Alert variant="error" title="Error loading dashboard">
          {statsError.message}. Make sure the backend server is running.
        </Alert>
      </div>
    )
  }

  if (!stats || stats.ticket_count === 0) {
    return (
      <EmptyState
        title="No data available"
        description="Import analyzed CSV files to see your dashboard. Go to the Analyze page to get started."
        action={
          <a href="/analyze" className="btn btn-primary">
            Start Analyzing
          </a>
        }
      />
    )
  }

  const sentimentPieData = [
    { name: 'Positive', value: stats.sentiment.positive, color: COLORS[0] },
    { name: 'Neutral', value: stats.sentiment.neutral, color: COLORS[1] },
    { name: 'Negative', value: stats.sentiment.negative, color: COLORS[2] },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Overview of your support analytics
        </p>
      </div>

      {/* Critical Insights Alert */}
      {insights && insights.summary.critical > 0 && (
        <Alert variant="warning" title={`${insights.summary.critical} Critical Insight${insights.summary.critical > 1 ? 's' : ''}`}>
          {insights.insights
            .filter((i) => i.severity === 'critical')
            .slice(0, 2)
            .map((i) => i.title)
            .join(', ')}
          . <a href="/insights" className="underline">View all insights</a>
        </Alert>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Tickets"
          value={formatNumber(stats.ticket_count)}
          icon={<MessageSquare className="w-5 h-5" />}
        />
        <MetricCard
          title="CSAT Score"
          value={formatPercent(stats.csat.satisfaction_rate)}
          icon={<ThumbsUp className="w-5 h-5" />}
          trend={stats.csat.satisfaction_rate >= 70 ? 'up' : stats.csat.satisfaction_rate >= 50 ? 'neutral' : 'down'}
        />
        <MetricCard
          title="Resolution Rate"
          value={formatPercent(stats.resolution.resolution_rate)}
          icon={<CheckCircle className="w-5 h-5" />}
          trend={stats.resolution.resolution_rate >= 70 ? 'up' : stats.resolution.resolution_rate >= 50 ? 'neutral' : 'down'}
        />
        <MetricCard
          title="Negative Sentiment"
          value={formatPercent(stats.sentiment.negative_pct)}
          icon={<AlertTriangle className="w-5 h-5" />}
          trend={stats.sentiment.negative_pct <= 20 ? 'up' : stats.sentiment.negative_pct <= 35 ? 'neutral' : 'down'}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Trend */}
        <Card>
          <CardHeader
            title="Sentiment Trend"
            description="Weekly sentiment distribution"
          />
          {trendLoading ? (
            <div className="h-64 flex items-center justify-center">
              <PageLoader />
            </div>
          ) : sentimentTrend && sentimentTrend.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sentimentTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="period"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => {
                      const date = new Date(value)
                      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(value: number) => [`${value.toFixed(1)}%`, '']}
                    labelFormatter={(label) => new Date(label).toLocaleDateString()}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="positive_pct"
                    name="Positive"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="neutral_pct"
                    name="Neutral"
                    stroke="#6b7280"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="negative_pct"
                    name="Negative"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No trend data available
            </div>
          )}
        </Card>

        {/* Sentiment Distribution Pie */}
        <Card>
          <CardHeader
            title="Sentiment Distribution"
            description="Overall sentiment breakdown"
          />
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={sentimentPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {sentimentPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => [formatNumber(value), 'Tickets']}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Top Topics */}
      <Card>
        <CardHeader
          title="Top Topics"
          description="Most common support topics"
        />
        {topicsLoading ? (
          <div className="h-64 flex items-center justify-center">
            <PageLoader />
          </div>
        ) : topics && topics.length > 0 ? (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={topics.slice(0, 10)}
                layout="vertical"
                margin={{ left: 150 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis
                  type="category"
                  dataKey="topic"
                  tick={{ fontSize: 12 }}
                  width={140}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    name === 'count' ? formatNumber(value) : `${value.toFixed(1)}%`,
                    name === 'count' ? 'Tickets' : 'Percentage',
                  ]}
                />
                <Bar dataKey="count" fill="#0ea5e9" radius={[0, 4, 4, 0]}>
                  {topics.slice(0, 10).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={TOPIC_COLORS[index % TOPIC_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-64 flex items-center justify-center text-gray-500">
            No topic data available
          </div>
        )}
      </Card>

      {/* Quick Stats Footer */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
          <p className="text-2xl font-bold text-success-600">{formatNumber(stats.sentiment.positive)}</p>
          <p className="text-sm text-gray-500">Positive Tickets</p>
        </div>
        <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
          <p className="text-2xl font-bold text-gray-600">{formatNumber(stats.sentiment.neutral)}</p>
          <p className="text-sm text-gray-500">Neutral Tickets</p>
        </div>
        <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
          <p className="text-2xl font-bold text-danger-600">{formatNumber(stats.sentiment.negative)}</p>
          <p className="text-sm text-gray-500">Negative Tickets</p>
        </div>
        <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
          <p className="text-2xl font-bold text-primary-600">{formatNumber(stats.resolution.resolved)}</p>
          <p className="text-sm text-gray-500">Resolved Issues</p>
        </div>
      </div>
    </div>
  )
}
