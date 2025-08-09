import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeToggle } from '../ui/theme-toggle'

// Mock next-themes
jest.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: jest.fn(),
    resolvedTheme: 'light',
    themes: ['light', 'dark'],
    systemTheme: 'light',
  }),
}))

describe('ThemeToggle', () => {
  it('renders theme toggle button', () => {
    render(<ThemeToggle />)
    
    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
  })

  it('has accessible label', () => {
    render(<ThemeToggle />)
    
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Toggle theme')
  })
})
