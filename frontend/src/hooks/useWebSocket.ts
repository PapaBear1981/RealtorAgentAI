/**
 * React hook for WebSocket integration.
 * 
 * This hook provides easy-to-use WebSocket functionality for React components
 * including automatic connection management, message handling, and cleanup.
 */

import { useEffect, useRef, useState } from 'react'
import { websocketService, WebSocketMessage, AgentStatusUpdate, ContractStatusUpdate, DocumentProcessingUpdate, SystemStatusUpdate } from '@/services/websocketService'

export interface UseWebSocketOptions {
  autoConnect?: boolean
  reconnectOnMount?: boolean
}

export interface WebSocketState {
  isConnected: boolean
  isConnecting: boolean
  error: Event | null
  lastMessage: WebSocketMessage | null
}

/**
 * Main WebSocket hook
 */
export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { autoConnect = true, reconnectOnMount = true } = options
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null,
  })

  const unsubscribeRefs = useRef<(() => void)[]>([])

  useEffect(() => {
    // Set up connection handlers
    const unsubscribeConnect = websocketService.onConnect(() => {
      setState(prev => ({ ...prev, isConnected: true, isConnecting: false, error: null }))
    })

    const unsubscribeDisconnect = websocketService.onDisconnect(() => {
      setState(prev => ({ ...prev, isConnected: false, isConnecting: false }))
    })

    const unsubscribeError = websocketService.onError((error) => {
      setState(prev => ({ ...prev, error, isConnecting: false }))
    })

    unsubscribeRefs.current.push(unsubscribeConnect, unsubscribeDisconnect, unsubscribeError)

    // Auto-connect if requested
    if (autoConnect && !websocketService.isConnected()) {
      setState(prev => ({ ...prev, isConnecting: true }))
      websocketService.connect().catch(error => {
        console.error('Failed to connect WebSocket:', error)
        setState(prev => ({ ...prev, error, isConnecting: false }))
      })
    }

    return () => {
      // Cleanup subscriptions
      unsubscribeRefs.current.forEach(unsubscribe => unsubscribe())
      unsubscribeRefs.current = []
    }
  }, [autoConnect])

  const connect = async () => {
    setState(prev => ({ ...prev, isConnecting: true, error: null }))
    try {
      await websocketService.connect()
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Event, isConnecting: false }))
    }
  }

  const disconnect = () => {
    websocketService.disconnect()
  }

  const send = (type: string, data: any) => {
    websocketService.send(type, data)
  }

  return {
    ...state,
    connect,
    disconnect,
    send,
  }
}

/**
 * Hook for subscribing to specific message types
 */
export function useWebSocketSubscription<T = any>(
  messageType: string,
  handler: (data: T) => void,
  dependencies: any[] = []
) {
  useEffect(() => {
    const unsubscribe = websocketService.subscribe(messageType, (message) => {
      handler(message.data as T)
    })

    return unsubscribe
  }, [messageType, ...dependencies])
}

/**
 * Hook for agent status updates
 */
export function useAgentStatusUpdates(handler: (update: AgentStatusUpdate) => void) {
  useEffect(() => {
    const unsubscribe = websocketService.subscribeToAgentUpdates(handler)
    return unsubscribe
  }, [handler])
}

/**
 * Hook for contract status updates
 */
export function useContractStatusUpdates(handler: (update: ContractStatusUpdate) => void) {
  useEffect(() => {
    const unsubscribe = websocketService.subscribeToContractUpdates(handler)
    return unsubscribe
  }, [handler])
}

/**
 * Hook for document processing updates
 */
export function useDocumentProcessingUpdates(handler: (update: DocumentProcessingUpdate) => void) {
  useEffect(() => {
    const unsubscribe = websocketService.subscribeToDocumentUpdates(handler)
    return unsubscribe
  }, [handler])
}

/**
 * Hook for system status updates
 */
export function useSystemStatusUpdates(handler: (update: SystemStatusUpdate) => void) {
  useEffect(() => {
    const unsubscribe = websocketService.subscribeToSystemUpdates(handler)
    return unsubscribe
  }, [handler])
}

/**
 * Hook for real-time collaboration
 */
export function useCollaboration(roomId: string) {
  const [participants, setParticipants] = useState<string[]>([])
  const [typingUsers, setTypingUsers] = useState<string[]>([])

  useEffect(() => {
    if (!roomId) return

    // Join room
    websocketService.joinRoom(roomId)

    // Subscribe to collaboration events
    const unsubscribeParticipants = websocketService.subscribe('room_participants', (message) => {
      setParticipants(message.data.participants || [])
    })

    const unsubscribeTyping = websocketService.subscribe('user_typing', (message) => {
      const { user_id, is_typing } = message.data
      setTypingUsers(prev => {
        if (is_typing) {
          return prev.includes(user_id) ? prev : [...prev, user_id]
        } else {
          return prev.filter(id => id !== user_id)
        }
      })
    })

    return () => {
      // Leave room and cleanup
      websocketService.leaveRoom(roomId)
      unsubscribeParticipants()
      unsubscribeTyping()
    }
  }, [roomId])

  const sendTyping = (isTyping: boolean) => {
    websocketService.sendTyping(roomId, isTyping)
  }

  return {
    participants,
    typingUsers,
    sendTyping,
  }
}

/**
 * Hook for real-time notifications
 */
export function useRealTimeNotifications() {
  const [notifications, setNotifications] = useState<any[]>([])

  useEffect(() => {
    const unsubscribe = websocketService.subscribe('notification', (message) => {
      setNotifications(prev => [message.data, ...prev].slice(0, 50)) // Keep last 50 notifications
    })

    return unsubscribe
  }, [])

  const clearNotifications = () => {
    setNotifications([])
  }

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id))
  }

  return {
    notifications,
    clearNotifications,
    removeNotification,
  }
}

/**
 * Hook for real-time metrics
 */
export function useRealTimeMetrics() {
  const [metrics, setMetrics] = useState<Record<string, number>>({})
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  useEffect(() => {
    const unsubscribe = websocketService.subscribe('metrics_update', (message) => {
      setMetrics(message.data.metrics || {})
      setLastUpdate(new Date())
    })

    return unsubscribe
  }, [])

  return {
    metrics,
    lastUpdate,
  }
}

/**
 * Hook for connection status with automatic reconnection
 */
export function useWebSocketConnection() {
  const { isConnected, isConnecting, error, connect } = useWebSocket()
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const maxReconnectAttempts = 5

  useEffect(() => {
    if (error && !isConnected && reconnectAttempts < maxReconnectAttempts) {
      const timeout = setTimeout(() => {
        setReconnectAttempts(prev => prev + 1)
        connect()
      }, Math.pow(2, reconnectAttempts) * 1000) // Exponential backoff

      return () => clearTimeout(timeout)
    }
  }, [error, isConnected, reconnectAttempts, connect])

  useEffect(() => {
    if (isConnected) {
      setReconnectAttempts(0)
    }
  }, [isConnected])

  return {
    isConnected,
    isConnecting,
    error,
    reconnectAttempts,
    maxReconnectAttempts,
  }
}
