import { useState, useEffect, useCallback } from 'react'
import { Card, CardHeader } from '@/components/Card'
import Alert from '@/components/Alert'
import LoadingSpinner, { PageLoader } from '@/components/LoadingSpinner'
import { cn, formatNumber } from '@/lib/utils'
import api from '@/api/client'
import { Database, Trash2, Upload, RefreshCw, Key, Eye, EyeOff, CheckCircle, XCircle } from 'lucide-react'

interface DatabaseStats {
  total_tickets: number
  total_batches: number
  date_range_start: string | null
  date_range_end: string | null
  sentiment_distribution: Record<string, number>
  resolution_rate: number
  db_path: string
  db_size_mb: number
}

interface Batch {
  id: number
  import_date: string
  source_file: string
  period_start: string | null
  period_end: string | null
  total_tickets: number
  new_tickets: number
  notes: string | null
}

interface ApiKeyStatus {
  configured: boolean
  masked_key: string | null
  source: 'settings_file' | 'environment' | 'none'
}

export default function Settings() {
  const [stats, setStats] = useState<DatabaseStats | null>(null)
  const [batches, setBatches] = useState<Batch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingBatch, setDeletingBatch] = useState<number | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<string | null>(null)

  // API Key state
  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyStatus | null>(null)
  const [newApiKey, setNewApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [savingApiKey, setSavingApiKey] = useState(false)
  const [validatingApiKey, setValidatingApiKey] = useState(false)
  const [apiKeyValidation, setApiKeyValidation] = useState<{ valid: boolean; message: string } | null>(null)
  const [apiKeySuccess, setApiKeySuccess] = useState<string | null>(null)

  const fetchApiKeyStatus = useCallback(async () => {
    try {
      const status = await api.settings.getApiKeyStatus() as ApiKeyStatus
      setApiKeyStatus(status)
    } catch (err) {
      console.error('Failed to fetch API key status:', err)
    }
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsRes, batchesRes] = await Promise.all([
        api.data.getStats() as Promise<DatabaseStats>,
        api.data.getBatches() as Promise<{ batches: Batch[] }>,
      ])
      setStats(statsRes)
      setBatches(batchesRes.batches)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    fetchApiKeyStatus()
  }, [fetchData, fetchApiKeyStatus])

  const handleValidateApiKey = async () => {
    if (!newApiKey.trim()) return

    setValidatingApiKey(true)
    setApiKeyValidation(null)
    try {
      const result = await api.settings.validateApiKey(newApiKey) as { valid: boolean; message: string }
      setApiKeyValidation(result)
    } catch (err) {
      setApiKeyValidation({
        valid: false,
        message: err instanceof Error ? err.message : 'Validation failed'
      })
    } finally {
      setValidatingApiKey(false)
    }
  }

  const handleSaveApiKey = async () => {
    if (!newApiKey.trim()) return

    setSavingApiKey(true)
    setError(null)
    setApiKeySuccess(null)
    try {
      await api.settings.setApiKey(newApiKey)
      setApiKeySuccess('API key saved successfully')
      setNewApiKey('')
      setApiKeyValidation(null)
      await fetchApiKeyStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save API key')
    } finally {
      setSavingApiKey(false)
    }
  }

  const handleDeleteApiKey = async () => {
    if (!confirm('Are you sure you want to remove the stored API key?')) return

    try {
      const result = await api.settings.deleteApiKey() as { environment_key_exists: boolean }
      if (result.environment_key_exists) {
        setApiKeySuccess('API key removed from settings. Note: An environment variable is still configured.')
      } else {
        setApiKeySuccess('API key removed')
      }
      await fetchApiKeyStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove API key')
    }
  }

  const handleDeleteBatch = async (batchId: number) => {
    if (!confirm('Are you sure you want to delete this batch? This cannot be undone.')) {
      return
    }

    setDeletingBatch(batchId)
    try {
      await api.data.deleteBatch(batchId)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete batch')
    } finally {
      setDeletingBatch(null)
    }
  }

  const handleImport = async () => {
    if (!importFile) return

    setImporting(true)
    setImportResult(null)
    try {
      const result = await api.data.importCSV(importFile) as {
        batch_id: number
        total_rows: number
        imported: number
        duplicates: number
      }
      setImportResult(
        `Successfully imported ${result.imported} tickets (${result.duplicates} duplicates skipped)`
      )
      setImportFile(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import file')
    } finally {
      setImporting(false)
    }
  }

  if (loading) {
    return <PageLoader />
  }

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">
          Manage your database and configuration
        </p>
      </div>

      {error && (
        <Alert variant="error">{error}</Alert>
      )}

      {importResult && (
        <Alert variant="success">{importResult}</Alert>
      )}

      {apiKeySuccess && (
        <Alert variant="success">{apiKeySuccess}</Alert>
      )}

      {/* OpenAI API Key Configuration */}
      <Card>
        <CardHeader
          title="OpenAI API Key"
          description="Configure your OpenAI API key for AI-powered analysis"
        />
        
        {/* Current Status */}
        {apiKeyStatus && (
          <div className="mb-6">
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
              <Key className={cn(
                'w-5 h-5',
                apiKeyStatus.configured ? 'text-success-500' : 'text-gray-400'
              )} />
              <div className="flex-1">
                {apiKeyStatus.configured ? (
                  <>
                    <p className="font-medium text-gray-900">API Key Configured</p>
                    <p className="text-sm text-gray-500">
                      {apiKeyStatus.masked_key}
                      {apiKeyStatus.source === 'environment' && (
                        <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                          from environment
                        </span>
                      )}
                      {apiKeyStatus.source === 'settings_file' && (
                        <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                          from settings
                        </span>
                      )}
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-medium text-gray-900">No API Key Configured</p>
                    <p className="text-sm text-gray-500">
                      Add your OpenAI API key to enable analysis features
                    </p>
                  </>
                )}
              </div>
              {apiKeyStatus.configured && apiKeyStatus.source === 'settings_file' && (
                <button
                  onClick={handleDeleteApiKey}
                  className="btn btn-secondary text-danger-600 hover:bg-danger-50"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Add/Update API Key */}
        <div className="space-y-4">
          <div>
            <label className="label">
              {apiKeyStatus?.configured ? 'Update API Key' : 'Enter API Key'}
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                className="input pr-20"
                placeholder="sk-proj-..."
                value={newApiKey}
                onChange={(e) => {
                  setNewApiKey(e.target.value)
                  setApiKeyValidation(null)
                }}
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-400 hover:text-gray-600"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Get your API key from{' '}
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                platform.openai.com/api-keys
              </a>
            </p>
          </div>

          {/* Validation Result */}
          {apiKeyValidation && (
            <div className={cn(
              'flex items-center gap-2 p-3 rounded-lg',
              apiKeyValidation.valid ? 'bg-success-50 text-success-700' : 'bg-danger-50 text-danger-700'
            )}>
              {apiKeyValidation.valid ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              <span className="text-sm">{apiKeyValidation.message}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleValidateApiKey}
              disabled={!newApiKey.trim() || validatingApiKey}
              className="btn btn-secondary"
            >
              {validatingApiKey ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Validating...
                </>
              ) : (
                'Validate Key'
              )}
            </button>
            <button
              onClick={handleSaveApiKey}
              disabled={!newApiKey.trim() || savingApiKey}
              className="btn btn-primary"
            >
              {savingApiKey ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Saving...
                </>
              ) : (
                'Save API Key'
              )}
            </button>
          </div>
        </div>
      </Card>

      {/* Database Stats */}
      <Card>
        <CardHeader
          title="Database Statistics"
          description={stats?.db_path || 'Default location'}
          action={
            <button onClick={fetchData} className="btn btn-secondary">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </button>
          }
        />
        
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <Database className="w-5 h-5 text-gray-400 mb-2" />
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(stats.total_tickets)}
              </p>
              <p className="text-sm text-gray-500">Total Tickets</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(stats.total_batches)}
              </p>
              <p className="text-sm text-gray-500">Import Batches</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">
                {stats.db_size_mb.toFixed(2)} MB
              </p>
              <p className="text-sm text-gray-500">Database Size</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">
                {(stats.resolution_rate * 100).toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500">Resolution Rate</p>
            </div>
          </div>
        )}

        {stats?.date_range_start && (
          <p className="text-sm text-gray-500 mt-4">
            Data range: {new Date(stats.date_range_start).toLocaleDateString()} - {' '}
            {stats.date_range_end ? new Date(stats.date_range_end).toLocaleDateString() : 'Present'}
          </p>
        )}
      </Card>

      {/* Import CSV */}
      <Card>
        <CardHeader
          title="Import Analyzed CSV"
          description="Import previously analyzed CSV files into the database"
        />
        
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-medium
                  file:bg-primary-50 file:text-primary-700
                  hover:file:bg-primary-100"
                disabled={importing}
              />
            </div>
            <button
              onClick={handleImport}
              disabled={!importFile || importing}
              className="btn btn-primary"
            >
              {importing ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Import
                </>
              )}
            </button>
          </div>
          <p className="text-sm text-gray-500">
            Import CSV files that have been analyzed with the AI Support Analyzer.
            Duplicate tickets will be automatically skipped.
          </p>
        </div>
      </Card>

      {/* Import Batches */}
      <Card>
        <CardHeader
          title="Import History"
          description="View and manage imported data batches"
        />
        
        {batches.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No import batches yet. Import a CSV file to get started.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                    File
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                    Date
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                    Period
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                    Tickets
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.id} className="border-b border-gray-100">
                    <td className="py-3 px-4">
                      <p className="font-medium text-gray-900">{batch.source_file}</p>
                      {batch.notes && (
                        <p className="text-sm text-gray-500">{batch.notes}</p>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500">
                      {new Date(batch.import_date).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500">
                      {batch.period_start && batch.period_end
                        ? `${new Date(batch.period_start).toLocaleDateString()} - ${new Date(batch.period_end).toLocaleDateString()}`
                        : '-'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm font-medium text-gray-900">
                        {formatNumber(batch.new_tickets)}
                      </span>
                      <span className="text-sm text-gray-500">
                        {' '}/ {formatNumber(batch.total_tickets)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDeleteBatch(batch.id)}
                        disabled={deletingBatch === batch.id}
                        className={cn(
                          'p-2 rounded-lg hover:bg-danger-50 text-danger-600 transition-colors',
                          deletingBatch === batch.id && 'opacity-50'
                        )}
                      >
                        {deletingBatch === batch.id ? (
                          <LoadingSpinner size="sm" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* About */}
      <Card>
        <CardHeader
          title="About"
          description="AI Support Analyzer Web UI"
        />
        <div className="space-y-2 text-sm text-gray-500">
          <p>Version: 1.0.0</p>
          <p>Built with React, TypeScript, and FastAPI</p>
          <p>Powered by OpenAI GPT-4</p>
        </div>
      </Card>
    </div>
  )
}
