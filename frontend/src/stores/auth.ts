import type { AuthState, User } from '@/types'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

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

            const mockToken = 'mock-jwt-token-' + Date.now()

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
        const { token } = get()
        if (!token) {
          set({ isAuthenticated: false, user: null })
          return
        }

        set({ isLoading: true })
        try {
          // TODO: Replace with actual API call
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          })

          if (!response.ok) {
            throw new Error('Auth check failed')
          }

          const user = await response.json()
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
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
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
