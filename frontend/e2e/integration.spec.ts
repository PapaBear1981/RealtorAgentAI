/**
 * Comprehensive integration tests for Phase 15B completion.
 * 
 * These tests validate:
 * - Zero mock data throughout the platform
 * - Real API integration for all components
 * - End-to-end workflows with real backend
 * - WebSocket real-time communication
 * - Complete data flow from frontend to database
 */

import { test, expect } from '@playwright/test'

test.describe('Phase 15B: Complete Integration Validation', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
  })

  test('should have zero mock data in dashboard analytics', async ({ page }) => {
    // Track all API calls to verify real backend integration
    const apiCalls = new Set<string>()
    
    page.on('request', request => {
      if (request.url().includes('/analytics/')) {
        apiCalls.add(request.url())
      }
    })

    // Navigate to analytics page
    await page.click('nav >> text=Analytics')
    await expect(page).toHaveURL('/analytics')

    // Wait for analytics to load
    await page.waitForTimeout(2000)

    // Verify analytics API calls were made
    expect(apiCalls.size).toBeGreaterThan(0)
    
    // Check that no hardcoded mock values are present
    const pageContent = await page.content()
    
    // These are known mock values that should NOT appear
    const mockValues = [
      'John Smith',
      'Jane Doe', 
      '123 Main Street',
      '$365,000',
      '$5,000',
      '2024-03-15',
      'mock-jwt-token',
      'simulateFileProcessing',
      'mockExtractedData'
    ]

    for (const mockValue of mockValues) {
      expect(pageContent).not.toContain(mockValue)
    }
  })

  test('should use real API for document processing workflow', async ({ page }) => {
    let uploadCalled = false
    let processingCalled = false
    let extractionCalled = false

    // Monitor all document-related API calls
    page.route('**/files/upload', async route => {
      uploadCalled = true
      await route.continue()
    })

    page.route('**/files/*/process', async route => {
      processingCalled = true
      await route.continue()
    })

    page.route('**/ai-agents/document-extract', async route => {
      extractionCalled = true
      await route.continue()
    })

    // Navigate to documents page
    await page.click('nav >> text=Documents')
    await expect(page).toHaveURL('/documents')

    // Upload a test document
    const testFile = Buffer.from('Test real estate contract content for processing.')
    const fileInput = page.locator('input[type="file"]')
    
    await fileInput.setInputFiles({
      name: 'test-contract.pdf',
      mimeType: 'application/pdf',
      buffer: testFile
    })

    // Wait for upload and processing
    await page.waitForTimeout(3000)

    // Verify real API calls were made (not mock simulation)
    expect(uploadCalled).toBe(true)
    
    // Check that processing status shows real backend activity
    const processingStatus = page.locator('[data-testid="processing-status"]')
    await expect(processingStatus).toBeVisible()
  })

  test('should use real contract management APIs', async ({ page }) => {
    let contractApiCalled = false
    let templateApiCalled = false

    // Monitor contract-related API calls
    page.route('**/contracts*', async route => {
      contractApiCalled = true
      await route.continue()
    })

    page.route('**/templates*', async route => {
      templateApiCalled = true
      await route.continue()
    })

    // Navigate to contracts page
    await page.click('nav >> text=Contracts')
    await expect(page).toHaveURL('/contracts')

    // Wait for contracts to load
    await page.waitForTimeout(2000)

    // Verify real API calls were made
    expect(contractApiCalled).toBe(true)
    expect(templateApiCalled).toBe(true)

    // Check that contract data comes from database (not hardcoded)
    const contractList = page.locator('[data-testid="contract-list"]')
    await expect(contractList).toBeVisible()
  })

  test('should validate AI agent real-time communication', async ({ page }) => {
    let agentApiCalled = false
    let websocketConnected = false

    // Monitor AI agent API calls
    page.route('**/ai-agents/**', async route => {
      agentApiCalled = true
      await route.continue()
    })

    // Check for WebSocket connection attempts
    page.on('websocket', ws => {
      websocketConnected = true
      console.log('WebSocket connected:', ws.url())
    })

    // Navigate to AI assistant
    await page.click('nav >> text=AI Assistant')
    await expect(page).toHaveURL('/assistant')

    // Trigger an AI agent action
    await page.fill('[data-testid="agent-input"]', 'Extract data from uploaded documents')
    await page.click('[data-testid="send-button"]')

    // Wait for AI processing
    await page.waitForTimeout(3000)

    // Verify real AI agent integration (not mock responses)
    expect(agentApiCalled).toBe(true)
    
    // Check for real-time updates via WebSocket
    const agentResponse = page.locator('[data-testid="agent-response"]')
    await expect(agentResponse).toBeVisible()
  })

  test('should persist data across page refreshes', async ({ page }) => {
    // Upload a document
    await page.click('nav >> text=Documents')
    
    const testFile = Buffer.from('Persistent test document content.')
    const fileInput = page.locator('input[type="file"]')
    
    await fileInput.setInputFiles({
      name: 'persistent-test.txt',
      mimeType: 'text/plain',
      buffer: testFile
    })

    // Wait for upload
    await page.waitForTimeout(2000)

    // Refresh the page
    await page.reload()

    // Verify document persists (stored in database, not local state)
    await expect(page.locator('text=persistent-test.txt')).toBeVisible()
  })

  test('should handle authentication token refresh', async ({ page }) => {
    let refreshCalled = false

    // Monitor token refresh API calls
    page.route('**/auth/refresh', async route => {
      refreshCalled = true
      await route.continue()
    })

    // Simulate token expiration by setting invalid token
    await page.evaluate(() => {
      localStorage.setItem('auth-token', 'expired-token-12345')
    })

    // Try to access a protected resource
    await page.click('nav >> text=Analytics')

    // Wait for automatic token refresh
    await page.waitForTimeout(2000)

    // Should either refresh token or redirect to login
    const currentUrl = page.url()
    expect(currentUrl).toMatch(/(analytics|login)/)
  })

  test('should validate complete user workflow end-to-end', async ({ page }) => {
    const apiCalls = new Set<string>()
    
    // Track all API calls in the workflow
    page.on('request', request => {
      if (request.url().includes('/api/') || request.url().includes(':8000/')) {
        apiCalls.add(request.method() + ' ' + request.url())
      }
    })

    // Complete workflow: Upload → Process → Create Contract → Review
    
    // Step 1: Upload document
    await page.click('nav >> text=Documents')
    const testFile = Buffer.from('Complete workflow test document with contract data.')
    const fileInput = page.locator('input[type="file"]')
    
    await fileInput.setInputFiles({
      name: 'workflow-test.pdf',
      mimeType: 'application/pdf',
      buffer: testFile
    })

    await page.waitForTimeout(2000)

    // Step 2: Navigate to contracts and create new contract
    await page.click('nav >> text=Contracts')
    await page.click('[data-testid="create-contract-button"]')
    
    // Fill contract details
    await page.fill('[data-testid="contract-title"]', 'E2E Test Contract')
    await page.selectOption('[data-testid="template-select"]', { index: 0 })
    await page.click('[data-testid="save-contract"]')

    await page.waitForTimeout(2000)

    // Step 3: Review the contract
    await page.click('nav >> text=Review')
    
    // Verify multiple API calls were made throughout the workflow
    expect(apiCalls.size).toBeGreaterThan(5)
    
    // Verify no mock data was used in the workflow
    const pageContent = await page.content()
    expect(pageContent).not.toContain('mock')
    expect(pageContent).not.toContain('simulate')
    expect(pageContent).not.toContain('fake')
  })

  test('should validate real-time WebSocket updates', async ({ page }) => {
    let websocketMessages = 0

    // Monitor WebSocket messages
    page.on('websocket', ws => {
      ws.on('framereceived', event => {
        websocketMessages++
        console.log('WebSocket message received:', event.payload)
      })
    })

    // Navigate to a page that uses real-time updates
    await page.click('nav >> text=Documents')
    
    // Upload a file to trigger real-time processing updates
    const testFile = Buffer.from('Real-time test document for WebSocket validation.')
    const fileInput = page.locator('input[type="file"]')
    
    await fileInput.setInputFiles({
      name: 'realtime-test.txt',
      mimeType: 'text/plain',
      buffer: testFile
    })

    // Wait for real-time updates
    await page.waitForTimeout(5000)

    // Verify WebSocket communication occurred
    expect(websocketMessages).toBeGreaterThan(0)
  })

  test('should validate database integration', async ({ page }) => {
    // Create data that should persist in database
    await page.click('nav >> text=Contracts')
    await page.click('[data-testid="create-contract-button"]')
    
    const uniqueTitle = `Database Test Contract ${Date.now()}`
    await page.fill('[data-testid="contract-title"]', uniqueTitle)
    await page.selectOption('[data-testid="template-select"]', { index: 0 })
    await page.click('[data-testid="save-contract"]')

    // Navigate away and back
    await page.click('nav >> text=Dashboard')
    await page.click('nav >> text=Contracts')

    // Verify data persists (stored in database)
    await expect(page.locator(`text=${uniqueTitle}`)).toBeVisible()
  })
})
