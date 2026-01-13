import { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon?: ReactNode
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}

export default function MetricCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  trend,
  className,
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (!trend) return null
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-success-500" />
      case 'down':
        return <TrendingDown className="w-4 h-4 text-danger-500" />
      default:
        return <Minus className="w-4 h-4 text-gray-400" />
    }
  }

  const getTrendColor = () => {
    if (!trend) return 'text-gray-500'
    switch (trend) {
      case 'up':
        return 'text-success-600'
      case 'down':
        return 'text-danger-600'
      default:
        return 'text-gray-500'
    }
  }

  return (
    <div className={cn('card p-6', className)}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="mt-2">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        {(change !== undefined || changeLabel) && (
          <div className="flex items-center gap-1 mt-2">
            {getTrendIcon()}
            <span className={cn('text-sm font-medium', getTrendColor())}>
              {change !== undefined && (
                <span>{change > 0 ? '+' : ''}{change.toFixed(1)}%</span>
              )}
              {changeLabel && <span className="text-gray-500 ml-1">{changeLabel}</span>}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
