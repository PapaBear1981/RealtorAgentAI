import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Define protected and public routes
const protectedRoutes = ['/dashboard']
const publicRoutes = ['/login', '/']

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname
  const isProtectedRoute = protectedRoutes.some(route => path.startsWith(route))
  const isPublicRoute = publicRoutes.includes(path)

  // For now, we'll use a simple cookie-based check
  // In a real app, you'd decrypt and verify the session token
  const sessionCookie = request.cookies.get('auth-storage')?.value

  // Check if user has a session (simplified check)
  let hasValidSession = false
  if (sessionCookie) {
    try {
      const sessionData = JSON.parse(sessionCookie)
      hasValidSession = sessionData.state?.isAuthenticated === true && sessionData.state?.token
    } catch (error) {
      // Invalid session data
      hasValidSession = false
    }
  }

  // Redirect to login if accessing protected route without session
  if (isProtectedRoute && !hasValidSession) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Redirect to dashboard if accessing login while authenticated
  if (path === '/login' && hasValidSession) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

// Configure which routes the middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
