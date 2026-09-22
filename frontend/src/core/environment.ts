const DEFAULT_API_BASE_URL = '/api/v1'

function isLoopback(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]'
}

export function resolveApiBaseUrl(rawValue = import.meta.env.VITE_API_BASE_URL): string {
  const value = (rawValue || DEFAULT_API_BASE_URL).trim()

  if (value.startsWith('/')) {
    if (value.startsWith('//') || value.includes('\\') || value.includes('?') || value.includes('#')) {
      throw new Error('VITE_API_BASE_URL contiene una ruta relativa no permitida.')
    }
    return value.replace(/\/$/, '')
  }

  const url = new URL(value)
  if (url.username || url.password) {
    throw new Error('VITE_API_BASE_URL no debe contener credenciales.')
  }
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && isLoopback(url.hostname))) {
    throw new Error('La API remota debe utilizar HTTPS.')
  }
  if (url.search || url.hash) {
    throw new Error('VITE_API_BASE_URL no debe contener parámetros ni fragmentos.')
  }
  return url.toString().replace(/\/$/, '')
}

export const API_BASE_URL = resolveApiBaseUrl()
