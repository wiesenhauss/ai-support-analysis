import { useState, useEffect, useMemo } from 'react'
import { Card, CardHeader } from '@/components/Card'
import { cn } from '@/lib/utils'
import { CheckCircle, AlertCircle, ArrowRight, Columns } from 'lucide-react'
import type { ColumnMatchInfo } from '@/api/client'

interface ColumnMappingCardProps {
  validationResult: {
    all_required_matched: boolean
    columns: ColumnMatchInfo[]
    available_columns: string[]
  }
  onMappingChange: (mapping: Record<string, string>) => void
  disabled?: boolean
}

export default function ColumnMappingCard({
  validationResult,
  onMappingChange,
  disabled = false,
}: ColumnMappingCardProps) {
  const { columns, available_columns } = validationResult

  const [userSelections, setUserSelections] = useState<Record<string, string>>({})

  useEffect(() => {
    const initial: Record<string, string> = {}
    for (const col of columns) {
      if (col.matched_column) {
        initial[col.expected_name] = col.matched_column
      }
    }
    setUserSelections(initial)
  }, [columns])

  const allRequiredMapped = useMemo(() => {
    return columns
      .filter((c) => c.required)
      .every((c) => userSelections[c.expected_name])
  }, [columns, userSelections])

  useEffect(() => {
    const mapping: Record<string, string> = {}
    for (const [expectedName, csvColumn] of Object.entries(userSelections)) {
      if (csvColumn) {
        mapping[expectedName] = csvColumn
      }
    }
    onMappingChange(mapping)
  }, [userSelections, onMappingChange])

  const usedColumns = useMemo(() => {
    return new Set(Object.values(userSelections).filter(Boolean))
  }, [userSelections])

  const handleSelect = (expectedName: string, csvColumn: string) => {
    setUserSelections((prev) => ({
      ...prev,
      [expectedName]: csvColumn,
    }))
  }

  const requiredColumns = columns.filter((c) => c.required)
  const optionalColumns = columns.filter((c) => !c.required)
  const unmatchedRequired = requiredColumns.filter((c) => !userSelections[c.expected_name])
  const unmatchedOptional = optionalColumns.filter((c) => !userSelections[c.expected_name])

  return (
    <Card>
      <CardHeader
        title="Column Mapping"
        description="Map your CSV columns to the expected fields for analysis"
        action={
          allRequiredMapped ? (
            <div className="flex items-center gap-1.5 text-success-600 text-sm font-medium">
              <CheckCircle className="w-4 h-4" />
              Ready
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-warning-600 text-sm font-medium">
              <AlertCircle className="w-4 h-4" />
              {unmatchedRequired.length} required {unmatchedRequired.length === 1 ? 'field' : 'fields'} unmapped
            </div>
          )
        }
      />

      <div className="space-y-1">
        {/* Table header */}
        <div className="grid grid-cols-[1fr_32px_1fr] gap-2 px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
          <span>Expected Column</span>
          <span />
          <span>Your CSV Column</span>
        </div>

        {/* Required columns */}
        {requiredColumns.length > 0 && (
          <div className="space-y-1">
            {requiredColumns.map((col) => (
              <MappingRow
                key={col.expected_name}
                col={col}
                selectedValue={userSelections[col.expected_name] || ''}
                availableColumns={available_columns}
                usedColumns={usedColumns}
                onSelect={handleSelect}
                disabled={disabled}
              />
            ))}
          </div>
        )}

        {/* Divider between required and optional */}
        {requiredColumns.length > 0 && optionalColumns.length > 0 && (
          <div className="flex items-center gap-3 py-2 px-3">
            <div className="flex-1 border-t border-gray-200" />
            <span className="text-xs text-gray-400">Optional</span>
            <div className="flex-1 border-t border-gray-200" />
          </div>
        )}

        {/* Optional columns */}
        {optionalColumns.map((col) => (
          <MappingRow
            key={col.expected_name}
            col={col}
            selectedValue={userSelections[col.expected_name] || ''}
            availableColumns={available_columns}
            usedColumns={usedColumns}
            onSelect={handleSelect}
            disabled={disabled}
          />
        ))}
      </div>

      {/* Info about unmapped optional columns */}
      {unmatchedOptional.length > 0 && allRequiredMapped && (
        <p className="text-xs text-gray-500 mt-4 px-3">
          Unmapped optional columns will be created with empty values. Analysis will continue with available data.
        </p>
      )}
    </Card>
  )
}

function MappingRow({
  col,
  selectedValue,
  availableColumns,
  usedColumns,
  onSelect,
  disabled,
}: {
  col: ColumnMatchInfo
  selectedValue: string
  availableColumns: string[]
  usedColumns: Set<string>
  onSelect: (expectedName: string, csvColumn: string) => void
  disabled: boolean
}) {
  const isMatched = !!selectedValue
  const isAutoMatched = !!col.matched_column && selectedValue === col.matched_column

  return (
    <div
      className={cn(
        'grid grid-cols-[1fr_32px_1fr] gap-2 items-center px-3 py-2.5 rounded-lg transition-colors',
        isMatched ? 'bg-success-50/50' : col.required ? 'bg-warning-50/50' : 'bg-gray-50',
      )}
    >
      {/* Expected column info */}
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Columns className={cn('w-4 h-4 flex-shrink-0', isMatched ? 'text-success-500' : col.required ? 'text-warning-500' : 'text-gray-400')} />
          <span className="font-medium text-sm text-gray-900 truncate">
            {col.expected_name}
          </span>
          {col.required && (
            <span className="text-[10px] font-semibold uppercase tracking-wider text-warning-600 bg-warning-100 px-1.5 py-0.5 rounded flex-shrink-0">
              Required
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-0.5 ml-6 truncate">{col.description}</p>
      </div>

      {/* Arrow */}
      <div className="flex justify-center">
        <ArrowRight className={cn('w-4 h-4', isMatched ? 'text-success-400' : 'text-gray-300')} />
      </div>

      {/* Dropdown */}
      <div>
        <select
          value={selectedValue}
          onChange={(e) => onSelect(col.expected_name, e.target.value)}
          disabled={disabled}
          className={cn(
            'w-full text-sm rounded-md border px-3 py-2 bg-white transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            isMatched ? 'border-success-300 text-gray-900' : 'border-gray-300 text-gray-500',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        >
          <option value="">
            {col.required ? '-- Select a column --' : '-- Not mapped (optional) --'}
          </option>
          {availableColumns.map((csvCol) => {
            const isUsedElsewhere = usedColumns.has(csvCol) && csvCol !== selectedValue
            return (
              <option key={csvCol} value={csvCol} disabled={isUsedElsewhere}>
                {csvCol}{isUsedElsewhere ? ' (already mapped)' : ''}
                {isAutoMatched && csvCol === col.matched_column ? ' (auto-detected)' : ''}
              </option>
            )
          })}
        </select>
        {isAutoMatched && (
          <p className="text-[11px] text-success-600 mt-0.5">Auto-detected</p>
        )}
      </div>
    </div>
  )
}
