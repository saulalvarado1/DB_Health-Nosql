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
})
