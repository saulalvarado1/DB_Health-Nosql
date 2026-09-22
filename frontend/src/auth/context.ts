import { createContext } from 'react'

import type { AuthCredentials, User } from '../api/contracts'

export interface AuthContextValue {
  user: User | null
  isInitializing: boolean
  login: (credentials: AuthCredentials) => Promise<void>
  register: (credentials: AuthCredentials) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
