import { describe, expect, it, vi } from 'vitest'

import { saveAccessToken } from '../core/token-store'
import { httpClient } from './http-client'

describe('httpClient', () => {
  it('envía el token solo en Authorization y omite credenciales del navegador', async () => {
    saveAccessToken('token-de-prueba')
    const fetchMock = vi.spyOn(window, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await httpClient.get<{ ok: boolean }>('/health')

    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(url).toBe('/api/v1/health')
    expect(String(url)).not.toContain('token-de-prueba')
    expect(init?.credentials).toBe('omit')
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer token-de-prueba')
  })

  it('descarga archivos asociando el blob y retrasando la revocación para evitar cancelaciones en Chromium', async () => {
    vi.useFakeTimers()
    const createObjectUrlMock = vi.fn().mockReturnValue('blob:http://localhost/test-blob')
    const revokeObjectUrlMock = vi.fn()
    window.URL.createObjectURL = createObjectUrlMock
    window.URL.revokeObjectURL = revokeObjectUrlMock

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    vi.spyOn(window, 'fetch').mockResolvedValue(
      new Response('col1,col2\nval1,val2', {
        status: 200,
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="reporte_custom.csv"',
        },
      }),
    )

    await httpClient.download('/databases/123/export', 'fallback.csv')

    expect(createObjectUrlMock).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
    expect(revokeObjectUrlMock).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1000)
    expect(revokeObjectUrlMock).toHaveBeenCalledWith('blob:http://localhost/test-blob')

    clickSpy.mockRestore()
    vi.useRealTimers()
  })
})
