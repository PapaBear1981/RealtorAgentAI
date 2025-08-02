import { test, expect } from '@playwright/test'

test.describe('Contract Generator', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
    
    // Navigate to contracts page
    await page.click('nav >> text=Contracts')
    await expect(page).toHaveURL('/contracts')
  })

  test('should display contract generator interface', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Contract Generator')
    await expect(page.locator('text=Generate standardized contracts from templates and extracted data')).toBeVisible()
    
    // Check tabs
    await expect(page.locator('text=Select Template')).toBeVisible()
    await expect(page.locator('text=Fill Variables')).toBeVisible()
    await expect(page.locator('text=Preview & Generate')).toBeVisible()
  })

  test('should display template selection', async ({ page }) => {
    await expect(page.locator('text=Choose Contract Template')).toBeVisible()
    await expect(page.locator('text=Select from our library of standardized real estate contract templates')).toBeVisible()
    
    // Check for templates
    await expect(page.locator('text=Residential Purchase Agreement')).toBeVisible()
    await expect(page.locator('text=Standard residential real estate purchase agreement')).toBeVisible()
    await expect(page.locator('text=Exclusive Listing Agreement')).toBeVisible()
    await expect(page.locator('text=Exclusive right to sell listing agreement')).toBeVisible()
  })

  test('should select template and navigate to variables tab', async ({ page }) => {
    // Select Purchase Agreement template
    await page.click('text=Residential Purchase Agreement')
    
    // Should automatically switch to Fill Variables tab
    await expect(page.locator('[data-state="active"]:has-text("Fill Variables")')).toBeVisible()
    await expect(page.locator('text=Fill Contract Variables')).toBeVisible()
    await expect(page.locator('text=Complete the required information for: Residential Purchase Agreement')).toBeVisible()
  })

  test('should display form fields for selected template', async ({ page }) => {
    // Select template first
    await page.click('text=Residential Purchase Agreement')
    
    // Check form fields
    await expect(page.locator('label:has-text("Buyer Name")')).toBeVisible()
    await expect(page.locator('label:has-text("Seller Name")')).toBeVisible()
    await expect(page.locator('label:has-text("Property Address")')).toBeVisible()
    await expect(page.locator('label:has-text("Purchase Price")')).toBeVisible()
    await expect(page.locator('label:has-text("Closing Date")')).toBeVisible()
    await expect(page.locator('label:has-text("Earnest Money")')).toBeVisible()
    await expect(page.locator('label:has-text("Financing Type")')).toBeVisible()
  })

  test('should fill form and generate contract', async ({ page }) => {
    // Select template
    await page.click('text=Residential Purchase Agreement')
    
    // Fill form fields
    await page.fill('input[placeholder="John Smith"]', 'John Smith')
    await page.fill('input[placeholder="Jane Doe"]', 'Jane Doe')
    await page.fill('textarea[placeholder="123 Main St, Anytown, ST 12345"]', '123 Main St, Anytown, ST 12345')
    await page.fill('input[placeholder="350000"]', '350000')
    await page.fill('input[type="date"]', '2024-03-15')
    await page.fill('input[placeholder="5000"]', '5000')
    
    // Select financing type
    await page.click('button:has-text("Select an option")')
    await page.click('text=Conventional')
    
    // Generate contract
    await page.click('text=Generate Contract')
    
    // Should switch to preview tab
    await expect(page.locator('[data-state="active"]:has-text("Preview & Generate")')).toBeVisible()
    await expect(page.locator('text=Generated Contract')).toBeVisible()
  })

  test('should validate required fields', async ({ page }) => {
    // Select template
    await page.click('text=Residential Purchase Agreement')
    
    // Try to generate without filling required fields
    const generateButton = page.locator('text=Generate Contract')
    await expect(generateButton).toBeDisabled()
    
    // Fill one field
    await page.fill('input[placeholder="John Smith"]', 'John Smith')
    await expect(generateButton).toBeDisabled()
    
    // Fill all required fields
    await page.fill('input[placeholder="Jane Doe"]', 'Jane Doe')
    await page.fill('textarea[placeholder="123 Main St, Anytown, ST 12345"]', '123 Main St, Anytown, ST 12345')
    await page.fill('input[placeholder="350000"]', '350000')
    await page.fill('input[type="date"]', '2024-03-15')
    await page.fill('input[placeholder="5000"]', '5000')
    await page.click('button:has-text("Select an option")')
    await page.click('text=Conventional')
    
    await expect(generateButton).toBeEnabled()
  })

  test('should display contract preview', async ({ page }) => {
    // Select template and fill form
    await page.click('text=Residential Purchase Agreement')
    await page.fill('input[placeholder="John Smith"]', 'John Smith')
    await page.fill('input[placeholder="Jane Doe"]', 'Jane Doe')
    await page.fill('textarea[placeholder="123 Main St, Anytown, ST 12345"]', '123 Main St, Anytown, ST 12345')
    await page.fill('input[placeholder="350000"]', '350000')
    await page.fill('input[type="date"]', '2024-03-15')
    await page.fill('input[placeholder="5000"]', '5000')
    await page.click('button:has-text("Select an option")')
    await page.click('text=Conventional')
    
    // Generate contract
    await page.click('text=Generate Contract')
    
    // Check preview content
    await expect(page.locator('text=RESIDENTIAL PURCHASE AGREEMENT')).toBeVisible()
    await expect(page.locator('text=John Smith')).toBeVisible()
    await expect(page.locator('text=Jane Doe')).toBeVisible()
    await expect(page.locator('text=123 Main St, Anytown, ST 12345')).toBeVisible()
    await expect(page.locator('text=$350000')).toBeVisible()
  })

  test('should allow editing variables from preview', async ({ page }) => {
    // Generate a contract first
    await page.click('text=Residential Purchase Agreement')
    await page.fill('input[placeholder="John Smith"]', 'John Smith')
    await page.fill('input[placeholder="Jane Doe"]', 'Jane Doe')
    await page.fill('textarea[placeholder="123 Main St, Anytown, ST 12345"]', '123 Main St, Anytown, ST 12345')
    await page.fill('input[placeholder="350000"]', '350000')
    await page.fill('input[type="date"]', '2024-03-15')
    await page.fill('input[placeholder="5000"]', '5000')
    await page.click('button:has-text("Select an option")')
    await page.click('text=Conventional')
    await page.click('text=Generate Contract')
    
    // Click edit variables
    await page.click('text=Edit Variables')
    
    // Should return to variables tab
    await expect(page.locator('[data-state="active"]:has-text("Fill Variables")')).toBeVisible()
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    
    await expect(page.locator('h1')).toContainText('Contract Generator')
    await expect(page.locator('text=Select Template')).toBeVisible()
    await expect(page.locator('text=Residential Purchase Agreement')).toBeVisible()
  })

  test('should display help button with contract context', async ({ page }) => {
    const helpButton = page.locator('button[title="Get AI Help"]')
    await expect(helpButton).toBeVisible()
    
    await helpButton.click()
    await expect(page.locator('text=AI Contract Assistant')).toBeVisible()
    
    // Close modal
    await page.click('button:has-text("✕")')
  })
})
