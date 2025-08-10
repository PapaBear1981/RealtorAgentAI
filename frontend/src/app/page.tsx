import { LandingPage } from "@/components/landing/LandingPage"
import { AnimationProvider } from "@/components/landing/animations/AnimationProvider"

export default function HomePage() {
  return (
    <AnimationProvider>
      <LandingPage />
    </AnimationProvider>
  )
}
