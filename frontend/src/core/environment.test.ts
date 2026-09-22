import { describe, expect, it } from 'vitest'

import { resolveApiBaseUrl } from './environment'

describe('resolveApiBaseUrl', () => {
  it('acepta la ruta relativa de la API', () => {
    expect(resolveApiBaseUrl('/api/v1/')).toBe('/api/v1')
  })

  it('rechaza credenciales embebidas en la URL', () => {
    expect(() => resolveApiBaseUrl('https://usuario:secreto@example.com/api/v1')).toThrow(
      'no debe contener credenciales',
    )
  })

  it('rechaza HTTP para servidores remotos', () => {
    expect(() => resolveApiBaseUrl('http://api.example.com/api/v1')).toThrow(
      'debe utilizar HTTPS',
    )
  })

  it('permite HTTP solamente para desarrollo local', () => {
    expect(resolveApiBaseUrl('http://127.0.0.1:8000/api/v1')).toBe(
      'http://127.0.0.1:8000/api/v1',
    )
  })
})
