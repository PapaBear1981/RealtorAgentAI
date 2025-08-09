import { authService } from '@/services/authService'
import type { AuthState, User } from '@/types'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Cookie storage implementation for Zustand persist
const cookieStorage = {
  getItem: (name: string) => {
    if (typeof document === 'undefined') return null
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    if (parts.length === 2) {
      const cookieValue = parts.pop()?.split(';').shift() || null
      if (cookieValue) {
        try {
          return JSON.parse(decodeURIComponent(cookieValue))
        } catch {
          return null
        }
      }
    }
    return null
  },
  setItem: (name: string, value: any): void => {
    if (typeof document === 'undefined') return
    const encodedValue = encodeURIComponent(JSON.stringify(value))
    document.cookie = `${name}=${encodedValue}; path=/; max-age=${60 * 60 * 24 * 7}` // 7 days
  },
  removeItem: (name: string): void => {
    if (typeof document === 'undefined') return
    document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT`
  },
}

interface AuthStore extends AuthState {
  refreshToken: string | null
  // Actions
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setRefreshToken: (refreshToken: string | null) => void
  setLoading: (loading: boolean) => void
  checkAuth: () => Promise<void>
  refreshAccessToken: () => Promise<void>
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      // Actions
      login: async (email: string, password: string) => {
        set({ isLoading: true })
        try {
          const response = await authService.login(email, password)

          set({
            user: response.user,
            token: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: async () => {
        const { token } = get()

        // Call logout API if we have a token
        if (token) {
          try {
            await authService.logout(token)
          } catch (error) {
            console.warn('Logout API call failed:', error)
          }
        }

        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
        })
      },

      setUser: (user: User | null) => {
        set({
          user,
          isAuthenticated: !!user
        })
      },

      setToken: (token: string | null) => {
        set({ token })
      },

      setLoading: (isLoading: boolean) => {
        set({ isLoading })
      },

      setRefreshToken: (refreshToken: string | null) => {
        set({ refreshToken })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()

        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        try {
          const response = await authService.refreshToken(refreshToken)

          set({
            user: response.user,
            token: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
          })
        } catch (error) {
          // Refresh failed, clear auth state
          set({
            user: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
          })
          throw error
        }
      },

      checkAuth: async () => {
        const { token } = get()

        if (!token) {
          set({ isAuthenticated: false, user: null })
          return
        }

        set({ isLoading: true })
        try {
          const user = await authService.validateToken(token)

          if (user) {
            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            })
          } else {
            throw new Error('Token validation failed')
          }
        } catch (error) {
          console.warn('checkAuth error:', error)
          set({
            user: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: cookieStorage,
    }
  )
)
