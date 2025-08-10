"use client"

import { motion } from "framer-motion"
import { 
  Code, 
  Database, 
  Cloud, 
  Shield, 
  Zap, 
  Globe,
  Server,
  Cpu,
  Lock,
  Gauge,
  CheckCircle,
  Star
} from "lucide-react"
import { AnimatedSection, StaggeredContainer, StaggeredItem, HoverAnimation } from "./animations/AnimatedSection"

export function TechnologySection() {
  const techStack = [
    {
      category: "Frontend",
      icon: Code,
      gradient: "from-blue-500 to-cyan-500",
      technologies: [
        { name: "Next.js 15", description: "React framework with App Router", logo: "⚛️" },
        { name: "Tailwind CSS", description: "Utility-first CSS framework", logo: "🎨" },
        { name: "shadcn/ui", description: "Modern component library", logo: "🧩" },
        { name: "Framer Motion", description: "Production-ready animations", logo: "🎭" }
      ]
    },
    {
      category: "Backend",
      icon: Server,
      gradient: "from-green-500 to-emerald-500",
      technologies: [
        { name: "FastAPI", description: "High-performance Python API", logo: "⚡" },
        { name: "SQLModel", description: "Type-safe database ORM", logo: "🗃️" },
        { name: "Alembic", description: "Database migration tool", logo: "🔄" },
        { name: "Pydantic", description: "Data validation library", logo: "✅" }
      ]
    },
    {
      category: "AI & ML",
      icon: Cpu,
      gradient: "from-purple-500 to-pink-500",
      technologies: [
        { name: "CrewAI", description: "Multi-agent orchestration", logo: "🤖" },
        { name: "OpenAI GPT", description: "Advanced language models", logo: "🧠" },
        { name: "Anthropic Claude", description: "Constitutional AI assistant", logo: "🎯" },
        { name: "Ollama", description: "Local model deployment", logo: "🏠" }
      ]
    },
    {
      category: "Infrastructure",
      icon: Cloud,
      gradient: "from-orange-500 to-red-500",
      technologies: [
        { name: "Docker", description: "Containerization platform", logo: "🐳" },
        { name: "PostgreSQL", description: "Advanced relational database", logo: "🐘" },
        { name: "Redis", description: "In-memory data structure", logo: "🔴" },
        { name: "AWS/Azure", description: "Cloud infrastructure", logo: "☁️" }
      ]
    }
  ]

  const securityFeatures = [
    {
      icon: Shield,
      title: "Enterprise Security",
      description: "End-to-end encryption and secure data handling",
      features: ["AES-256 encryption", "SOC 2 compliance", "GDPR compliant"]
    },
    {
      icon: Lock,
      title: "Data Privacy",
      description: "Your data stays secure with industry-leading protection",
      features: ["Zero-trust architecture", "Regular security audits", "Data anonymization"]
    },
    {
      icon: Gauge,
      title: "High Performance",
      description: "Optimized for speed and reliability at scale",
      features: ["99.9% uptime SLA", "Sub-second response", "Auto-scaling"]
    },
    {
      icon: Globe,
      title: "Global Availability",
      description: "Accessible worldwide with multi-region deployment",
      features: ["CDN acceleration", "Multi-region backup", "24/7 monitoring"]
    }
  ]

  const metrics = [
    { value: "99.9%", label: "Uptime SLA", icon: CheckCircle },
    { value: "<100ms", label: "API Response", icon: Zap },
    { value: "SOC 2", label: "Compliance", icon: Shield },
    { value: "24/7", label: "Support", icon: Star }
  ]

  return (
    <section id="technology" className="py-24 bg-background relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <AnimatedSection animation="fadeIn" className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center space-x-2 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 px-4 py-2 rounded-full text-sm font-medium mb-6"
          >
            <Code className="w-4 h-4" />
            <span>Modern Technology</span>
          </motion.div>
          
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            <span className="bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-600 bg-clip-text text-transparent">
              Built on Cutting-Edge Tech
            </span>
          </h2>
          
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            Our platform leverages the latest technologies to deliver unmatched performance, 
            security, and scalability for your real estate business.
          </p>
        </AnimatedSection>

        {/* Performance Metrics */}
        <StaggeredContainer className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
          {metrics.map((metric, index) => (
            <StaggeredItem key={metric.label}>
              <HoverAnimation>
                <div className="text-center bg-card border border-border/50 rounded-2xl p-6 backdrop-blur-sm">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r from-purple-500 to-blue-500 text-white mb-3">
                    <metric.icon className="w-6 h-6" />
                  </div>
                  <div className="text-3xl font-bold text-foreground mb-1">
                    {metric.value}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {metric.label}
                  </div>
                </div>
              </HoverAnimation>
            </StaggeredItem>
          ))}
        </StaggeredContainer>

        {/* Technology Stack */}
        <StaggeredContainer className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
          {techStack.map((stack, index) => (
            <StaggeredItem key={stack.category}>
              <HoverAnimation>
                <div className="bg-card border border-border/50 rounded-3xl p-8 backdrop-blur-sm h-full">
                  <div className="flex items-center mb-6">
                    <div className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-r ${stack.gradient} text-white mr-4 shadow-lg`}>
                      <stack.icon className="w-7 h-7" />
                    </div>
                    <h3 className="text-2xl font-bold text-foreground">
                      {stack.category}
                    </h3>
                  </div>
                  
                  <div className="space-y-4">
                    {stack.technologies.map((tech, techIndex) => (
                      <motion.div
                        key={tech.name}
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.5, delay: techIndex * 0.1 }}
                        className="flex items-center space-x-4 p-3 rounded-xl bg-accent/30 hover:bg-accent/50 transition-colors"
                      >
                        <div className="text-2xl">
                          {tech.logo}
                        </div>
                        <div>
                          <h4 className="font-semibold text-foreground">
                            {tech.name}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {tech.description}
                          </p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </HoverAnimation>
            </StaggeredItem>
          ))}
        </StaggeredContainer>

        {/* Security & Performance Features */}
        <div className="space-y-12">
          <AnimatedSection animation="fadeIn" className="text-center">
            <h3 className="text-3xl font-bold text-foreground mb-4">
              Enterprise-Grade Security & Performance
            </h3>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Built with security-first architecture and optimized for high-performance at scale
            </p>
          </AnimatedSection>

          <StaggeredContainer className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {securityFeatures.map((feature, index) => (
              <StaggeredItem key={feature.title}>
                <HoverAnimation>
                  <div className="bg-card border border-border/50 rounded-2xl p-6 text-center backdrop-blur-sm h-full">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r from-green-500 to-blue-500 text-white mb-4 shadow-lg">
                      <feature.icon className="w-8 h-8" />
                    </div>
                    
                    <h4 className="text-xl font-bold text-foreground mb-3">
                      {feature.title}
                    </h4>
                    
                    <p className="text-muted-foreground mb-4 leading-relaxed">
                      {feature.description}
                    </p>
                    
                    <div className="space-y-2">
                      {feature.features.map((item, itemIndex) => (
                        <div key={itemIndex} className="flex items-center justify-center space-x-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                          <span className="text-muted-foreground">{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </HoverAnimation>
              </StaggeredItem>
            ))}
          </StaggeredContainer>
        </div>

        {/* Architecture Visualization */}
        <AnimatedSection animation="fadeIn" className="mt-16">
          <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900/50 dark:to-slate-800/50 rounded-3xl p-8 border border-border/50 backdrop-blur-sm">
            <h3 className="text-2xl font-bold text-foreground text-center mb-8">
              Modern Architecture Overview
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <HoverAnimation>
                <div className="text-center">
                  <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-r from-blue-500 to-cyan-500 flex items-center justify-center text-white shadow-lg">
                    <Code className="w-10 h-10" />
                  </div>
                  <h4 className="font-semibold text-foreground mb-2">Frontend Layer</h4>
                  <p className="text-sm text-muted-foreground">Next.js + React with modern UI components</p>
                </div>
              </HoverAnimation>
              
              <HoverAnimation>
                <div className="text-center">
                  <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-r from-green-500 to-emerald-500 flex items-center justify-center text-white shadow-lg">
                    <Server className="w-10 h-10" />
                  </div>
                  <h4 className="font-semibold text-foreground mb-2">API Layer</h4>
                  <p className="text-sm text-muted-foreground">FastAPI with type-safe data validation</p>
                </div>
              </HoverAnimation>
              
              <HoverAnimation>
                <div className="text-center">
                  <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-white shadow-lg">
                    <Cpu className="w-10 h-10" />
                  </div>
                  <h4 className="font-semibold text-foreground mb-2">AI Layer</h4>
                  <p className="text-sm text-muted-foreground">Multi-agent AI with CrewAI orchestration</p>
                </div>
              </HoverAnimation>
            </div>
          </div>
        </AnimatedSection>
      </div>
    </section>
  )
}
