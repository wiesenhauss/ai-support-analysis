/**
 * Custom Per-Ticket Analysis Configuration Dialog
 * Allows users to define AI analyses that run on each ticket
 */

import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import api, { CustomTicketAnalysis } from '@/api/client'
import LoadingSpinner from './LoadingSpinner'
import Alert from './Alert'
import { X, Plus, Pencil, Trash2, Save, CheckSquare, Square } from 'lucide-react'

interface CustomTicketAnalysisDialogProps {
  isOpen: boolean
  onClose: () => void
  availableColumns?: string[]
}

// Default columns to show if none provided
const DEFAULT_COLUMNS = [
  'Interaction Message Body',
  'Ticket Message Body',
  'CSAT Rating',
  'CSAT Reason',
  'CSAT Comment',
  'Tags',
  'Created Date',
  'SENTIMENT_ANALYSIS',
  'DETAIL_SUMMARY',
  'CUSTOMER_GOAL',
  'WHAT_HAPPENED',
  'MAIN_TOPIC',
  'PRODUCT_AREA',
]

// Example analyses for quick setup
const EXAMPLE_ANALYSES: CustomTicketAnalysis[] = [
  {
    name: 'IS_REFUND_REQUEST',
    prompt: 'Determine if this ticket is a refund or cancellation request. Look for keywords like "refund", "cancel", "money back", or explicit requests to cancel a subscription or get a refund.',
    result_type: 'boolean',
    description: 'Identifies refund/cancellation requests',
    columns: ['Interaction Message Body', 'CSAT Comment'],
  },
  {
    name: 'URGENCY_LEVEL',
    prompt: 'Rate the urgency of this support ticket. Consider the customer\'s language, the nature of the issue, and any time-sensitive factors. Respond with exactly one of: low, medium, high, critical',
    result_type: 'string',
    description: 'Classifies ticket urgency',
    columns: ['Interaction Message Body', 'CSAT Rating'],
  },
  {
    name: 'NEEDS_ESCALATION',
    prompt: 'Determine if this ticket should be escalated to a senior support agent or specialist. Consider: complexity of issue, customer frustration, technical depth required, or specific product expertise needed.',
    result_type: 'boolean',
    description: 'Identifies tickets needing escalation',
    columns: ['Interaction Message Body', 'SENTIMENT_ANALYSIS', 'MAIN_TOPIC'],
  },
]

export default function CustomTicketAnalysisDialog({
  isOpen,
  onClose,
  availableColumns = DEFAULT_COLUMNS,
}: CustomTicketAnalysisDialogProps) {
  const [analyses, setAnalyses] = useState<CustomTicketAnalysis[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Edit dialog state
  const [editingAnalysis, setEditingAnalysis] = useState<CustomTicketAnalysis | null>(null)
  const [isNewAnalysis, setIsNewAnalysis] = useState(false)

  // Load analyses on mount
  useEffect(() => {
    if (isOpen) {
      loadAnalyses()
    }
  }, [isOpen])

  const loadAnalyses = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.settings.getCustomTicketAnalyses()
      setAnalyses(response.analyses)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analyses')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveAll = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await api.settings.saveCustomTicketAnalyses(analyses)
      setSuccess(`Saved ${analyses.length} custom analyses`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save analyses')
    } finally {
      setSaving(false)
    }
  }

  const handleAddNew = () => {
    setEditingAnalysis({
      name: '',
      prompt: '',
      result_type: 'boolean',
      description: '',
      columns: [],
    })
    setIsNewAnalysis(true)
  }

  const handleEdit = (analysis: CustomTicketAnalysis) => {
    setEditingAnalysis({ ...analysis })
    setIsNewAnalysis(false)
  }

  const handleDelete = (name: string) => {
    if (!confirm(`Delete analysis "${name}"? This cannot be undone.`)) return
    setAnalyses(prev => prev.filter(a => a.name !== name))
    setSuccess(`Deleted analysis "${name}". Click Save to confirm.`)
  }

  const handleSaveEdit = (updated: CustomTicketAnalysis) => {
    if (isNewAnalysis) {
      // Check for duplicate names
      if (analyses.some(a => a.name === updated.name)) {
        setError(`Analysis with name "${updated.name}" already exists`)
        return
      }
      setAnalyses(prev => [...prev, updated])
    } else {
      setAnalyses(prev => prev.map(a => a.name === editingAnalysis?.name ? updated : a))
    }
    setEditingAnalysis(null)
    setSuccess('Changes saved locally. Click Save to apply.')
  }

  const handleAddExample = (example: CustomTicketAnalysis) => {
    if (analyses.some(a => a.name === example.name)) {
      setError(`Analysis "${example.name}" already exists`)
      return
    }
    setAnalyses(prev => [...prev, example])
    setSuccess(`Added example "${example.name}". Click Save to apply.`)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Custom Per-Ticket Analyses</h2>
            <p className="text-sm text-gray-500 mt-1">
              Define AI analyses that run on each ticket during processing
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <Alert variant="error" className="mb-4">
              {error}
            </Alert>
          )}

          {success && (
            <Alert variant="success" className="mb-4">
              {success}
            </Alert>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <>
              {/* Analyses List */}
              {analyses.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-lg">
                  <p className="text-gray-500 mb-4">No custom analyses configured yet.</p>
                  <button onClick={handleAddNew} className="btn btn-primary">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Your First Analysis
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {analyses.map((analysis) => (
                    <div
                      key={analysis.name}
                      className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-primary-600">
                            CUSTOM_{analysis.name}
                          </span>
                          <span className={cn(
                            'text-xs px-2 py-0.5 rounded',
                            analysis.result_type === 'boolean'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-purple-100 text-purple-700'
                          )}>
                            {analysis.result_type}
                          </span>
                        </div>
                        {analysis.description && (
                          <p className="text-sm text-gray-500 mt-1">{analysis.description}</p>
                        )}
                        <p className="text-xs text-gray-400 mt-2">
                          {analysis.columns.length} columns selected
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(analysis)}
                          className="p-2 hover:bg-gray-200 rounded-lg text-gray-600"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(analysis.name)}
                          className="p-2 hover:bg-danger-50 rounded-lg text-danger-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Add Button */}
              {analyses.length > 0 && (
                <button onClick={handleAddNew} className="btn btn-secondary mt-4 w-full">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Analysis
                </button>
              )}

              {/* Example Analyses */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Quick Add Examples</h3>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_ANALYSES.map((example) => (
                    <button
                      key={example.name}
                      onClick={() => handleAddExample(example)}
                      disabled={analyses.some(a => a.name === example.name)}
                      className={cn(
                        'text-xs px-3 py-1.5 rounded-lg border transition-colors',
                        analyses.some(a => a.name === example.name)
                          ? 'border-gray-200 text-gray-400 cursor-not-allowed'
                          : 'border-primary-200 text-primary-700 hover:bg-primary-50'
                      )}
                    >
                      + {example.name}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <p className="text-sm text-gray-500">
            {analyses.length} {analyses.length === 1 ? 'analysis' : 'analyses'} configured
          </p>
          <div className="flex gap-3">
            <button onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button
              onClick={handleSaveAll}
              disabled={saving}
              className="btn btn-primary"
            >
              {saving ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save All
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Edit Sub-Dialog */}
      {editingAnalysis && (
        <EditAnalysisDialog
          analysis={editingAnalysis}
          isNew={isNewAnalysis}
          availableColumns={availableColumns}
          onSave={handleSaveEdit}
          onCancel={() => setEditingAnalysis(null)}
        />
      )}
    </div>
  )
}

// ============== Edit Analysis Sub-Dialog ==============

interface EditAnalysisDialogProps {
  analysis: CustomTicketAnalysis
  isNew: boolean
  availableColumns: string[]
  onSave: (analysis: CustomTicketAnalysis) => void
  onCancel: () => void
}

function EditAnalysisDialog({
  analysis,
  isNew,
  availableColumns,
  onSave,
  onCancel,
}: EditAnalysisDialogProps) {
  const [form, setForm] = useState<CustomTicketAnalysis>(analysis)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validateAndSave = () => {
    const newErrors: Record<string, string> = {}

    if (!form.name.trim()) {
      newErrors.name = 'Name is required'
    } else if (!/^[A-Z0-9_]+$/i.test(form.name)) {
      newErrors.name = 'Name must contain only letters, numbers, and underscores'
    }

    if (!form.prompt.trim()) {
      newErrors.prompt = 'Prompt is required'
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    onSave({
      ...form,
      name: form.name.toUpperCase(),
    })
  }

  const toggleColumn = (column: string) => {
    setForm(prev => ({
      ...prev,
      columns: prev.columns.includes(column)
        ? prev.columns.filter(c => c !== column)
        : [...prev.columns, column],
    }))
  }

  const selectAllColumns = () => {
    setForm(prev => ({ ...prev, columns: [...availableColumns] }))
  }

  const clearAllColumns = () => {
    setForm(prev => ({ ...prev, columns: [] }))
  }

  const selectCommonColumns = () => {
    const common = ['Interaction Message Body', 'CSAT Rating', 'CSAT Comment', 'SENTIMENT_ANALYSIS']
    setForm(prev => ({ ...prev, columns: common.filter(c => availableColumns.includes(c)) }))
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {isNew ? 'Add New Analysis' : 'Edit Analysis'}
          </h2>
          <button onClick={onCancel} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Name */}
          <div>
            <label className="label">
              Column Name <span className="text-danger-500">*</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-gray-400 font-mono">CUSTOM_</span>
              <input
                type="text"
                className={cn('input flex-1 uppercase', errors.name && 'border-danger-500')}
                placeholder="IS_REFUND_REQUEST"
                value={form.name}
                onChange={(e) => {
                  setForm(prev => ({ ...prev, name: e.target.value.toUpperCase() }))
                  setErrors(prev => ({ ...prev, name: '' }))
                }}
              />
            </div>
            {errors.name && (
              <p className="text-sm text-danger-600 mt-1">{errors.name}</p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              Use letters, numbers, and underscores only
            </p>
          </div>

          {/* Result Type */}
          <div>
            <label className="label">Result Type</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="result_type"
                  checked={form.result_type === 'boolean'}
                  onChange={() => setForm(prev => ({ ...prev, result_type: 'boolean' }))}
                  className="w-4 h-4 text-primary-600"
                />
                <span className="text-sm">Boolean (True/False)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="result_type"
                  checked={form.result_type === 'string'}
                  onChange={() => setForm(prev => ({ ...prev, result_type: 'string' }))}
                  className="w-4 h-4 text-primary-600"
                />
                <span className="text-sm">String (Text)</span>
              </label>
            </div>
          </div>

          {/* Prompt */}
          <div>
            <label className="label">
              AI Prompt <span className="text-danger-500">*</span>
            </label>
            <textarea
              className={cn('input min-h-[120px]', errors.prompt && 'border-danger-500')}
              placeholder="What should the AI determine for each ticket?"
              value={form.prompt}
              onChange={(e) => {
                setForm(prev => ({ ...prev, prompt: e.target.value }))
                setErrors(prev => ({ ...prev, prompt: '' }))
              }}
            />
            {errors.prompt && (
              <p className="text-sm text-danger-600 mt-1">{errors.prompt}</p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              {form.result_type === 'boolean'
                ? 'Write a prompt that can be answered with True or False'
                : 'Write a prompt that expects a text response'}
            </p>
          </div>

          {/* Column Selection */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label mb-0">Columns to Include</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={selectCommonColumns}
                  className="text-xs text-primary-600 hover:underline"
                >
                  Select Common
                </button>
                <button
                  type="button"
                  onClick={selectAllColumns}
                  className="text-xs text-primary-600 hover:underline"
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={clearAllColumns}
                  className="text-xs text-gray-500 hover:underline"
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="max-h-[200px] overflow-y-auto border border-gray-200 rounded-lg p-3">
              <div className="grid grid-cols-2 gap-2">
                {availableColumns.map((column) => (
                  <label
                    key={column}
                    className="flex items-center gap-2 cursor-pointer p-1.5 hover:bg-gray-50 rounded"
                  >
                    <button
                      type="button"
                      onClick={() => toggleColumn(column)}
                      className="flex items-center"
                    >
                      {form.columns.includes(column) ? (
                        <CheckSquare className="w-4 h-4 text-primary-600" />
                      ) : (
                        <Square className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                    <span className="text-sm text-gray-700 truncate">{column}</span>
                  </label>
                ))}
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {form.columns.length} columns selected. These will be included in the AI context.
            </p>
          </div>

          {/* Description */}
          <div>
            <label className="label">Description (Optional)</label>
            <input
              type="text"
              className="input"
              placeholder="Brief description of what this analysis does"
              value={form.description}
              onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <button onClick={onCancel} className="btn btn-secondary">
            Cancel
          </button>
          <button onClick={validateAndSave} className="btn btn-primary">
            <Save className="w-4 h-4 mr-2" />
            {isNew ? 'Add Analysis' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
