import { generateUniqueId } from '@/utils/idGenerator'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Message {
  id: string
  type: 'user' | 'agent' | 'system' | 'action'
  content: string
  timestamp: string
  context?: string
  actionType?: 'contract_fill' | 'document_extract' | 'signature_send' | 'review_request' | 'file_search'
  actionStatus?: 'pending' | 'in_progress' | 'completed' | 'failed'
  actionData?: any
}

interface AgentAction {
  id: string
  type: 'contract_fill' | 'document_extract' | 'signature_send' | 'review_request' | 'file_search'
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  description: string
  progress?: number
  result?: any
  error?: string
}

interface AssistantAgentState {
  isOpen: boolean
  messages: Message[]
  currentContext: {
    page: string
    dealId?: string
    contractId?: string
    documentName?: string
    availableFiles?: string[]
    availableContracts?: string[]
  }
  isLoading: boolean
  currentActions: AgentAction[]

  // Actions
  togglePanel: () => void
  openPanel: () => void
  closePanel: () => void
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  setLoading: (loading: boolean) => void
  updateContext: (context: AssistantAgentState['currentContext']) => void
  clearMessages: () => void
  addAction: (action: Omit<AgentAction, 'id'>) => void
  updateAction: (id: string, updates: Partial<AgentAction>) => void
  removeAction: (id: string) => void
}

export const useAssistantAgentStore = create<AssistantAgentState>()(
  persist(
    (set, get) => ({
      isOpen: false,
      messages: [
        {
          id: generateUniqueId(),
          type: 'agent',
          content: `Hello! I'm your AI Assistant Agent for real estate contracts. I can actively help you by performing tasks on your behalf.

I can:
• **Fill out contracts** using information from your uploaded files
• **Extract data** from documents and organize it
• **Send contracts** for review and signatures
• **Search through** your files and folders
• **Coordinate workflows** between different parts of the system

Just tell me what you'd like me to do! For example: "Fill out the Purchase Agreement using the information from the Johnson's folder"`,
          timestamp: new Date().toISOString(),
          context: 'Dashboard'
        }
      ],
      currentContext: {
        page: 'Dashboard',
        availableFiles: ['Johnson_Property_Disclosure.pdf', 'Johnson_Financial_Info.pdf', 'Property_Inspection_Report.pdf'],
        availableContracts: ['Residential Purchase Agreement', 'Listing Agreement', 'Property Disclosure Form']
      },
      isLoading: false,
      currentActions: [],

      togglePanel: () => set((state) => ({ isOpen: !state.isOpen })),

      openPanel: () => set({ isOpen: true }),

      closePanel: () => set({ isOpen: false }),

      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: generateUniqueId(),
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
            id: generateUniqueId(),
            type: 'agent',
            content: `I can see you're now on the ${context.page} page${context.documentName ? ` working on "${context.documentName}"` : ''}.

${context.availableFiles?.length ? `I can see you have ${context.availableFiles.length} files available: ${context.availableFiles.slice(0, 3).join(', ')}${context.availableFiles.length > 3 ? '...' : ''}` : ''}

What would you like me to help you accomplish here?`,
            timestamp: new Date().toISOString(),
            context: context.page
          }

          set((state) => ({
            messages: [...state.messages, contextMessage]
          }))
        }
      },

      addAction: (action) => {
        const newAction: AgentAction = {
          ...action,
          id: generateUniqueId()
        }
        set((state) => ({
          currentActions: [...state.currentActions, newAction]
        }))
      },

      updateAction: (id, updates) => {
        set((state) => ({
          currentActions: state.currentActions.map(action =>
            action.id === id ? { ...action, ...updates } : action
          )
        }))
      },

      removeAction: (id) => {
        set((state) => ({
          currentActions: state.currentActions.filter(action => action.id !== id)
        }))
      },

      clearMessages: () => set({
        messages: [
          {
            id: generateUniqueId(),
            type: 'agent',
            content: `Hello! I'm your AI Assistant Agent for real estate contracts. I can actively help you by performing tasks on your behalf.

I can:
• **Fill out contracts** using information from your uploaded files
• **Extract data** from documents and organize it
• **Send contracts** for review and signatures
• **Search through** your files and folders
• **Coordinate workflows** between different parts of the system

Just tell me what you'd like me to do!`,
            timestamp: new Date().toISOString(),
            context: get().currentContext.page
          }
        ]
      })
    }),
    {
      name: 'assistant-agent-storage-v2',
      partialize: (state) => ({
        isOpen: state.isOpen,
        messages: state.messages,
        currentContext: state.currentContext,
        currentActions: state.currentActions
      })
    }
  )
)
