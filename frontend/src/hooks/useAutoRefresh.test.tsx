import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAutoRefresh } from './useAutoRefresh'

function setVisibility(value: DocumentVisibilityState) {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    value,
  })
}

describe('useAutoRefresh', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setVisibility('visible')
  })

  afterEach(() => {
    vi.useRealTimers()
    setVisibility('visible')
  })

  it('ejecuta actualizaciones sucesivas después del intervalo', async () => {
    const callback = vi.fn().mockResolvedValue(undefined)
    renderHook(() => useAutoRefresh({ callback, enabled: true, intervalMs: 1_000 }))

    await act(async () => vi.advanceTimersByTimeAsync(1_000))
    expect(callback).toHaveBeenCalledTimes(1)

    await act(async () => vi.advanceTimersByTimeAsync(1_000))
    expect(callback).toHaveBeenCalledTimes(2)
  })

  it('no superpone actualizaciones lentas', async () => {
    let finishRequest: (() => void) | undefined
    const callback = vi.fn(() => new Promise<void>((resolve) => {
      finishRequest = resolve
    }))
    renderHook(() => useAutoRefresh({ callback, enabled: true, intervalMs: 1_000 }))

    await act(async () => vi.advanceTimersByTimeAsync(1_000))
    await act(async () => vi.advanceTimersByTimeAsync(10_000))
    expect(callback).toHaveBeenCalledTimes(1)

    await act(async () => {
      finishRequest?.()
      await Promise.resolve()
    })
    await act(async () => vi.advanceTimersByTimeAsync(1_000))
    expect(callback).toHaveBeenCalledTimes(2)
  })

  it('se detiene mientras la pestaña está oculta y actualiza al regresar', async () => {
    const callback = vi.fn().mockResolvedValue(undefined)
    setVisibility('hidden')
    renderHook(() => useAutoRefresh({ callback, enabled: true, intervalMs: 1_000 }))

    await act(async () => vi.advanceTimersByTimeAsync(5_000))
    expect(callback).not.toHaveBeenCalled()

    setVisibility('visible')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
      await Promise.resolve()
    })
    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('no programa consultas cuando está deshabilitado', async () => {
    const callback = vi.fn().mockResolvedValue(undefined)
    renderHook(() => useAutoRefresh({ callback, enabled: false, intervalMs: 1_000 }))

    await act(async () => vi.advanceTimersByTimeAsync(5_000))
    expect(callback).not.toHaveBeenCalled()
  })
})
