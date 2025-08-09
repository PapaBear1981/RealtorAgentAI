import { expect, test } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
  })

  test('should display dashboard with all widgets', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Dashboard')
    await expect(page.locator('text=Overview of your real estate contracts and activities')).toBeVisible()

    // Check all widgets are present
    await expect(page.locator('text=My Deals')).toBeVisible()
    await expect(page.locator('text=Pending Signatures')).toBeVisible()
    await expect(page.locator('text=Compliance Alerts')).toBeVisible()
    await expect(page.locator('text=Recent Uploads')).toBeVisible()

    // Intercept analytics API calls to verify real data integration
    let analyticsApiCalled = false

    page.route('**/analytics/dashboard/overview*', async route => {
      analyticsApiCalled = true
      await route.continue()
    })

    // Wait for API call to complete
    await page.waitForTimeout(1000)

    // Verify real API call was made (not mock data)
    expect(analyticsApiCalled).toBe(true)

    // Check that widget values are dynamic (not hardcoded mock values)
    // The exact values will depend on seeded database data
    const dealCount = await page.locator('[data-testid="deals-count"]').textContent()
    const signatureCount = await page.locator('[data-testid="signatures-count"]').textContent()
    const alertCount = await page.locator('[data-testid="alerts-count"]').textContent()
    const uploadCount = await page.locator('[data-testid="uploads-count"]').textContent()

    // Verify values are numbers (not mock text)
    expect(dealCount).toMatch(/^\d+$/)
    expect(signatureCount).toMatch(/^\d+$/)
    expect(alertCount).toMatch(/^\d+$/)
    expect(uploadCount).toMatch(/^\d+$/)
  })

  test('should display quick action cards', async ({ page }) => {
    await expect(page.locator('text=Document Intake')).toBeVisible()
    await expect(page.locator('text=Upload and process real estate documents')).toBeVisible()

    await expect(page.locator('text=Contract Generator')).toBeVisible()
    await expect(page.locator('text=Generate contracts from templates')).toBeVisible()

    await expect(page.locator('text=Signature Tracker')).toBeVisible()
    await expect(page.locator('text=Track multi-party signatures')).toBeVisible()
  })

  test('should navigate to documents page from quick action', async ({ page }) => {
    await page.click('text=Upload Documents')
    await expect(page).toHaveURL('/documents')
    await expect(page.locator('h1')).toContainText('Document Intake')
  })

  test('should navigate to contracts page from quick action', async ({ page }) => {
    await page.click('text=Create Contract')
    await expect(page).toHaveURL('/contracts')
    await expect(page.locator('h1')).toContainText('Contract Generator')
  })

  test('should navigate to signatures page from quick action', async ({ page }) => {
    await page.click('text=View Signatures')
    await expect(page).toHaveURL('/signatures')
    await expect(page.locator('h1')).toContainText('Signature Tracker')
  })

  test('should display navigation with all menu items', async ({ page }) => {
    await expect(page.locator('text=Dashboard')).toBeVisible()
    await expect(page.locator('text=Documents')).toBeVisible()
    await expect(page.locator('text=Contracts')).toBeVisible()
    await expect(page.locator('text=Signatures')).toBeVisible()
    await expect(page.locator('text=Admin')).toBeVisible() // Admin user sees admin menu
  })

  test('should navigate between pages using navigation menu', async ({ page }) => {
    // Navigate to Documents
    await page.click('nav >> text=Documents')
    await expect(page).toHaveURL('/documents')
    await expect(page.locator('h1')).toContainText('Document Intake')

    // Navigate to Contracts
    await page.click('nav >> text=Contracts')
    await expect(page).toHaveURL('/contracts')
    await expect(page.locator('h1')).toContainText('Contract Generator')

    // Navigate to Signatures
    await page.click('nav >> text=Signatures')
    await expect(page).toHaveURL('/signatures')
    await expect(page.locator('h1')).toContainText('Signature Tracker')

    // Navigate back to Dashboard
    await page.click('nav >> text=Dashboard')
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('h1')).toContainText('Dashboard')
  })

  test('should display user information in header', async ({ page }) => {
    await expect(page.locator('text=Welcome, Admin User')).toBeVisible()
    await expect(page.locator('text=admin')).toBeVisible() // Role badge
    await expect(page.locator('text=Logout')).toBeVisible()
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })

    // Check that widgets stack properly on mobile
    await expect(page.locator('text=My Deals')).toBeVisible()
    await expect(page.locator('text=Pending Signatures')).toBeVisible()
    await expect(page.locator('text=Compliance Alerts')).toBeVisible()
    await expect(page.locator('text=Recent Uploads')).toBeVisible()

    // Check that quick actions are still accessible
    await expect(page.locator('text=Document Intake')).toBeVisible()
    await expect(page.locator('text=Contract Generator')).toBeVisible()
    await expect(page.locator('text=Signature Tracker')).toBeVisible()
  })

  test('should display help button', async ({ page }) => {
    // Check for floating help button
    const helpButton = page.locator('button[title="Get AI Help"]')
    await expect(helpButton).toBeVisible()

    // Click help button to open modal
    await helpButton.click()
    await expect(page.locator('text=AI Contract Assistant')).toBeVisible()
    await expect(page.locator('text=Dashboard')).toBeVisible() // Context badge

    // Close modal
    await page.click('button:has-text("✕")')
    await expect(page.locator('text=AI Contract Assistant')).not.toBeVisible()
  })
})
