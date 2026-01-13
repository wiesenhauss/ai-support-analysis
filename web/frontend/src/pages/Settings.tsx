import { useState, useEffect, useCallback } from 'react'
import { Card, CardHeader } from '@/components/Card'
import Alert from '@/components/Alert'
import LoadingSpinner, { PageLoader } from '@/components/LoadingSpinner'
import { cn, formatNumber } from '@/lib/utils'
import api from '@/api/client'
import { Database, Trash2, Upload, RefreshCw } from 'lucide-react'

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

export default function Settings() {
  const [stats, setStats] = useState<DatabaseStats | null>(null)
  const [batches, setBatches] = useState<Batch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingBatch, setDeletingBatch] = useState<number | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<string | null>(null)

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
  }, [fetchData])

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
