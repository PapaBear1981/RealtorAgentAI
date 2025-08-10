"use client"

import { motion } from "framer-motion"
import { FeaturesSection } from "./FeaturesSection"
import { HeroSection } from "./HeroSection"
import { LandingNavigation } from "./LandingNavigation"

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Landing Navigation */}
      <LandingNavigation />

      {/* Hero Section */}
      <HeroSection />

      {/* Features Section */}
      <FeaturesSection />

      {/* Future sections will be added here */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 1.2 }}
        className="min-h-screen flex items-center justify-center"
      >
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-muted-foreground">
            More sections coming soon...
          </h2>
          <p className="text-sm text-muted-foreground mt-2">
            Benefits, Technology Stack, Testimonials, and more
          </p>
        </div>
      </motion.div>
    </div>
  )
}
