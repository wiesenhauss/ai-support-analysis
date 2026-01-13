import { useState, useEffect, useCallback } from 'react'

interface UseApiOptions<T> {
  immediate?: boolean
  defaultValue?: T
}

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

export function useApi<T>(
  fetchFn: () => Promise<T>,
  options: UseApiOptions<T> = {}
) {
  const { immediate = true, defaultValue } = options

  const [state, setState] = useState<UseApiState<T>>({
    data: defaultValue ?? null,
    loading: immediate,
    error: null,
  })

  const execute = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetchFn()
      setState({ data, loading: false, error: null })
      return data
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error : new Error(String(error)),
      }))
      throw error
    }
  }, [fetchFn])

  const refetch = useCallback(() => {
    return execute()
  }, [execute])

  useEffect(() => {
    if (immediate) {
      execute().catch(() => {})
    }
  }, [immediate, execute])

  return {
    ...state,
    refetch,
    execute,
  }
}

export function useLazyApi<T, Args extends unknown[]>(
  fetchFn: (...args: Args) => Promise<T>
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const execute = useCallback(
    async (...args: Args) => {
      setState((prev) => ({ ...prev, loading: true, error: null }))
      try {
        const data = await fetchFn(...args)
        setState({ data, loading: false, error: null })
        return data
      } catch (error) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: error instanceof Error ? error : new Error(String(error)),
        }))
        throw error
      }
    },
    [fetchFn]
  )

  return {
    ...state,
    execute,
  }
}
