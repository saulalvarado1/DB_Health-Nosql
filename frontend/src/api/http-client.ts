import { API_BASE_URL } from '../core/environment'
import { clearAccessToken, readAccessToken } from '../core/token-store'

const REQUEST_TIMEOUT_MS = 15_000
export const AUTH_EXPIRED_EVENT = 'db-health-monitor:auth-expired'

interface ErrorPayload {
  detail?: string | Array<{ msg?: string }>
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function errorMessage(payload: ErrorPayload | null, fallback: string): string {
  if (typeof payload?.detail === 'string') return payload.detail
  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail.flatMap((item) => (item.msg ? [item.msg] : []))
    if (messages.length > 0) return messages.join(' ')
  }
  return fallback
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  const token = readAccessToken()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
    })

    if (response.status === 204) return undefined as T

    const payload = (await response.json().catch(() => null)) as ErrorPayload | T | null
    if (!response.ok) {
      if (response.status === 401 && token) {
        clearAccessToken()
        window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
      }
      throw new ApiError(
        errorMessage(payload as ErrorPayload | null, 'No se pudo completar la solicitud.'),
        response.status,
      )
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('La API tardó demasiado en responder.', 408)
    }
    throw new ApiError('No fue posible conectar con la API.', 0)
  } finally {
    window.clearTimeout(timeout)
  }
}

export const httpClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: 'DELETE' }),
  download: async (path: string, fallbackFilename: string) => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
    const token = readAccessToken()
    const headers = new Headers()
    if (token) headers.set('Authorization', `Bearer ${token}`)

    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        headers,
        signal: controller.signal,
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
      })

      if (!response.ok) {
        if (response.status === 401 && token) {
          clearAccessToken()
          window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
        }
        throw new ApiError('No fue posible descargar el archivo.', response.status)
      }

      const blob = await response.blob()
      const disposition = response.headers.get('Content-Disposition')
      let filename = fallbackFilename
      if (disposition && disposition.includes('filename=')) {
        const match = disposition.match(/filename="?([^";]+)"?/)
        if (match?.[1]) filename = match[1]
      }

      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      if (error instanceof ApiError) throw error
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError('La descarga tardó demasiado en responder.', 408)
      }
      throw new ApiError('No fue posible descargar el reporte.', 0)
    } finally {
      window.clearTimeout(timeout)
    }
  },
}

