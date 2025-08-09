/**
 * WebSocket service for real-time communication.
 * 
 * This service handles all real-time communication including:
 * - AI agent status updates
 * - Contract processing notifications
 * - Live collaboration features
 * - System status updates
 */

import { useAuthStore } from '@/stores/auth'

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
  id?: string
}

export interface AgentStatusUpdate {
  agent_id: string
  agent_type: string
  status: 'idle' | 'processing' | 'completed' | 'error'
  progress?: number
  message?: string
  execution_id?: string
}

export interface ContractStatusUpdate {
  contract_id: string
  status: 'draft' | 'review' | 'sent' | 'signed' | 'void'
  updated_by: string
  timestamp: string
  changes?: Record<string, any>
}

export interface DocumentProcessingUpdate {
  document_id: string
  status: 'uploading' | 'processing' | 'completed' | 'error'
  progress?: number
  extracted_data?: any
  error_message?: string
}

export interface SystemStatusUpdate {
  component: string
  status: 'healthy' | 'warning' | 'error'
  message?: string
  metrics?: Record<string, number>
}

type MessageHandler = (message: WebSocketMessage) => void
type ConnectionHandler = () => void
type ErrorHandler = (error: Event) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private messageHandlers: Map<string, MessageHandler[]> = new Map()
  private connectionHandlers: ConnectionHandler[] = []
  private disconnectionHandlers: ConnectionHandler[] = []
  private errorHandlers: ErrorHandler[] = []
  private isConnecting = false
  private shouldReconnect = true

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.isConnecting = true
    const token = useAuthStore.getState().token

    if (!token) {
      console.warn('No authentication token available for WebSocket connection')
      this.isConnecting = false
      return
    }

    try {
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
      this.ws = new WebSocket(`${wsUrl}?token=${token}`)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.connectionHandlers.forEach(handler => handler())
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        this.isConnecting = false
        this.disconnectionHandlers.forEach(handler => handler())
        
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
        this.errorHandlers.forEach(handler => handler(error))
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.isConnecting = false
      throw error
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Send message to server
   */
  send(type: string, data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type,
        data,
        timestamp: new Date().toISOString(),
        id: this.generateMessageId(),
      }
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected, cannot send message:', type)
    }
  }

  /**
   * Subscribe to specific message types
   */
  subscribe(messageType: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, [])
    }
    this.messageHandlers.get(messageType)!.push(handler)

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(messageType)
      if (handlers) {
        const index = handlers.indexOf(handler)
        if (index > -1) {
          handlers.splice(index, 1)
        }
      }
    }
  }

  /**
   * Subscribe to connection events
   */
  onConnect(handler: ConnectionHandler): () => void {
    this.connectionHandlers.push(handler)
    return () => {
      const index = this.connectionHandlers.indexOf(handler)
      if (index > -1) {
        this.connectionHandlers.splice(index, 1)
      }
    }
  }

  /**
   * Subscribe to disconnection events
   */
  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectionHandlers.push(handler)
    return () => {
      const index = this.disconnectionHandlers.indexOf(handler)
      if (index > -1) {
        this.disconnectionHandlers.splice(index, 1)
      }
    }
  }

  /**
   * Subscribe to error events
   */
  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.push(handler)
    return () => {
      const index = this.errorHandlers.indexOf(handler)
      if (index > -1) {
        this.errorHandlers.splice(index, 1)
      }
    }
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * Handle incoming messages
   */
  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          console.error('Error in message handler:', error)
        }
      })
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`Scheduling WebSocket reconnect attempt ${this.reconnectAttempts} in ${delay}ms`)
    
    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect().catch(error => {
          console.error('Reconnection attempt failed:', error)
        })
      }
    }, delay)
  }

  /**
   * Generate unique message ID
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Subscribe to agent status updates
   */
  subscribeToAgentUpdates(handler: (update: AgentStatusUpdate) => void): () => void {
    return this.subscribe('agent_status_update', (message) => {
      handler(message.data as AgentStatusUpdate)
    })
  }

  /**
   * Subscribe to contract status updates
   */
  subscribeToContractUpdates(handler: (update: ContractStatusUpdate) => void): () => void {
    return this.subscribe('contract_status_update', (message) => {
      handler(message.data as ContractStatusUpdate)
    })
  }

  /**
   * Subscribe to document processing updates
   */
  subscribeToDocumentUpdates(handler: (update: DocumentProcessingUpdate) => void): () => void {
    return this.subscribe('document_processing_update', (message) => {
      handler(message.data as DocumentProcessingUpdate)
    })
  }

  /**
   * Subscribe to system status updates
   */
  subscribeToSystemUpdates(handler: (update: SystemStatusUpdate) => void): () => void {
    return this.subscribe('system_status_update', (message) => {
      handler(message.data as SystemStatusUpdate)
    })
  }

  /**
   * Join a collaboration room
   */
  joinRoom(roomId: string): void {
    this.send('join_room', { room_id: roomId })
  }

  /**
   * Leave a collaboration room
   */
  leaveRoom(roomId: string): void {
    this.send('leave_room', { room_id: roomId })
  }

  /**
   * Send typing indicator
   */
  sendTyping(roomId: string, isTyping: boolean): void {
    this.send('typing', { room_id: roomId, is_typing: isTyping })
  }
}

export const websocketService = new WebSocketService()
export default websocketService
