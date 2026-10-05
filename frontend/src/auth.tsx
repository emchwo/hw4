import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import * as api from './api'

export type AuthMode = 'login' | 'register'

interface AuthContextValue {
  user: api.User | null
  loading: boolean
  modal: AuthMode | null
  openModal: (mode: AuthMode) => void
  closeModal: () => void
  login: (email: string, password: string) => Promise<void>
  register: (data: api.RegisterData) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<api.User | null>(null)
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState<AuthMode | null>(null)

  useEffect(() => {
    api
      .getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const openModal = useCallback((mode: AuthMode) => setModal(mode), [])
  const closeModal = useCallback(() => setModal(null), [])

  const login = useCallback(async (email: string, password: string) => {
    setUser(await api.login(email, password))
    setModal(null)
  }, [])

  const register = useCallback(async (data: api.RegisterData) => {
    setUser(await api.register(data))
    setModal(null)
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, modal, openModal, closeModal, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
