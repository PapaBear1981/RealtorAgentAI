import { AuthInitializer } from "@/components/auth/AuthInitializer"
import { AuthenticatedAssistantAgent } from "@/components/help/AuthenticatedAssistantAgent"
import { LanguageToggle } from "@/components/LanguageToggle"
import { Toaster } from "@/components/ui/toaster"
import "@/styles/globals.css"
import "@/lib/i18n"
import type { Metadata } from "next"
import { Inter } from "next/font/google"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "RealtorAgentAI - Real Estate Contract Platform",
  description: "Multi-Agent Real Estate Contract Platform for automated document processing, contract generation, and signature tracking.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <div className="min-h-screen bg-background font-sans antialiased">
          <AuthInitializer />
          <div className="absolute top-4 right-4">
            <LanguageToggle />
          </div>
          {children}
          <AuthenticatedAssistantAgent />
          <Toaster />
        </div>
      </body>
    </html>
  )
}
