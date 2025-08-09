/**
 * API client with automatic authentication and token refresh.
 * 
 * This client automatically adds authentication headers to requests
 * and handles token refresh when tokens expire.
 */

import { useAuthStore } from '@/stores/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ApiResponse<T = any> {
  data: T
  status: number
  statusText: string
}

export interface ApiError {
  detail: string
  status_code: number
}

class ApiClient {
  private baseUrl: string

  constructor() {
    this.baseUrl = API_BASE_URL
  }

  /**
   * Make an authenticated API request
   */
  async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    
    // Get current auth state
    const { token, refreshAccessToken } = useAuthStore.getState()
    
    // Add authentication header if token exists
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const requestOptions: RequestInit = {
      ...options,
      headers,
    }

    try {
      const response = await fetch(url, requestOptions)
      
      // Handle 401 Unauthorized - try to refresh token
      if (response.status === 401 && token) {
        try {
          await refreshAccessToken()
          
          // Retry the request with new token
          const newToken = useAuthStore.getState().token
          if (newToken) {
            headers['Authorization'] = `Bearer ${newToken}`
            const retryResponse = await fetch(url, { ...requestOptions, headers })
            
            if (!retryResponse.ok) {
              throw new Error(`API request failed: ${retryResponse.status} ${retryResponse.statusText}`)
            }
            
            const data = await retryResponse.json()
            return {
              data,
              status: retryResponse.status,
              statusText: retryResponse.statusText,
            }
          }
        } catch (refreshError) {
          // Refresh failed, let the original 401 error propagate
          console.warn('Token refresh failed:', refreshError)
        }
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `API request failed: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      return {
        data,
        status: response.status,
        statusText: response.statusText,
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error('Network error occurred')
    }
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'GET' })
  }

  /**
   * POST request
   */
  async post<T = any>(endpoint: string, data?: any, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * PUT request
   */
  async put<T = any>(endpoint: string, data?: any, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * PATCH request
   */
  async patch<T = any>(endpoint: string, data?: any, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' })
  }

  /**
   * Upload file with form data
   */
  async uploadFile<T = any>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, string>,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const formData = new FormData()
    formData.append('file', file)
    
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value)
      })
    }

    // Get current auth state
    const { token } = useAuthStore.getState()
    
    const headers: Record<string, string> = {
      ...options.headers as Record<string, string>,
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Don't set Content-Type for FormData - let browser set it with boundary
    delete headers['Content-Type']

    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      headers,
      body: formData,
    })
  }

  /**
   * Download file
   */
  async downloadFile(endpoint: string, filename?: string): Promise<void> {
    const response = await this.request(endpoint, { method: 'GET' })
    
    // Create blob from response
    const blob = new Blob([response.data])
    
    // Create download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename || 'download'
    
    // Trigger download
    document.body.appendChild(link)
    link.click()
    
    // Cleanup
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  /**
   * Get base URL
   */
  getBaseUrl(): string {
    return this.baseUrl
  }
}

export const apiClient = new ApiClient()
export default apiClient
