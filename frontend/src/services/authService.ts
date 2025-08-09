/**
 * Authentication service for real backend API integration.
 * 
 * This service handles all authentication-related API calls including:
 * - Login/logout
 * - Token management and refresh
 * - User profile management
 * - Role-based access validation
 */

import { User } from '@/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface RegisterRequest {
  email: string
  name: string
  password: string
  role?: 'agent' | 'tc' | 'signer'
}

export interface ApiError {
  detail: string
  status_code: number
}

class AuthService {
  private baseUrl: string

  constructor() {
    this.baseUrl = API_BASE_URL
  }

  /**
   * Login user with email and password
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        username: email, // FastAPI OAuth2PasswordRequestForm uses 'username'
        password: password,
      }),
    })

    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    const data = await response.json()
    
    // Transform backend response to match frontend expectations
    return {
      access_token: data.access_token,
      refresh_token: data.refresh_token || '',
      token_type: data.token_type || 'bearer',
      expires_in: data.expires_in || 3600,
      user: {
        id: data.user.id.toString(),
        email: data.user.email,
        name: data.user.name,
        role: data.user.role,
        created_at: data.user.created_at,
        disabled: data.user.disabled || false,
      }
    }
  }

  /**
   * Register new user
   */
  async register(userData: RegisterRequest): Promise<User> {
    const response = await fetch(`${this.baseUrl}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    })

    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new Error(error.detail || 'Registration failed')
    }

    const data = await response.json()
    return {
      id: data.id.toString(),
      email: data.email,
      name: data.name,
      role: data.role,
      created_at: data.created_at,
      disabled: data.disabled || false,
    }
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(token: string): Promise<User> {
    const response = await fetch(`${this.baseUrl}/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new Error(error.detail || 'Failed to get user profile')
    }

    const data = await response.json()
    return {
      id: data.id.toString(),
      email: data.email,
      name: data.name,
      role: data.role,
      created_at: data.created_at,
      disabled: data.disabled || false,
    }
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    })

    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new Error(error.detail || 'Token refresh failed')
    }

    const data = await response.json()
    return {
      access_token: data.access_token,
      refresh_token: data.refresh_token || refreshToken,
      token_type: data.token_type || 'bearer',
      expires_in: data.expires_in || 3600,
      user: {
        id: data.user.id.toString(),
        email: data.user.email,
        name: data.user.name,
        role: data.user.role,
        created_at: data.user.created_at,
        disabled: data.user.disabled || false,
      }
    }
  }

  /**
   * Logout user (invalidate token on server)
   */
  async logout(token: string): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch (error) {
      // Logout should succeed even if server call fails
      console.warn('Logout server call failed:', error)
    }
  }

  /**
   * Validate token and get user info
   */
  async validateToken(token: string): Promise<User | null> {
    try {
      return await this.getCurrentUser(token)
    } catch (error) {
      console.warn('Token validation failed:', error)
      return null
    }
  }

  /**
   * Check if user has required role
   */
  hasRole(user: User | null, requiredRole: string): boolean {
    if (!user) return false
    
    // Admin has access to everything
    if (user.role === 'admin') return true
    
    // Exact role match
    if (user.role === requiredRole) return true
    
    // Role hierarchy (if needed)
    const roleHierarchy = {
      'admin': 4,
      'agent': 3,
      'tc': 2,
      'signer': 1,
    }
    
    const userLevel = roleHierarchy[user.role as keyof typeof roleHierarchy] || 0
    const requiredLevel = roleHierarchy[requiredRole as keyof typeof roleHierarchy] || 0
    
    return userLevel >= requiredLevel
  }

  /**
   * Create authorization header
   */
  createAuthHeader(token: string): Record<string, string> {
    return {
      'Authorization': `Bearer ${token}`,
    }
  }
}

export const authService = new AuthService()
export default authService
