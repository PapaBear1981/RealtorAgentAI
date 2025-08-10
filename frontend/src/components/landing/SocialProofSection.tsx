"use client"

import { motion } from "framer-motion"
import { 
  Shield, 
  Award, 
  CheckCircle, 
  Star, 
  Users, 
  TrendingUp,
  Lock,
  Globe,
  Zap,
  Building
} from "lucide-react"
import { AnimatedSection, StaggeredContainer, StaggeredItem, HoverAnimation } from "./animations/AnimatedSection"

export function SocialProofSection() {
  const certifications = [
    {
      name: "SOC 2 Type II",
      description: "Security, availability, and confidentiality",
      icon: Shield,
      gradient: "from-blue-500 to-cyan-500"
    },
    {
      name: "GDPR Compliant",
      description: "European data protection standards",
      icon: Lock,
      gradient: "from-green-500 to-emerald-500"
    },
    {
      name: "ISO 27001",
      description: "Information security management",
      icon: Award,
      gradient: "from-purple-500 to-pink-500"
    },
    {
      name: "CCPA Compliant",
      description: "California consumer privacy act",
      icon: CheckCircle,
      gradient: "from-orange-500 to-red-500"
    }
  ]

  const trustIndicators = [
    {
      icon: Users,
      value: "10,000+",
      label: "Active Users",
      description: "Real estate professionals trust our platform"
    },
    {
      icon: Building,
      value: "500+",
      label: "Agencies",
      description: "Real estate agencies using our solution"
    },
    {
      icon: TrendingUp,
      value: "99.9%",
      label: "Uptime",
      description: "Reliable service you can count on"
    },
    {
      icon: Star,
      value: "4.9/5",
      label: "User Rating",
      description: "Consistently high customer satisfaction"
    }
  ]

  const technologyPartners = [
    {
      name: "OpenAI",
      description: "Advanced AI language models",
      logo: "🤖",
      category: "AI Partner"
    },
    {
      name: "Anthropic",
      description: "Constitutional AI technology",
      logo: "🧠",
      category: "AI Partner"
    },
    {
      name: "Microsoft Azure",
      description: "Cloud infrastructure & security",
      logo: "☁️",
      category: "Cloud Partner"
    },
    {
      name: "AWS",
      description: "Scalable cloud services",
      logo: "🌐",
      category: "Cloud Partner"
    },
    {
      name: "Docker",
      description: "Containerization platform",
      logo: "🐳",
      category: "DevOps Partner"
    },
    {
      name: "PostgreSQL",
      description: "Enterprise database solution",
      logo: "🐘",
      category: "Database Partner"
    }
  ]

  const testimonials = [
    {
      quote: "RealtorAgentAI has transformed our workflow. We're processing contracts 80% faster and our compliance rate is perfect.",
      author: "Sarah Johnson",
      role: "Senior Real Estate Agent",
      company: "Premier Properties",
      rating: 5
    },
    {
      quote: "The AI agents handle all the tedious work, letting us focus on what matters - our clients. Game-changing technology.",
      author: "Michael Chen",
      role: "Transaction Coordinator",
      company: "Metro Realty Group",
      rating: 5
    },
    {
      quote: "Finally, a solution that understands real estate compliance. The multi-jurisdiction support is exactly what we needed.",
      author: "Lisa Rodriguez",
      role: "Compliance Officer",
      company: "Statewide Real Estate",
      rating: 5
    }
  ]

  return (
    <section className="py-24 bg-gradient-to-br from-background via-accent/5 to-background relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <AnimatedSection animation="fadeIn" className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center space-x-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-4 py-2 rounded-full text-sm font-medium mb-6"
          >
            <Shield className="w-4 h-4" />
            <span>Trusted & Secure</span>
          </motion.div>
          
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            <span className="bg-gradient-to-r from-blue-600 via-green-600 to-purple-600 bg-clip-text text-transparent">
              Trusted by Thousands
            </span>
          </h2>
          
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            Join the growing community of real estate professionals who trust our platform 
            with their most important business processes.
          </p>
        </AnimatedSection>

        {/* Trust Indicators */}
        <StaggeredContainer className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
          {trustIndicators.map((indicator, index) => (
            <StaggeredItem key={indicator.label}>
              <HoverAnimation>
                <div className="text-center bg-card border border-border/50 rounded-2xl p-6 backdrop-blur-sm">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r from-blue-500 to-purple-500 text-white mb-4 shadow-lg">
                    <indicator.icon className="w-8 h-8" />
                  </div>
                  
                  <div className="text-3xl font-bold text-foreground mb-2">
                    {indicator.value}
                  </div>
                  
                  <div className="text-lg font-semibold text-foreground mb-2">
                    {indicator.label}
                  </div>
                  
                  <p className="text-sm text-muted-foreground">
                    {indicator.description}
                  </p>
                </div>
              </HoverAnimation>
            </StaggeredItem>
          ))}
        </StaggeredContainer>

        {/* Security Certifications */}
        <div className="mb-16">
          <AnimatedSection animation="fadeIn" className="text-center mb-12">
            <h3 className="text-3xl font-bold text-foreground mb-4">
              Enterprise-Grade Security
            </h3>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Your data is protected by industry-leading security standards and certifications
            </p>
          </AnimatedSection>

          <StaggeredContainer className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {certifications.map((cert, index) => (
              <StaggeredItem key={cert.name}>
                <HoverAnimation>
                  <div className="bg-card border border-border/50 rounded-2xl p-6 text-center backdrop-blur-sm">
                    <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r ${cert.gradient} text-white mb-4 shadow-lg`}>
                      <cert.icon className="w-8 h-8" />
                    </div>
                    
                    <h4 className="text-lg font-bold text-foreground mb-2">
                      {cert.name}
                    </h4>
                    
                    <p className="text-sm text-muted-foreground">
                      {cert.description}
                    </p>
                  </div>
                </HoverAnimation>
              </StaggeredItem>
            ))}
          </StaggeredContainer>
        </div>

        {/* Technology Partners */}
        <div className="mb-16">
          <AnimatedSection animation="fadeIn" className="text-center mb-12">
            <h3 className="text-3xl font-bold text-foreground mb-4">
              Technology Partners
            </h3>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Built with best-in-class technologies from industry leaders
            </p>
          </AnimatedSection>

          <StaggeredContainer className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {technologyPartners.map((partner, index) => (
              <StaggeredItem key={partner.name}>
                <HoverAnimation>
                  <div className="bg-card border border-border/50 rounded-xl p-4 text-center backdrop-blur-sm">
                    <div className="text-3xl mb-2">
                      {partner.logo}
                    </div>
                    <h5 className="font-semibold text-foreground text-sm mb-1">
                      {partner.name}
                    </h5>
                    <p className="text-xs text-muted-foreground mb-2">
                      {partner.description}
                    </p>
                    <div className="text-xs bg-accent/50 text-accent-foreground px-2 py-1 rounded-full">
                      {partner.category}
                    </div>
                  </div>
                </HoverAnimation>
              </StaggeredItem>
            ))}
          </StaggeredContainer>
        </div>

        {/* Customer Testimonials */}
        <div>
          <AnimatedSection animation="fadeIn" className="text-center mb-12">
            <h3 className="text-3xl font-bold text-foreground mb-4">
              What Our Customers Say
            </h3>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Real feedback from real estate professionals using our platform
            </p>
          </AnimatedSection>

          <StaggeredContainer className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <StaggeredItem key={testimonial.author}>
                <HoverAnimation>
                  <div className="bg-card border border-border/50 rounded-2xl p-6 backdrop-blur-sm h-full">
                    <div className="flex items-center mb-4">
                      {[...Array(testimonial.rating)].map((_, i) => (
                        <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                      ))}
                    </div>
                    
                    <blockquote className="text-muted-foreground mb-6 leading-relaxed">
                      "{testimonial.quote}"
                    </blockquote>
                    
                    <div className="border-t border-border pt-4">
                      <div className="font-semibold text-foreground">
                        {testimonial.author}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {testimonial.role}
                      </div>
                      <div className="text-sm text-blue-600 dark:text-blue-400">
                        {testimonial.company}
                      </div>
                    </div>
                  </div>
                </HoverAnimation>
              </StaggeredItem>
            ))}
          </StaggeredContainer>
        </div>
      </div>
    </section>
  )
}
