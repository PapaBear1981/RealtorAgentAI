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
  // Actions
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setLoading: (loading: boolean) => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      // Actions
      login: async (email: string, password: string) => {
        set({ isLoading: true })
        try {
          // Mock authentication for demo purposes
          // TODO: Replace with actual API call
          await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API delay

          if (email === 'admin@example.com' && password === 'password') {
            const mockUser: User = {
              id: '1',
              email: 'admin@example.com',
              name: 'Admin User',
              role: 'admin',
              created_at: new Date().toISOString(),
            }

            const mockToken = 'mock-jwt-token-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9)

            set({
              user: mockUser,
              token: mockToken,
              isAuthenticated: true,
              isLoading: false,
            })
          } else {
            throw new Error('Invalid credentials')
          }
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
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

      checkAuth: async () => {
        const { token, user } = get()

        // Debug logging
        console.log('checkAuth called:', { token: !!token, user: !!user, tokenPrefix: token?.substring(0, 20) })

        if (!token) {
          console.log('No token found, clearing auth state')
          set({ isAuthenticated: false, user: null })
          return
        }

        set({ isLoading: true })
        try {
          // For mock authentication, validate the token format and restore user
          if (token.startsWith('mock-jwt-token-') && user) {
            // Token is valid and we have user data, restore the session
            console.log('Valid session found, restoring authentication')
            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            })
          } else {
            // Invalid token or missing user data, clear session
            console.log('Invalid session data, clearing auth state')
            throw new Error('Invalid session data')
          }

          // TODO: Replace with actual API call when backend is ready
          // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me`, {
          //   headers: {
          //     'Authorization': `Bearer ${token}`,
          //   },
          // })
          //
          // if (!response.ok) {
          //   throw new Error('Auth check failed')
          // }
          //
          // const user = await response.json()
          // set({
          //   user,
          //   isAuthenticated: true,
          //   isLoading: false,
          // })
        } catch (error) {
          console.log('checkAuth error:', error)
          set({
            user: null,
            token: null,
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
