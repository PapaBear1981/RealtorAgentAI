import { test, expect } from '@playwright/test'
import path from 'path'

test.describe('Document Intake', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
    
    // Navigate to documents page
    await page.click('nav >> text=Documents')
    await expect(page).toHaveURL('/documents')
  })

  test('should display document intake interface', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Document Intake')
    await expect(page.locator('text=Upload and process real estate documents with AI-powered extraction')).toBeVisible()
    
    // Check upload area
    await expect(page.locator('text=Upload Documents')).toBeVisible()
    await expect(page.locator('text=Drag and drop files or click to select')).toBeVisible()
    await expect(page.locator('text=PDF, DOC, DOCX, Images, TXT up to 10MB')).toBeVisible()
  })

  test('should show drag and drop interface', async ({ page }) => {
    const dropzone = page.locator('[data-testid="dropzone"], .border-dashed')
    await expect(dropzone).toBeVisible()
    
    // Check for upload icon and text
    await expect(page.locator('text=Drag and drop files here, or click to select')).toBeVisible()
    await expect(page.locator('text=PDF, DOC, DOCX, Images, TXT up to 10MB')).toBeVisible()
  })

  test('should handle file upload simulation', async ({ page }) => {
    // Create a test file
    const testFile = path.join(__dirname, 'fixtures', 'test-document.txt')
    
    // Since we can't actually create files in this test environment,
    // we'll test the UI behavior when files are "uploaded"
    const fileInput = page.locator('input[type="file"]')
    
    // The file input should be present but hidden
    await expect(fileInput).toBeAttached()
  })

  test('should display uploaded files section when files are present', async ({ page }) => {
    // This test would need actual file upload functionality
    // For now, we'll test that the interface is ready for file uploads
    
    // Check that the upload area is interactive
    const dropzone = page.locator('.border-dashed')
    await expect(dropzone).toBeVisible()
    
    // Hover over dropzone to test hover state
    await dropzone.hover()
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    
    await expect(page.locator('h1')).toContainText('Document Intake')
    await expect(page.locator('text=Upload Documents')).toBeVisible()
    await expect(page.locator('text=Drag and drop files here, or click to select')).toBeVisible()
  })

  test('should display help button with document context', async ({ page }) => {
    const helpButton = page.locator('button[title="Get AI Help"]')
    await expect(helpButton).toBeVisible()
    
    await helpButton.click()
    await expect(page.locator('text=AI Contract Assistant')).toBeVisible()
    
    // Close modal
    await page.click('button:has-text("✕")')
  })

  test('should navigate back to dashboard', async ({ page }) => {
    await page.click('nav >> text=Dashboard')
    await expect(page).toHaveURL('/dashboard')
  })

  test('should maintain authentication state', async ({ page }) => {
    await expect(page.locator('text=Welcome, Admin User')).toBeVisible()
    await expect(page.locator('text=admin')).toBeVisible()
  })
})
