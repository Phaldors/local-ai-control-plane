import { useCallback, useEffect, useRef, useState } from 'react'

/** Loads on mount and every `intervalMs`; `reload()` forces a refresh. Stale responses are dropped. */
export function usePolling<T>(load: () => Promise<T>, intervalMs: number | null, key: unknown) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const loadRef = useRef(load)
  loadRef.current = load

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const value = await loadRef.current()
        if (!cancelled) {
          setData(value)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(e as Error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    setLoading(true)
    void run()
    const timer = intervalMs ? setInterval(() => void run(), intervalMs) : undefined
    return () => {
      cancelled = true
      if (timer) clearInterval(timer)
    }
  }, [key, intervalMs, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}
