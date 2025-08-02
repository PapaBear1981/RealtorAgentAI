import { test, expect } from '@playwright/test'

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin before each test
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
    
    // Navigate to admin page
    await page.click('nav >> text=Admin')
    await expect(page).toHaveURL('/admin')
  })

  test('should display admin panel interface', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Admin Panel')
    await expect(page.locator('text=Manage users, templates, system configuration, and audit trails')).toBeVisible()
  })

  test('should display admin tabs', async ({ page }) => {
    await expect(page.locator('text=User Management')).toBeVisible()
    await expect(page.locator('text=Templates')).toBeVisible()
    await expect(page.locator('text=System Config')).toBeVisible()
    await expect(page.locator('text=Audit Logs')).toBeVisible()
  })

  test('should display user management by default', async ({ page }) => {
    await expect(page.locator('text=Users (3)')).toBeVisible()
    await expect(page.locator('text=Manage user accounts and permissions')).toBeVisible()
    
    // Check for mock users
    await expect(page.locator('text=John Smith')).toBeVisible()
    await expect(page.locator('text=john.smith@realty.com')).toBeVisible()
    await expect(page.locator('text=Jane Doe')).toBeVisible()
    await expect(page.locator('text=jane.doe@realty.com')).toBeVisible()
    await expect(page.locator('text=Mike Johnson')).toBeVisible()
    await expect(page.locator('text=mike.johnson@realty.com')).toBeVisible()
  })

  test('should display user roles and status', async ({ page }) => {
    // Check for role badges
    await expect(page.locator('text=agent')).toBeVisible()
    await expect(page.locator('text=tc')).toBeVisible()
    
    // Check for status badges
    await expect(page.locator('text=active')).toBeVisible()
  })

  test('should select user and show details', async ({ page }) => {
    // Click on first user
    await page.click('text=John Smith')
    
    // Check details panel
    await expect(page.locator('text=User Details')).toBeVisible()
    await expect(page.locator('text=John Smith')).toBeVisible()
    
    // Check form fields
    await expect(page.locator('label:has-text("Name")')).toBeVisible()
    await expect(page.locator('label:has-text("Email")')).toBeVisible()
    await expect(page.locator('label:has-text("Role")')).toBeVisible()
    await expect(page.locator('label:has-text("Status")')).toBeVisible()
    await expect(page.locator('label:has-text("Created")')).toBeVisible()
  })

  test('should toggle user status', async ({ page }) => {
    // Click deactivate button for first user
    await page.click('text=Deactivate')
    
    // Check for success toast
    await expect(page.locator('text=User Status Updated')).toBeVisible()
    await expect(page.locator('text=User status has been changed successfully')).toBeVisible()
  })

  test('should display templates tab', async ({ page }) => {
    // Switch to templates tab
    await page.click('text=Templates')
    
    await expect(page.locator('text=Contract Templates (2)')).toBeVisible()
    await expect(page.locator('text=Manage contract templates and versions')).toBeVisible()
    
    // Check for mock templates
    await expect(page.locator('text=Residential Purchase Agreement')).toBeVisible()
    await expect(page.locator('text=Version 2.1')).toBeVisible()
    await expect(page.locator('text=Listing Agreement')).toBeVisible()
    await expect(page.locator('text=Version 1.8')).toBeVisible()
  })

  test('should display template information', async ({ page }) => {
    // Switch to templates tab
    await page.click('text=Templates')
    
    // Check template details
    await expect(page.locator('text=Purchase')).toBeVisible() // Category
    await expect(page.locator('text=Used 45 times')).toBeVisible()
    await expect(page.locator('text=Used 32 times')).toBeVisible()
    await expect(page.locator('text=Admin User')).toBeVisible() // Author
  })

  test('should change template status', async ({ page }) => {
    // Switch to templates tab
    await page.click('text=Templates')
    
    // Change status of first template
    await page.click('button:has-text("Active")')
    await page.click('text=Draft')
    
    // Check for success toast
    await expect(page.locator('text=Template Status Updated')).toBeVisible()
    await expect(page.locator('text=Template status has been changed successfully')).toBeVisible()
  })

  test('should display system configuration', async ({ page }) => {
    // Switch to system config tab
    await page.click('text=System Config')
    
    // Check AI model configuration
    await expect(page.locator('text=AI Model Configuration')).toBeVisible()
    await expect(page.locator('text=Configure AI model routing and settings')).toBeVisible()
    await expect(page.locator('label:has-text("Primary Model")')).toBeVisible()
    await expect(page.locator('label:has-text("Fallback Model")')).toBeVisible()
    await expect(page.locator('label:has-text("Token Limit")')).toBeVisible()
    
    // Check system settings
    await expect(page.locator('text=System Settings')).toBeVisible()
    await expect(page.locator('text=General system configuration')).toBeVisible()
    await expect(page.locator('label:has-text("Max File Size (MB)")')).toBeVisible()
    await expect(page.locator('label:has-text("Session Timeout (hours)")')).toBeVisible()
    await expect(page.locator('label:has-text("Backup Retention (days)")')).toBeVisible()
  })

  test('should display audit logs', async ({ page }) => {
    // Switch to audit logs tab
    await page.click('text=Audit Logs')
    
    await expect(page.locator('text=Audit Trail (2)')).toBeVisible()
    await expect(page.locator('text=System activity and security audit logs')).toBeVisible()
    
    // Check for mock audit entries
    await expect(page.locator('text=CONTRACT_GENERATED')).toBeVisible()
    await expect(page.locator('text=DOCUMENT_UPLOADED')).toBeVisible()
    await expect(page.locator('text=john.smith@realty.com')).toBeVisible()
    await expect(page.locator('text=jane.doe@realty.com')).toBeVisible()
  })

  test('should display audit log details', async ({ page }) => {
    // Switch to audit logs tab
    await page.click('text=Audit Logs')
    
    // Check audit log details
    await expect(page.locator('text=Purchase Agreement - 123 Main St')).toBeVisible()
    await expect(page.locator('text=Generated contract from template')).toBeVisible()
    await expect(page.locator('text=Property Disclosure.pdf')).toBeVisible()
    await expect(page.locator('text=Uploaded document for processing')).toBeVisible()
    await expect(page.locator('text=IP: 192.168.1.100')).toBeVisible()
    await expect(page.locator('text=IP: 192.168.1.101')).toBeVisible()
  })

  test('should save configuration changes', async ({ page }) => {
    // Switch to system config tab
    await page.click('text=System Config')
    
    // Click save configuration
    await page.click('text=Save Configuration')
    
    // Should show some feedback (in a real app, this would show a toast)
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    
    await expect(page.locator('h1')).toContainText('Admin Panel')
    await expect(page.locator('text=User Management')).toBeVisible()
    await expect(page.locator('text=John Smith')).toBeVisible()
  })

  test('should display help button with admin context', async ({ page }) => {
    const helpButton = page.locator('button[title="Get AI Help"]')
    await expect(helpButton).toBeVisible()
    
    await helpButton.click()
    await expect(page.locator('text=AI Contract Assistant')).toBeVisible()
    
    // Close modal
    await page.click('button:has-text("✕")')
  })

  test('should show placeholder when no user selected', async ({ page }) => {
    // Check default state (no user selected initially)
    await expect(page.locator('text=Select a user to view details')).toBeVisible()
  })

  test('should maintain tab state during interactions', async ({ page }) => {
    // Switch to templates tab
    await page.click('text=Templates')
    await expect(page.locator('text=Contract Templates')).toBeVisible()
    
    // Change template status
    await page.click('button:has-text("Active")')
    await page.click('text=Draft')
    
    // Should still be on templates tab
    await expect(page.locator('text=Contract Templates')).toBeVisible()
  })
})
