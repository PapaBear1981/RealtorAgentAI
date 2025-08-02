import { test, expect } from '@playwright/test'

test.describe('Signature Tracker', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
    
    // Navigate to signatures page
    await page.click('nav >> text=Signatures')
    await expect(page).toHaveURL('/signatures')
  })

  test('should display signature tracker interface', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Signature Tracker')
    await expect(page.locator('text=Track multi-party signatures with audit trails and notifications')).toBeVisible()
    
    // Check for signature requests section
    await expect(page.locator('text=Signature Requests')).toBeVisible()
    await expect(page.locator('text=Manage and track all your signature requests')).toBeVisible()
  })

  test('should display signature requests list', async ({ page }) => {
    // Check for mock signature requests
    await expect(page.locator('text=Purchase Agreement - 123 Main St')).toBeVisible()
    await expect(page.locator('text=Listing Agreement - 456 Oak Ave')).toBeVisible()
    await expect(page.locator('text=Property Disclosure - 789 Pine St')).toBeVisible()
    
    // Check status badges
    await expect(page.locator('text=in progress')).toBeVisible()
    await expect(page.locator('text=completed')).toBeVisible()
    await expect(page.locator('text=sent')).toBeVisible()
  })

  test('should display progress bars for signature requests', async ({ page }) => {
    // Check that progress indicators are visible
    await expect(page.locator('text=Completion Progress')).toBeVisible()
    await expect(page.locator('text=66%')).toBeVisible() // Purchase Agreement progress
    await expect(page.locator('text=100%')).toBeVisible() // Listing Agreement progress
    await expect(page.locator('text=0%')).toBeVisible() // Property Disclosure progress
  })

  test('should display party avatars and status', async ({ page }) => {
    // Check for party information
    await expect(page.locator('text=Parties:')).toBeVisible()
    
    // Check for status badges on parties
    await expect(page.locator('[data-testid="party-status"], .text-xs:has-text("signed")')).toBeVisible()
    await expect(page.locator('[data-testid="party-status"], .text-xs:has-text("pending")')).toBeVisible()
  })

  test('should select signature request and show details', async ({ page }) => {
    // Click on first signature request
    await page.click('text=Purchase Agreement - 123 Main St')
    
    // Check details panel
    await expect(page.locator('text=Request Details')).toBeVisible()
    await expect(page.locator('text=Purchase Agreement - 123 Main St')).toBeVisible()
    
    // Check document information
    await expect(page.locator('text=Document Information')).toBeVisible()
    await expect(page.locator('text=Type:')).toBeVisible()
    await expect(page.locator('text=Created:')).toBeVisible()
    await expect(page.locator('text=Due Date:')).toBeVisible()
    await expect(page.locator('text=Status:')).toBeVisible()
  })

  test('should display signing parties in details panel', async ({ page }) => {
    // Select a signature request
    await page.click('text=Purchase Agreement - 123 Main St')
    
    // Check signing parties section
    await expect(page.locator('text=Signing Parties')).toBeVisible()
    
    // Check for party details
    await expect(page.locator('text=John Smith')).toBeVisible()
    await expect(page.locator('text=Buyer')).toBeVisible()
    await expect(page.locator('text=Jane Doe')).toBeVisible()
    await expect(page.locator('text=Seller')).toBeVisible()
    await expect(page.locator('text=Mike Johnson')).toBeVisible()
    await expect(page.locator('text=Agent')).toBeVisible()
  })

  test('should show signed party information', async ({ page }) => {
    // Select signature request
    await page.click('text=Purchase Agreement - 123 Main St')
    
    // Check for signed timestamp and IP address
    await expect(page.locator('text=Signed:')).toBeVisible()
    await expect(page.locator('text=IP:')).toBeVisible()
  })

  test('should display send reminder button for pending parties', async ({ page }) => {
    // Select signature request
    await page.click('text=Purchase Agreement - 123 Main St')
    
    // Check for send reminder button (should be visible for pending parties)
    await expect(page.locator('text=Send Reminder')).toBeVisible()
  })

  test('should send reminder when button clicked', async ({ page }) => {
    // Select signature request
    await page.click('text=Purchase Agreement - 123 Main St')
    
    // Click send reminder
    await page.click('text=Send Reminder')
    
    // Check for success toast
    await expect(page.locator('text=Reminder Sent')).toBeVisible()
    await expect(page.locator('text=A reminder email has been sent to the signer')).toBeVisible()
  })

  test('should display action buttons', async ({ page }) => {
    // Select signature request
    await page.click('text=Purchase Agreement - 123 Main St')
    
    // Check action buttons
    await expect(page.locator('text=Resend Document')).toBeVisible()
    await expect(page.locator('text=Download Audit Trail')).toBeVisible()
    await expect(page.locator('text=View Document')).toBeVisible()
  })

  test('should resend document when button clicked', async ({ page }) => {
    // Select signature request
    await page.click('text=Purchase Agreement - 123 Main St')
    
    // Click resend document
    await page.click('text=Resend Document')
    
    // Check for success toast
    await expect(page.locator('text=Document Resent')).toBeVisible()
    await expect(page.locator('text=The signature request has been resent to all pending parties')).toBeVisible()
  })

  test('should show placeholder when no request selected', async ({ page }) => {
    // Check default state
    await expect(page.locator('text=Select a signature request to view details')).toBeVisible()
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    
    await expect(page.locator('h1')).toContainText('Signature Tracker')
    await expect(page.locator('text=Signature Requests')).toBeVisible()
    await expect(page.locator('text=Purchase Agreement - 123 Main St')).toBeVisible()
  })

  test('should display help button with signature context', async ({ page }) => {
    const helpButton = page.locator('button[title="Get AI Help"]')
    await expect(helpButton).toBeVisible()
    
    await helpButton.click()
    await expect(page.locator('text=AI Contract Assistant')).toBeVisible()
    
    // Close modal
    await page.click('button:has-text("✕")')
  })

  test('should maintain selection across interactions', async ({ page }) => {
    // Select first request
    await page.click('text=Purchase Agreement - 123 Main St')
    await expect(page.locator('text=Request Details')).toBeVisible()
    
    // Send reminder
    await page.click('text=Send Reminder')
    await expect(page.locator('text=Reminder Sent')).toBeVisible()
    
    // Selection should still be active
    await expect(page.locator('text=Request Details')).toBeVisible()
    await expect(page.locator('text=Purchase Agreement - 123 Main St')).toBeVisible()
  })
})
