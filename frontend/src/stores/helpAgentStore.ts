import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Message {
  id: string
  type: 'user' | 'agent'
  content: string
  timestamp: string
  context?: string
}

interface HelpAgentState {
  isOpen: boolean
  messages: Message[]
  currentContext: {
    page: string
    dealId?: string
    contractId?: string
    documentName?: string
  }
  isLoading: boolean
  
  // Actions
  togglePanel: () => void
  openPanel: () => void
  closePanel: () => void
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  setLoading: (loading: boolean) => void
  updateContext: (context: HelpAgentState['currentContext']) => void
  clearMessages: () => void
}

export const useHelpAgentStore = create<HelpAgentState>()(
  persist(
    (set, get) => ({
      isOpen: false,
      messages: [
        {
          id: '1',
          type: 'agent',
          content: `Hello! I'm your AI assistant for real estate contracts. I can help you with questions about your current deal, explain contract clauses, check what's left to complete, and guide you through the process.

How can I help you today?`,
          timestamp: new Date().toISOString(),
          context: 'Dashboard'
        }
      ],
      currentContext: {
        page: 'Dashboard'
      },
      isLoading: false,

      togglePanel: () => set((state) => ({ isOpen: !state.isOpen })),
      
      openPanel: () => set({ isOpen: true }),
      
      closePanel: () => set({ isOpen: false }),
      
      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: Date.now().toString(),
          timestamp: new Date().toISOString()
        }
        set((state) => ({
          messages: [...state.messages, newMessage]
        }))
      },
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      updateContext: (context) => {
        set({ currentContext: context })
        
        // Add a context update message if the page changed
        const currentState = get()
        const lastMessage = currentState.messages[currentState.messages.length - 1]
        
        if (lastMessage && lastMessage.context !== context.page) {
          const contextMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: 'agent',
            content: `I can see you're now on the ${context.page} page${context.documentName ? ` working on "${context.documentName}"` : ''}. How can I help you here?`,
            timestamp: new Date().toISOString(),
            context: context.page
          }
          
          set((state) => ({
            messages: [...state.messages, contextMessage]
          }))
        }
      },
      
      clearMessages: () => set({ 
        messages: [
          {
            id: '1',
            type: 'agent',
            content: `Hello! I'm your AI assistant for real estate contracts. I can help you with questions about your current deal, explain contract clauses, check what's left to complete, and guide you through the process.

How can I help you today?`,
            timestamp: new Date().toISOString(),
            context: get().currentContext.page
          }
        ]
      })
    }),
    {
      name: 'help-agent-storage',
      partialize: (state) => ({
        isOpen: state.isOpen,
        messages: state.messages,
        currentContext: state.currentContext
      })
    }
  )
)
