import { fireEvent, render, screen } from '@testing-library/react'
import { ThemeToggle } from '../ui/theme-toggle'

// Mock next-themes with a spy function we can track
const mockSetTheme = jest.fn()

jest.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: mockSetTheme,
    resolvedTheme: 'light',
    themes: ['light', 'dark'],
    systemTheme: 'light',
  }),
}))

describe('ThemeToggle', () => {
  beforeEach(() => {
    // Clear the mock calls before each test
    mockSetTheme.mockClear()
  })

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

  it('calls setTheme when clicked', () => {
    render(<ThemeToggle />)

    const button = screen.getByRole('button')
    fireEvent.click(button)

    // Should call setTheme when clicked
    expect(mockSetTheme).toHaveBeenCalledTimes(1)
    // The actual theme value depends on the component's logic
    expect(mockSetTheme).toHaveBeenCalled()
  })
})
