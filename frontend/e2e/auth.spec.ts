import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display homepage with get started button', async ({ page }) => {
    await expect(page).toHaveTitle(/RealtorAgentAI/)
    await expect(page.locator('h1')).toContainText('RealtorAgentAI')
    await expect(page.locator('text=Multi-Agent Real Estate Contract Platform')).toBeVisible()
    await expect(page.locator('text=Get Started')).toBeVisible()
  })

  test('should navigate to login page', async ({ page }) => {
    await page.click('text=Get Started')
    await expect(page).toHaveURL('/login')
    await expect(page.locator('h1')).toContainText('RealtorAgentAI')
    await expect(page.locator('text=Sign in to your account')).toBeVisible()
    await expect(page.locator('text=Demo credentials: admin@example.com / password')).toBeVisible()
  })

  test('should show validation errors for empty form', async ({ page }) => {
    await page.goto('/login')
    await page.click('button[type="submit"]')
    
    // Check for validation errors
    await expect(page.locator('text=Please enter a valid email address')).toBeVisible()
    await expect(page.locator('text=Password is required')).toBeVisible()
  })

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'invalid@example.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')
    
    // Wait for error toast
    await expect(page.locator('text=Invalid credentials')).toBeVisible()
  })

  test('should successfully login with valid credentials', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    
    // Wait for success toast and redirect
    await expect(page.locator('text=You have been logged in successfully')).toBeVisible()
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('text=Welcome, Admin User')).toBeVisible()
  })

  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL('/login')
  })

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
    
    // Logout
    await page.click('text=Logout')
    await expect(page.locator('text=You have been logged out successfully')).toBeVisible()
    await expect(page).toHaveURL('/login')
  })

  test('should maintain session across page refreshes', async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
    
    // Refresh page
    await page.reload()
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('text=Welcome, Admin User')).toBeVisible()
  })

  test('should redirect authenticated user away from login page', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
    
    // Try to access login page
    await page.goto('/login')
    await expect(page).toHaveURL('/dashboard')
  })
})
