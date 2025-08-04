import { AuthInitializer } from "@/components/auth/AuthInitializer"
import { AuthenticatedAssistantAgent } from "@/components/help/AuthenticatedAssistantAgent"
import { Toaster } from "@/components/ui/toaster"
import { CommandPalette } from "@/components/ui/command-palette"
import "@/styles/globals.css"
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
          {children}
          <AuthenticatedAssistantAgent />
          <Toaster />
          <CommandPalette />
        </div>
      </body>
    </html>
  )
}
