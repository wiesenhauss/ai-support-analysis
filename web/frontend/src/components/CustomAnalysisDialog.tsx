import { useState, useEffect } from 'react'
import { X, Save, Trash2, Plus, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'
import api, { CustomPrompt } from '@/api/client'
import Alert from './Alert'

interface CustomAnalysisDialogProps {
  isOpen: boolean
  onClose: () => void
  availableColumns: string[]
  onPromptSelect?: (prompt: string, columns: string[]) => void
}

export default function CustomAnalysisDialog({
  isOpen,
  onClose,
  availableColumns,
  onPromptSelect,
}: CustomAnalysisDialogProps) {
  const [prompts, setPrompts] = useState<Record<string, CustomPrompt>>({})
  const [selectedPromptName, setSelectedPromptName] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Edit form state
  const [editName, setEditName] = useState('')
  const [editPrompt, setEditPrompt] = useState('')
  const [editColumns, setEditColumns] = useState<string[]>([])

  // Load prompts on open
  useEffect(() => {
    if (isOpen) {
      loadPrompts()
    }
  }, [isOpen])

  const loadPrompts = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.settings.getCustomPrompts()
      setPrompts(result.prompts || {})
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompts')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectPrompt = (name: string) => {
    setSelectedPromptName(name)
    const prompt = prompts[name]
    if (prompt) {
      setEditName(name)
      setEditPrompt(prompt.prompt)
      setEditColumns(prompt.columns || [])
    }
    setEditMode(false)
  }

  const handleNewPrompt = () => {
    setSelectedPromptName(null)
    setEditName('')
    setEditPrompt('')
    setEditColumns([])
    setEditMode(true)
  }

  const handleEditPrompt = () => {
    if (!selectedPromptName) return
    const prompt = prompts[selectedPromptName]
    if (prompt) {
      setEditName(selectedPromptName)
      setEditPrompt(prompt.prompt)
      setEditColumns(prompt.columns || [])
      setEditMode(true)
    }
  }

  const handleSavePrompt = async () => {
    if (!editName.trim() || !editPrompt.trim()) {
      setError('Name and prompt are required')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const promptData: CustomPrompt = {
        name: editName.trim(),
        prompt: editPrompt.trim(),
        columns: editColumns,
        created: new Date().toISOString(),
      }
      await api.settings.saveCustomPrompt(editName.trim(), promptData)
      setSuccess('Prompt saved successfully')
      await loadPrompts()
      setSelectedPromptName(editName.trim())
      setEditMode(false)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save prompt')
    } finally {
      setLoading(false)
    }
  }

  const handleDeletePrompt = async (name: string) => {
    if (!confirm(`Delete prompt "${name}"?`)) return

    setLoading(true)
    setError(null)
    try {
      await api.settings.deleteCustomPrompt(name)
      setSuccess('Prompt deleted')
      await loadPrompts()
      if (selectedPromptName === name) {
        setSelectedPromptName(null)
        setEditName('')
        setEditPrompt('')
        setEditColumns([])
      }
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete prompt')
    } finally {
      setLoading(false)
    }
  }

  const handleUsePrompt = () => {
    if (onPromptSelect && editPrompt) {
      onPromptSelect(editPrompt, editColumns)
      onClose()
    }
  }

  const toggleColumn = (column: string) => {
    setEditColumns((prev) =>
      prev.includes(column)
        ? prev.filter((c) => c !== column)
        : [...prev, column]
    )
  }

  if (!isOpen) return null

  const promptList = Object.keys(prompts)

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/50" onClick={onClose} />

        <div className="relative bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              Custom Analysis Prompts
            </h2>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex h-[60vh]">
            {/* Sidebar - Prompt List */}
            <div className="w-64 border-r bg-gray-50 p-4 overflow-y-auto">
              <button
                onClick={handleNewPrompt}
                className="w-full mb-4 flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                <Plus className="w-4 h-4" />
                New Prompt
              </button>

              {loading && promptList.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">Loading...</p>
              ) : promptList.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">
                  No saved prompts
                </p>
              ) : (
                <div className="space-y-2">
                  {promptList.map((name) => (
                    <div
                      key={name}
                      className={cn(
                        'flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors',
                        selectedPromptName === name
                          ? 'bg-primary-100 border border-primary-300'
                          : 'hover:bg-gray-100'
                      )}
                      onClick={() => handleSelectPrompt(name)}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <span className="text-sm truncate">{name}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeletePrompt(name)
                        }}
                        className="p-1 hover:bg-red-100 rounded text-gray-400 hover:text-red-600"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Main Content */}
            <div className="flex-1 p-6 overflow-y-auto">
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

              {!selectedPromptName && !editMode ? (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>Select a prompt or create a new one</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Prompt Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Prompt Name
                    </label>
                    {editMode ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="input"
                        placeholder="e.g., Refund Analysis"
                      />
                    ) : (
                      <p className="text-gray-900 font-medium">{editName}</p>
                    )}
                  </div>

                  {/* Prompt Text */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Analysis Prompt
                    </label>
                    {editMode ? (
                      <textarea
                        value={editPrompt}
                        onChange={(e) => setEditPrompt(e.target.value)}
                        className="input min-h-[150px] font-mono text-sm"
                        placeholder="Enter your custom analysis prompt...&#10;&#10;Example: Analyze the support tickets and identify common themes around refund requests. Summarize the main reasons customers ask for refunds and suggest improvements."
                      />
                    ) : (
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded-lg border">
                        {editPrompt}
                      </pre>
                    )}
                  </div>

                  {/* Column Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Columns to Include ({editColumns.length} selected)
                    </label>
                    {editMode ? (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-40 overflow-y-auto p-2 border rounded-lg bg-gray-50">
                        {availableColumns.length === 0 ? (
                          <p className="text-sm text-gray-500 col-span-full">
                            Upload a CSV first to see available columns
                          </p>
                        ) : (
                          availableColumns.map((column) => (
                            <label
                              key={column}
                              className={cn(
                                'flex items-center gap-2 p-2 rounded cursor-pointer text-sm transition-colors',
                                editColumns.includes(column)
                                  ? 'bg-primary-100 text-primary-700'
                                  : 'hover:bg-gray-100'
                              )}
                            >
                              <input
                                type="checkbox"
                                checked={editColumns.includes(column)}
                                onChange={() => toggleColumn(column)}
                                className="rounded"
                              />
                              <span className="truncate">{column}</span>
                            </label>
                          ))
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {editColumns.length === 0 ? (
                          <span className="text-sm text-gray-500">All columns</span>
                        ) : (
                          editColumns.map((col) => (
                            <span
                              key={col}
                              className="px-2 py-1 bg-gray-100 rounded text-sm"
                            >
                              {col}
                            </span>
                          ))
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 pt-4 border-t">
                    {editMode ? (
                      <>
                        <button
                          onClick={handleSavePrompt}
                          disabled={loading}
                          className="btn btn-primary"
                        >
                          <Save className="w-4 h-4 mr-2" />
                          Save Prompt
                        </button>
                        <button
                          onClick={() => {
                            setEditMode(false)
                            if (selectedPromptName) {
                              handleSelectPrompt(selectedPromptName)
                            }
                          }}
                          className="btn btn-secondary"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button onClick={handleEditPrompt} className="btn btn-secondary">
                          Edit
                        </button>
                        {onPromptSelect && (
                          <button onClick={handleUsePrompt} className="btn btn-primary">
                            Use This Prompt
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
