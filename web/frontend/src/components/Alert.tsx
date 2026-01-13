import { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react'

type AlertVariant = 'info' | 'success' | 'warning' | 'error'

interface AlertProps {
  variant?: AlertVariant
  title?: string
  children: ReactNode
  className?: string
}

const variants: Record<AlertVariant, { icon: typeof Info; classes: string }> = {
  info: {
    icon: Info,
    classes: 'bg-blue-50 text-blue-800 border-blue-200',
  },
  success: {
    icon: CheckCircle,
    classes: 'bg-success-50 text-success-600 border-green-200',
  },
  warning: {
    icon: AlertCircle,
    classes: 'bg-warning-50 text-warning-600 border-yellow-200',
  },
  error: {
    icon: XCircle,
    classes: 'bg-danger-50 text-danger-600 border-red-200',
  },
}

export default function Alert({ variant = 'info', title, children, className }: AlertProps) {
  const { icon: Icon, classes } = variants[variant]

  return (
    <div className={cn('flex gap-3 p-4 rounded-lg border', classes, className)}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>
        {title && <p className="font-medium mb-1">{title}</p>}
        <div className="text-sm">{children}</div>
      </div>
    </div>
  )
}
