const TOKEN_KEY = 'db-health-monitor.access-token'

let memoryToken: string | null = null

export function readAccessToken(): string | null {
  if (memoryToken) return memoryToken
  if (typeof window === 'undefined') return null

  memoryToken = window.sessionStorage.getItem(TOKEN_KEY)
  return memoryToken
}

export function saveAccessToken(token: string): void {
  memoryToken = token
  window.sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  memoryToken = null
  if (typeof window !== 'undefined') {
    window.sessionStorage.removeItem(TOKEN_KEY)
  }
}
