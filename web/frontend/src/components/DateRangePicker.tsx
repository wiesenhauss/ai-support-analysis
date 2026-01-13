import { useState, useEffect } from 'react'
import { Calendar, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DateRange {
  startDate: string | undefined
  endDate: string | undefined
}

interface DateRangePickerProps {
  value: DateRange
  onChange: (range: DateRange) => void
  className?: string
}

type PresetKey = 'all' | 'today' | 'last7' | 'last30' | 'last90' | 'thisMonth' | 'lastMonth' | 'custom'

const presets: { key: PresetKey; label: string }[] = [
  { key: 'all', label: 'All Time' },
  { key: 'today', label: 'Today' },
  { key: 'last7', label: 'Last 7 Days' },
  { key: 'last30', label: 'Last 30 Days' },
  { key: 'last90', label: 'Last 90 Days' },
  { key: 'thisMonth', label: 'This Month' },
  { key: 'lastMonth', label: 'Last Month' },
  { key: 'custom', label: 'Custom Range' },
]

function getPresetRange(preset: PresetKey): DateRange {
  const today = new Date()
  const formatDate = (d: Date) => d.toISOString().split('T')[0]

  switch (preset) {
    case 'all':
      return { startDate: undefined, endDate: undefined }
    case 'today':
      return { startDate: formatDate(today), endDate: formatDate(today) }
    case 'last7': {
      const start = new Date(today)
      start.setDate(start.getDate() - 6)
      return { startDate: formatDate(start), endDate: formatDate(today) }
    }
    case 'last30': {
      const start = new Date(today)
      start.setDate(start.getDate() - 29)
      return { startDate: formatDate(start), endDate: formatDate(today) }
    }
    case 'last90': {
      const start = new Date(today)
      start.setDate(start.getDate() - 89)
      return { startDate: formatDate(start), endDate: formatDate(today) }
    }
    case 'thisMonth': {
      const start = new Date(today.getFullYear(), today.getMonth(), 1)
      return { startDate: formatDate(start), endDate: formatDate(today) }
    }
    case 'lastMonth': {
      const start = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      const end = new Date(today.getFullYear(), today.getMonth(), 0)
      return { startDate: formatDate(start), endDate: formatDate(end) }
    }
    default:
      return { startDate: undefined, endDate: undefined }
  }
}

function getPresetFromRange(range: DateRange): PresetKey {
  if (!range.startDate && !range.endDate) return 'all'
  
  const today = new Date()
  const formatDate = (d: Date) => d.toISOString().split('T')[0]
  
  for (const preset of presets) {
    if (preset.key === 'all' || preset.key === 'custom') continue
    const presetRange = getPresetRange(preset.key)
    if (presetRange.startDate === range.startDate && presetRange.endDate === range.endDate) {
      return preset.key
    }
  }
  
  return 'custom'
}

export default function DateRangePicker({ value, onChange, className }: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activePreset, setActivePreset] = useState<PresetKey>(() => getPresetFromRange(value))
  const [customStart, setCustomStart] = useState(value.startDate || '')
  const [customEnd, setCustomEnd] = useState(value.endDate || '')

  useEffect(() => {
    setActivePreset(getPresetFromRange(value))
  }, [value])

  const handlePresetClick = (preset: PresetKey) => {
    setActivePreset(preset)
    if (preset !== 'custom') {
      const range = getPresetRange(preset)
      onChange(range)
      setIsOpen(false)
    }
  }

  const handleCustomApply = () => {
    onChange({
      startDate: customStart || undefined,
      endDate: customEnd || undefined,
    })
    setIsOpen(false)
  }

  const getDisplayLabel = () => {
    if (activePreset !== 'custom') {
      return presets.find((p) => p.key === activePreset)?.label || 'All Time'
    }
    if (value.startDate && value.endDate) {
      return `${formatDisplayDate(value.startDate)} - ${formatDisplayDate(value.endDate)}`
    }
    if (value.startDate) {
      return `From ${formatDisplayDate(value.startDate)}`
    }
    if (value.endDate) {
      return `Until ${formatDisplayDate(value.endDate)}`
    }
    return 'Custom Range'
  }

  const formatDisplayDate = (dateStr: string) => {
    const date = new Date(dateStr + 'T00:00:00')
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-700"
      >
        <Calendar className="w-4 h-4 text-gray-500" />
        <span>{getDisplayLabel()}</span>
        <ChevronDown className={cn('w-4 h-4 text-gray-400 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
            <div className="p-2">
              <div className="grid grid-cols-2 gap-1">
                {presets.slice(0, -1).map((preset) => (
                  <button
                    key={preset.key}
                    onClick={() => handlePresetClick(preset.key)}
                    className={cn(
                      'px-3 py-2 text-sm rounded-md text-left',
                      activePreset === preset.key
                        ? 'bg-primary-100 text-primary-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-100'
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="border-t border-gray-200 p-4">
              <p className="text-sm font-medium text-gray-700 mb-3">Custom Range</p>
              <div className="flex gap-2 mb-3">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={customStart}
                    onChange={(e) => {
                      setCustomStart(e.target.value)
                      setActivePreset('custom')
                    }}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">End Date</label>
                  <input
                    type="date"
                    value={customEnd}
                    onChange={(e) => {
                      setCustomEnd(e.target.value)
                      setActivePreset('custom')
                    }}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>
              <button
                onClick={handleCustomApply}
                disabled={!customStart && !customEnd}
                className="w-full px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Apply Custom Range
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
