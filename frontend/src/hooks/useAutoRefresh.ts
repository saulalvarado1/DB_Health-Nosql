import { useEffect, useRef } from 'react'

interface AutoRefreshOptions {
  callback: () => Promise<void> | void
  enabled: boolean
  intervalMs: number
  onError?: (error: unknown) => void
}

const MINIMUM_INTERVAL_MS = 1_000

export function useAutoRefresh({ callback, enabled, intervalMs, onError }: AutoRefreshOptions) {
  const callbackRef = useRef(callback)
  const onErrorRef = useRef(onError)

  useEffect(() => {
    callbackRef.current = callback
  }, [callback])

  useEffect(() => {
    onErrorRef.current = onError
  }, [onError])

  useEffect(() => {
    if (!enabled) return

    const delay = Math.max(MINIMUM_INTERVAL_MS, intervalMs)
    let cancelled = false
    let running = false
    let timerId: number | undefined

    function scheduleNextRun() {
      if (cancelled) return
      if (timerId !== undefined) window.clearTimeout(timerId)
      timerId = window.setTimeout(() => void run(), delay)
    }

    async function run() {
      timerId = undefined
      if (cancelled || running) return
      if (document.visibilityState !== 'visible') {
        scheduleNextRun()
        return
      }

      running = true
      try {
        await callbackRef.current()
      } catch (error) {
        onErrorRef.current?.(error)
      } finally {
        running = false
        scheduleNextRun()
      }
    }

    function handleVisibilityChange() {
      if (cancelled || running || document.visibilityState !== 'visible') return
      if (timerId !== undefined) window.clearTimeout(timerId)
      timerId = undefined
      void run()
    }

    scheduleNextRun()
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      cancelled = true
      if (timerId !== undefined) window.clearTimeout(timerId)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [enabled, intervalMs])
}
