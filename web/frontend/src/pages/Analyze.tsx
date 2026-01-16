import { useState, useCallback, useRef, useEffect } from 'react'
import { Card, CardHeader } from '@/components/Card'
import Alert from '@/components/Alert'
import LoadingSpinner from '@/components/LoadingSpinner'
import CustomAnalysisDialog from '@/components/CustomAnalysisDialog'
import { cn } from '@/lib/utils'
import api, { OutputFile } from '@/api/client'
import { Upload, FileText, X, Play, Square, CheckCircle, AlertCircle, Download, Settings } from 'lucide-react'

interface AnalysisOptions {
  main_analysis: boolean
  data_cleanup: boolean
  predict_csat: boolean
  topic_aggregator: boolean
  csat_trends: boolean
  product_feedback: boolean
  goals_trends: boolean
  custom_analysis: boolean
  custom_ticket_analysis: boolean
  visualization: boolean
  limit: number | null
  threads: number
}

type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

interface JobState {
  job_id: string
  status: JobStatus
  progress: number
  current_step: string
  logs: string[]
  error_message?: string
}

export default function Analyze() {
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [options, setOptions] = useState<AnalysisOptions>({
    main_analysis: true,
    data_cleanup: true,
    predict_csat: true,
    topic_aggregator: true,
    csat_trends: true,
    product_feedback: true,
    goals_trends: true,
    custom_analysis: false,
    custom_ticket_analysis: false,
    visualization: false,
    limit: null,
    threads: 50,
  })
  const [outputFiles, setOutputFiles] = useState<OutputFile[]>([])
  const [job, setJob] = useState<JobState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showCustomAnalysisDialog, setShowCustomAnalysisDialog] = useState(false)
  const [customPrompt, setCustomPrompt] = useState<string>('')
  const [customColumns, setCustomColumns] = useState<string[]>([])
  const [csvColumns, setCsvColumns] = useState<string[]>([])
  const pollInterval = useRef<number | null>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollInterval.current) {
        clearInterval(pollInterval.current)
      }
    }
  }, [])

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [job?.logs])

  // Parse CSV columns when file changes
  useEffect(() => {
    if (!file) {
      setCsvColumns([])
      return
    }

    const parseColumns = async () => {
      try {
        const text = await file.slice(0, 4096).text() // Read first 4KB
        const firstLine = text.split('\n')[0]
        if (firstLine) {
          // Simple CSV header parsing
          const columns = firstLine.split(',').map(col => col.trim().replace(/^"|"$/g, ''))
          setCsvColumns(columns)
        }
      } catch (err) {
        console.error('Failed to parse CSV columns:', err)
      }
    }

    parseColumns()
  }, [file])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile)
        setError(null)
      } else {
        setError('Please upload a CSV file')
      }
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile)
        setError(null)
      } else {
        setError('Please upload a CSV file')
      }
    }
  }, [])

  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const status = await api.analysis.getStatus(jobId) as JobState
      setJob(status)

      if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
        if (pollInterval.current) {
          clearInterval(pollInterval.current)
          pollInterval.current = null
        }
      }
    } catch (err) {
      console.error('Error polling job status:', err)
    }
  }, [])

  const startAnalysis = async () => {
    if (!file) return

    setError(null)
    try {
      // Build options with custom prompt if configured
      const analysisOptions = {
        ...options,
        custom_prompt: customPrompt || undefined,
        custom_columns: customColumns.length > 0 ? customColumns.join(',') : undefined,
      }
      const response = await api.analysis.start(file, analysisOptions) as { job_id: string; status: JobStatus }
      
      setJob({
        job_id: response.job_id,
        status: response.status,
        progress: 0,
        current_step: 'Starting...',
        logs: ['Analysis job started'],
      })

      // Start polling
      pollInterval.current = window.setInterval(() => {
        pollJobStatus(response.job_id)
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis')
    }
  }

  const cancelAnalysis = async () => {
    if (!job) return

    try {
      await api.analysis.cancel(job.job_id)
      setJob((prev) => prev ? { ...prev, status: 'cancelled' } : null)
      if (pollInterval.current) {
        clearInterval(pollInterval.current)
        pollInterval.current = null
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel analysis')
    }
  }

  const optionItems = [
    { key: 'main_analysis', label: 'Main Analysis', description: 'AI-powered ticket analysis' },
    { key: 'data_cleanup', label: 'Data Cleanup', description: 'Pre-process and clean data' },
    { key: 'predict_csat', label: 'Predict CSAT', description: 'Predict satisfaction scores' },
    { key: 'topic_aggregator', label: 'Topic Aggregation', description: 'Categorize by topics' },
    { key: 'csat_trends', label: 'CSAT Trends', description: 'Analyze satisfaction trends' },
    { key: 'product_feedback', label: 'Product Feedback', description: 'Extract product insights' },
    { key: 'goals_trends', label: 'Goals Trends', description: 'Analyze customer goals' },
    { key: 'custom_analysis', label: 'Custom Aggregate Analysis', description: 'User-defined prompt analysis' },
    { key: 'custom_ticket_analysis', label: 'Custom Per-Ticket Analysis', description: 'AI per-ticket custom analysis' },
    { key: 'visualization', label: 'Generate Visualizations', description: 'Create charts and graphs' },
  ] as const

  // Fetch output files when job completes
  useEffect(() => {
    if (job?.status === 'completed') {
      api.analysis.getFiles(job.job_id).then((res) => {
        setOutputFiles(res.files)
      }).catch(console.error)
    }
  }, [job?.status, job?.job_id])

  const handleDownloadFile = async (filename: string) => {
    if (!job) return
    try {
      await api.analysis.downloadFile(job.job_id, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download file')
    }
  }

  const isRunning = job?.status === 'pending' || job?.status === 'running'

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analyze Data</h1>
        <p className="text-gray-500 mt-1">
          Upload a CSV file to run AI-powered analysis
        </p>
      </div>

      {error && (
        <Alert variant="error">
          {error}
        </Alert>
      )}

      {/* File Upload */}
      <Card>
        <CardHeader title="Upload CSV File" description="Drag and drop or click to select" />
        
        <div
          className={cn(
            'relative border-2 border-dashed rounded-lg p-8 transition-colors',
            dragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300',
            isRunning && 'opacity-50 pointer-events-none'
          )}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            disabled={isRunning}
          />
          
          <div className="text-center">
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="w-8 h-8 text-primary-600" />
                <div className="text-left">
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setFile(null)
                  }}
                  className="p-1 hover:bg-gray-100 rounded"
                  disabled={isRunning}
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600">
                  Drop your CSV file here, or click to browse
                </p>
                <p className="text-sm text-gray-400 mt-2">
                  Supports Zendesk export format
                </p>
              </>
            )}
          </div>
        </div>
      </Card>

      {/* Analysis Options */}
      <Card>
        <CardHeader title="Analysis Options" description="Select which analyses to run" />
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {optionItems.map(({ key, label, description }) => (
            <div
              key={key}
              className={cn(
                'flex items-start gap-3 p-3 rounded-lg border transition-colors',
                options[key] ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300',
                isRunning && 'opacity-50 pointer-events-none'
              )}
            >
              <label className="flex items-start gap-3 cursor-pointer flex-1">
                <input
                  type="checkbox"
                  checked={options[key]}
                  onChange={(e) => setOptions({ ...options, [key]: e.target.checked })}
                  className="mt-1"
                  disabled={isRunning}
                />
                <div>
                  <p className="font-medium text-gray-900">{label}</p>
                  <p className="text-sm text-gray-500">{description}</p>
                  {key === 'custom_analysis' && customPrompt && (
                    <p className="text-xs text-primary-600 mt-1">Prompt configured</p>
                  )}
                </div>
              </label>
              {key === 'custom_analysis' && (
                <button
                  onClick={() => setShowCustomAnalysisDialog(true)}
                  className="p-1.5 hover:bg-gray-100 rounded"
                  title="Configure custom prompt"
                  disabled={isRunning}
                >
                  <Settings className="w-4 h-4 text-gray-500" />
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Advanced Options */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="font-medium text-gray-900 mb-4">Advanced Options</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Row Limit (optional)</label>
              <input
                type="number"
                className="input"
                placeholder="No limit"
                value={options.limit || ''}
                onChange={(e) => setOptions({ ...options, limit: e.target.value ? parseInt(e.target.value) : null })}
                disabled={isRunning}
              />
            </div>
            <div>
              <label className="label">Concurrent Threads</label>
              <input
                type="number"
                className="input"
                value={options.threads}
                onChange={(e) => setOptions({ ...options, threads: parseInt(e.target.value) || 50 })}
                disabled={isRunning}
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Action Button */}
      <div className="flex gap-4">
        {isRunning ? (
          <button onClick={cancelAnalysis} className="btn btn-danger">
            <Square className="w-4 h-4 mr-2" />
            Cancel Analysis
          </button>
        ) : (
          <button
            onClick={startAnalysis}
            disabled={!file}
            className="btn btn-primary"
          >
            <Play className="w-4 h-4 mr-2" />
            Start Analysis
          </button>
        )}
      </div>

      {/* Job Status */}
      {job && (
        <Card>
          <CardHeader
            title="Analysis Progress"
            description={`Job ID: ${job.job_id}`}
            action={
              <div className="flex items-center gap-2">
                {job.status === 'running' && <LoadingSpinner size="sm" />}
                {job.status === 'completed' && <CheckCircle className="w-5 h-5 text-success-500" />}
                {job.status === 'failed' && <AlertCircle className="w-5 h-5 text-danger-500" />}
                <span className={cn(
                  'text-sm font-medium capitalize',
                  job.status === 'completed' && 'text-success-600',
                  job.status === 'failed' && 'text-danger-600',
                  job.status === 'running' && 'text-primary-600'
                )}>
                  {job.status}
                </span>
              </div>
            }
          />

          {/* Progress Bar with Step Indicators */}
          <div className="mb-4">
            {/* Step Indicators */}
            <div className="flex justify-between mb-3">
              {['Upload', 'Cleanup', 'Analysis', 'Aggregation', 'Complete'].map((step, index) => {
                const stepProgress = (index / 4) * 100
                const isActive = job.progress >= stepProgress && job.progress < stepProgress + 25
                const isComplete = job.progress > stepProgress + 25 || (job.status === 'completed' && index < 4)
                const isFinal = index === 4 && job.status === 'completed'

                return (
                  <div key={step} className="flex flex-col items-center">
                    <div
                      className={cn(
                        'w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all',
                        isFinal || isComplete
                          ? 'bg-success-500 text-white'
                          : isActive
                          ? 'bg-primary-600 text-white ring-4 ring-primary-100'
                          : 'bg-gray-200 text-gray-500'
                      )}
                    >
                      {isFinal || isComplete ? (
                        <CheckCircle className="w-4 h-4" />
                      ) : (
                        index + 1
                      )}
                    </div>
                    <span className={cn(
                      'text-xs mt-1',
                      isActive ? 'text-primary-600 font-medium' : 'text-gray-500'
                    )}>
                      {step}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Progress Bar */}
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>{job.current_step}</span>
              <span>{job.progress.toFixed(0)}%</span>
            </div>
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full transition-all duration-500 rounded-full',
                  job.status === 'failed'
                    ? 'bg-danger-500'
                    : job.status === 'completed'
                    ? 'bg-success-500'
                    : 'bg-gradient-to-r from-primary-500 to-primary-600'
                )}
                style={{ width: `${job.progress}%` }}
              />
            </div>
          </div>

          {/* Logs */}
          <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
            <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
              {job.logs.join('\n')}
            </pre>
            <div ref={logsEndRef} />
          </div>

          {job.error_message && (
            <Alert variant="error" className="mt-4">
              {job.error_message}
            </Alert>
          )}

          {/* Output Files */}
          {job.status === 'completed' && outputFiles.length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h4 className="font-medium text-gray-900 mb-3">Output Files</h4>
              <div className="space-y-2">
                {outputFiles.map((file) => (
                  <div
                    key={file.name}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium text-gray-900 text-sm">{file.name}</p>
                        <p className="text-xs text-gray-500">
                          {file.size_mb.toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDownloadFile(file.name)}
                      className="btn btn-secondary btn-sm"
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Download
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Custom Analysis Dialog */}
      <CustomAnalysisDialog
        isOpen={showCustomAnalysisDialog}
        onClose={() => setShowCustomAnalysisDialog(false)}
        availableColumns={csvColumns}
        onPromptSelect={(prompt, columns) => {
          setCustomPrompt(prompt)
          setCustomColumns(columns)
          setOptions({ ...options, custom_analysis: true })
        }}
      />
    </div>
  )
}
