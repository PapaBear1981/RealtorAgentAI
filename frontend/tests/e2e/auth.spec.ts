/**
 * End-to-end tests for authentication flows.
 * 
 * Tests complete authentication workflows including:
 * - Login with valid credentials
 * - Login with invalid credentials
 * - JWT token management
 * - Role-based access control
 * - Session persistence
 * - Logout functionality
 */

import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto('/login')
  })

  test('should login with valid credentials', async ({ page }) => {
    // Fill login form with seeded user credentials
    await page.fill('[data-testid="email-input"]', 'admin@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    
    // Submit login form
    await page.click('[data-testid="login-button"]')
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Should display user name in navigation
    await expect(page.locator('[data-testid="user-name"]')).toContainText('Admin User')
    
    // Should have authentication token in localStorage
    const token = await page.evaluate(() => localStorage.getItem('auth-token'))
    expect(token).toBeTruthy()
  })

  test('should show error for invalid credentials', async ({ page }) => {
    // Fill login form with invalid credentials
    await page.fill('[data-testid="email-input"]', 'invalid@example.com')
    await page.fill('[data-testid="password-input"]', 'wrongpassword')
    
    // Submit login form
    await page.click('[data-testid="login-button"]')
    
    // Should show error message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible()
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Invalid credentials')
    
    // Should remain on login page
    await expect(page).toHaveURL('/login')
  })

  test('should persist session after page refresh', async ({ page }) => {
    // Login first
    await page.fill('[data-testid="email-input"]', 'admin@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Refresh the page
    await page.reload()
    
    // Should still be on dashboard (session persisted)
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('[data-testid="user-name"]')).toContainText('Admin User')
  })

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.fill('[data-testid="email-input"]', 'admin@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Click logout button
    await page.click('[data-testid="logout-button"]')
    
    // Should redirect to login page
    await expect(page).toHaveURL('/login')
    
    // Should clear authentication token
    const token = await page.evaluate(() => localStorage.getItem('auth-token'))
    expect(token).toBeFalsy()
  })

  test('should enforce role-based access control', async ({ page }) => {
    // Login as regular agent (not admin)
    await page.fill('[data-testid="email-input"]', 'agent@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Try to access admin-only page
    await page.goto('/admin')
    
    // Should be redirected or show access denied
    await expect(page.locator('[data-testid="access-denied"]')).toBeVisible()
  })

  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Try to access protected page without authentication
    await page.goto('/dashboard')
    
    // Should redirect to login page
    await expect(page).toHaveURL('/login')
  })

  test('should handle token expiration gracefully', async ({ page }) => {
    // Login first
    await page.fill('[data-testid="email-input"]', 'admin@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Simulate expired token by setting invalid token
    await page.evaluate(() => {
      localStorage.setItem('auth-token', 'expired-token')
    })
    
    // Try to navigate to another page
    await page.goto('/documents')
    
    // Should redirect to login due to invalid token
    await expect(page).toHaveURL('/login')
  })

  test('should validate form inputs', async ({ page }) => {
    // Try to submit empty form
    await page.click('[data-testid="login-button"]')
    
    // Should show validation errors
    await expect(page.locator('[data-testid="email-error"]')).toBeVisible()
    await expect(page.locator('[data-testid="password-error"]')).toBeVisible()
    
    // Fill invalid email
    await page.fill('[data-testid="email-input"]', 'invalid-email')
    await page.click('[data-testid="login-button"]')
    
    // Should show email format error
    await expect(page.locator('[data-testid="email-error"]')).toContainText('Invalid email format')
  })

  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept login request and simulate network error
    await page.route('**/auth/login', route => {
      route.abort('failed')
    })
    
    // Fill login form
    await page.fill('[data-testid="email-input"]', 'admin@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    
    // Should show network error message
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Network error')
  })

  test('should show loading state during login', async ({ page }) => {
    // Intercept login request to add delay
    await page.route('**/auth/login', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      route.continue()
    })
    
    // Fill login form
    await page.fill('[data-testid="email-input"]', 'admin@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    
    // Click login button
    await page.click('[data-testid="login-button"]')
    
    // Should show loading state
    await expect(page.locator('[data-testid="login-loading"]')).toBeVisible()
    
    // Loading should disappear after login completes
    await expect(page.locator('[data-testid="login-loading"]')).not.toBeVisible()
  })
})
