import type { Deal } from '@/types'
import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'

interface DealsState {
  deals: Deal[]
  currentDeal: Deal | null
  isLoading: boolean
  error: string | null
}

interface DealsActions {
  // Deal management
  fetchDeals: () => Promise<void>
  createDeal: (title: string) => Promise<Deal>
  updateDeal: (id: string, updates: Partial<Deal>) => Promise<void>
  deleteDeal: (id: string) => Promise<void>
  setCurrentDeal: (deal: Deal | null) => void

  // State management
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void
}

type DealsStore = DealsState & DealsActions

export const useDealsStore = create<DealsStore>()(
  immer((set, get) => ({
    // Initial state
    deals: [],
    currentDeal: null,
    isLoading: false,
    error: null,

    // Actions
    fetchDeals: async () => {
      set((state) => {
        state.isLoading = true
        state.error = null
      })

      try {
        // TODO: Replace with actual API call
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals`, {
          headers: {
            // 'Authorization': `Bearer ${token}`, // TODO: Get token from auth store
          },
        })

        if (!response.ok) {
          throw new Error('Failed to fetch deals')
        }

        const deals = await response.json()

        set((state) => {
          state.deals = deals
          state.isLoading = false
        })
      } catch (error) {
        set((state) => {
          state.error = error instanceof Error ? error.message : 'Unknown error'
          state.isLoading = false
        })
      }
    },

    createDeal: async (title: string) => {
      set((state) => {
        state.isLoading = true
        state.error = null
      })

      try {
        // TODO: Replace with actual API call
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            // 'Authorization': `Bearer ${token}`, // TODO: Get token from auth store
          },
          body: JSON.stringify({ title }),
        })

        if (!response.ok) {
          throw new Error('Failed to create deal')
        }

        const newDeal = await response.json()

        set((state) => {
          state.deals.push(newDeal)
          state.currentDeal = newDeal
          state.isLoading = false
        })

        return newDeal
      } catch (error) {
        set((state) => {
          state.error = error instanceof Error ? error.message : 'Unknown error'
          state.isLoading = false
        })
        throw error
      }
    },

    updateDeal: async (id: string, updates: Partial<Deal>) => {
      set((state) => {
        state.isLoading = true
        state.error = null
      })

      try {
        // TODO: Replace with actual API call
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals/${id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            // 'Authorization': `Bearer ${token}`, // TODO: Get token from auth store
          },
          body: JSON.stringify(updates),
        })

        if (!response.ok) {
          throw new Error('Failed to update deal')
        }

        const updatedDeal = await response.json()

        set((state) => {
          const index = state.deals.findIndex((deal: Deal) => deal.id === id)
          if (index !== -1) {
            state.deals[index] = updatedDeal
          }
          if (state.currentDeal?.id === id) {
            state.currentDeal = updatedDeal
          }
          state.isLoading = false
        })
      } catch (error) {
        set((state) => {
          state.error = error instanceof Error ? error.message : 'Unknown error'
          state.isLoading = false
        })
        throw error
      }
    },

    deleteDeal: async (id: string) => {
      set((state) => {
        state.isLoading = true
        state.error = null
      })

      try {
        // TODO: Replace with actual API call
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals/${id}`, {
          method: 'DELETE',
          headers: {
            // 'Authorization': `Bearer ${token}`, // TODO: Get token from auth store
          },
        })

        if (!response.ok) {
          throw new Error('Failed to delete deal')
        }

        set((state) => {
          state.deals = state.deals.filter((deal: Deal) => deal.id !== id)
          if (state.currentDeal?.id === id) {
            state.currentDeal = null
          }
          state.isLoading = false
        })
      } catch (error) {
        set((state) => {
          state.error = error instanceof Error ? error.message : 'Unknown error'
          state.isLoading = false
        })
        throw error
      }
    },

    setCurrentDeal: (deal: Deal | null) => {
      set((state) => {
        state.currentDeal = deal
      })
    },

    setLoading: (isLoading: boolean) => {
      set((state) => {
        state.isLoading = isLoading
      })
    },

    setError: (error: string | null) => {
      set((state) => {
        state.error = error
      })
    },

    clearError: () => {
      set((state) => {
        state.error = null
      })
    },
  }))
)
