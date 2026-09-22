import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

import type { AuthCredentials, User } from '../api/contracts'
import { AUTH_EXPIRED_EVENT } from '../api/http-client'
import { authApi } from '../api/resources'
import { clearAccessToken, readAccessToken, saveAccessToken } from '../core/token-store'
import { AuthContext } from './context'

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)

  const logout = useCallback(() => {
    clearAccessToken()
    setUser(null)
  }, [])

  useEffect(() => {
    const expireSession = () => setUser(null)
    window.addEventListener(AUTH_EXPIRED_EVENT, expireSession)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, expireSession)
  }, [])

  useEffect(() => {
    let active = true

    async function restoreSession() {
      if (!readAccessToken()) {
        if (active) setIsInitializing(false)
        return
      }
      try {
        const currentUser = await authApi.me()
        if (active) setUser(currentUser)
      } catch {
        clearAccessToken()
      } finally {
        if (active) setIsInitializing(false)
      }
    }

    void restoreSession()
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (credentials: AuthCredentials) => {
    const response = await authApi.login(credentials)
    saveAccessToken(response.access_token)
    try {
      setUser(await authApi.me())
    } catch (error) {
      clearAccessToken()
      throw error
    }
  }, [])

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      await authApi.register(credentials)
      await login(credentials)
    },
    [login],
  )

  const value = useMemo(
    () => ({ user, isInitializing, login, register, logout }),
    [isInitializing, login, logout, register, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
