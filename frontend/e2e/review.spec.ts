import { expect, test } from '@playwright/test'

test.describe('Contract Review', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')

    // Navigate to review page
    await page.goto('/review')
  })

  test('should display review interface', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Contract Review')
    await expect(page.locator('text=Review changes, add comments, and approve contract versions')).toBeVisible()

    // Check keyboard shortcuts hint
    await expect(page.locator('text=Keyboard: A = Approve, R = Request Changes')).toBeVisible()
  })

  test('should display review tabs', async ({ page }) => {
    await expect(page.locator('text=Redline View')).toBeVisible()
    await expect(page.locator('text=Version History')).toBeVisible()
    await expect(page.locator('text=All Comments')).toBeVisible()
  })

  test('should display current version information', async ({ page }) => {
    await expect(page.locator('text=Version 2: Updated Purchase Price')).toBeVisible()
    await expect(page.locator('text=By Jane Doe')).toBeVisible()
    await expect(page.locator('text=review')).toBeVisible() // Status badge
  })

  test('should display contract with changes highlighted', async ({ page }) => {
    // Check for contract content
    await expect(page.locator('text=RESIDENTIAL PURCHASE AGREEMENT')).toBeVisible()
    await expect(page.locator('text=John Smith')).toBeVisible()
    await expect(page.locator('text=Jane Doe')).toBeVisible()
    await expect(page.locator('text=$365,000')).toBeVisible() // Updated price

    // Check for change indicators
    await expect(page.locator('.bg-green-100')).toBeVisible() // Addition highlighting
  })

  test('should display line numbers', async ({ page }) => {
    // Check that line numbers are visible
    const lineNumbers = page.locator('.text-xs.text-gray-400.w-8')
    await expect(lineNumbers.first()).toBeVisible()
  })

  test('should display comments on lines', async ({ page }) => {
    // Check for existing comments
    await expect(page.locator('text=The price increase looks reasonable')).toBeVisible()
    await expect(page.locator('text=Mike Johnson')).toBeVisible()
    await expect(page.locator('text=Should we specify which home warranty company?')).toBeVisible()
    await expect(page.locator('text=Sarah Wilson')).toBeVisible()
  })

  test('should display comment replies', async ({ page }) => {
    // Check for comment replies
    await expect(page.locator('text=Agreed. The appraisal supports this value.')).toBeVisible()
    await expect(page.locator('text=John Smith')).toBeVisible()
  })

  test('should allow selecting lines for comments', async ({ page }) => {
    // Click on a line to select it
    await page.click('.group.relative:first-child')

    // Check that add comment section shows line selection
    await expect(page.locator('text=Comment on line')).toBeVisible()
  })

  test('should add new comments', async ({ page }) => {
    // Select a line
    await page.click('.group.relative:first-child')

    // Add comment
    await page.fill('textarea[placeholder="Enter your comment..."]', 'This is a test comment')
    await page.click('text=Add Comment')

    // Check for success toast
    await expect(page.locator('text=Comment Added')).toBeVisible()
    await expect(page.locator('text=Your comment has been added to the review')).toBeVisible()
  })

  test('should clear line selection', async ({ page }) => {
    // Select a line
    await page.click('.group.relative:first-child')
    await expect(page.locator('text=Comment on line')).toBeVisible()

    // Clear selection
    await page.click('text=Clear line selection')
    await expect(page.locator('text=General comment')).toBeVisible()
  })

  test('should display version history', async ({ page }) => {
    // Switch to version history tab
    await page.click('text=Version History')

    // Check version list
    await expect(page.locator('text=Version 1: Initial Draft')).toBeVisible()
    await expect(page.locator('text=Version 2: Updated Purchase Price')).toBeVisible()
    await expect(page.locator('text=approved')).toBeVisible()
    await expect(page.locator('text=review')).toBeVisible()
  })

  test('should switch between versions', async ({ page }) => {
    // Switch to version history tab
    await page.click('text=Version History')

    // Select different version
    await page.click('text=Version 1: Initial Draft')

    // Should update the main view
    await page.click('text=Redline View')
    // Version 1 should now be selected (would need to check for different content)
  })

  test('should display all comments tab', async ({ page }) => {
    // Switch to all comments tab
    await page.click('text=All Comments')

    // Check comments list
    await expect(page.locator('text=All Comments')).toBeVisible()
    await expect(page.locator('text=Review and respond to all comments on this contract')).toBeVisible()

    // Check individual comments
    await expect(page.locator('text=The price increase looks reasonable')).toBeVisible()
    await expect(page.locator('text=Should we specify which home warranty company?')).toBeVisible()
  })

  test('should display review summary', async ({ page }) => {
    // Check summary panel
    await expect(page.locator('text=Review Summary')).toBeVisible()
    await expect(page.locator('text=Total Comments:')).toBeVisible()
    await expect(page.locator('text=Unresolved:')).toBeVisible()
    await expect(page.locator('text=Changes:')).toBeVisible()
    await expect(page.locator('text=Status:')).toBeVisible()
  })

  test('should approve version with keyboard shortcut', async ({ page }) => {
    // Press 'A' key for approve
    await page.keyboard.press('a')

    // Check for approval toast
    await expect(page.locator('text=Version Approved')).toBeVisible()
    await expect(page.locator('text=The contract version has been approved successfully')).toBeVisible()
  })

  test('should request changes with keyboard shortcut', async ({ page }) => {
    // Press 'R' key for request changes
    await page.keyboard.press('r')

    // Check for request changes toast
    await expect(page.locator('text=Changes Requested')).toBeVisible()
    await expect(page.locator('text=Change request has been sent to the author')).toBeVisible()
  })

  test('should approve version with button', async ({ page }) => {
    // Click approve button
    await page.click('text=Approve')

    // Check for approval toast
    await expect(page.locator('text=Version Approved')).toBeVisible()
  })

  test('should request changes with button', async ({ page }) => {
    // Click request changes button
    await page.click('text=Request Changes')

    // Check for request changes toast
    await expect(page.locator('text=Changes Requested')).toBeVisible()
  })

  test('should display keyboard shortcut indicators on buttons', async ({ page }) => {
    // Check that buttons show keyboard shortcuts
    await expect(page.locator('kbd:has-text("A")')).toBeVisible()
    await expect(page.locator('kbd:has-text("R")')).toBeVisible()
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })

    await expect(page.locator('h1')).toContainText('Contract Review')
    await expect(page.locator('text=Redline View')).toBeVisible()
    await expect(page.locator('text=Version 2: Updated Purchase Price')).toBeVisible()
  })

  test('should display help button with review context', async ({ page }) => {
    const helpButton = page.locator('button[title="Get AI Help"]')
    await expect(helpButton).toBeVisible()

    await helpButton.click()
    await expect(page.locator('text=AI Contract Assistant')).toBeVisible()

    // Close modal
    await page.click('button:has-text("✕")')
  })
})
