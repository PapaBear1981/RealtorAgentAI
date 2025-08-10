"use client"

import { AboutContactSection } from "./AboutContactSection"
import { BenefitsSection } from "./BenefitsSection"
import { FeaturesSection } from "./FeaturesSection"
import { HeroSection } from "./HeroSection"
import { LandingNavigation } from "./LandingNavigation"
import { SocialProofSection } from "./SocialProofSection"
import { TechnologySection } from "./TechnologySection"

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Landing Navigation */}
      <LandingNavigation />

      {/* Hero Section */}
      <HeroSection />

      {/* Features Section */}
      <FeaturesSection />

      {/* Benefits Section */}
      <BenefitsSection />

      {/* Technology Section */}
      <TechnologySection />

      {/* Social Proof Section */}
      <SocialProofSection />

      {/* About & Contact Section */}
      <AboutContactSection />
    </div>
  )
}
