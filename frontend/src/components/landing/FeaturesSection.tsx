"use client"

import { motion } from "framer-motion"
import { 
  FileText, 
  Brain, 
  Shield, 
  PenTool, 
  Users, 
  BarChart3,
  CheckCircle,
  Zap,
  Database,
  Settings,
  Globe,
  Lock
} from "lucide-react"
import { AnimatedSection, StaggeredContainer, StaggeredItem, HoverAnimation } from "./animations/AnimatedSection"

export function FeaturesSection() {
  const features = [
    {
      id: "document-processing",
      icon: FileText,
      title: "AI-Powered Document Processing",
      subtitle: "Automated Document Ingestion & Smart Data Extraction",
      description: "Upload any real estate document format and let our AI extract key information with confidence scoring.",
      capabilities: [
        "PDF, DOCX, and image processing via OCR",
        "Smart entity extraction with confidence scoring",
        "Multi-format support for any document type",
        "Automated data validation and verification"
      ],
      gradient: "from-blue-500 to-cyan-500",
      bgGradient: "from-blue-50 to-cyan-50 dark:from-blue-950/20 dark:to-cyan-950/20"
    },
    {
      id: "contract-generation",
      icon: Brain,
      title: "Intelligent Contract Generation",
      subtitle: "Template-Based Generation with Advanced Rendering",
      description: "Generate standardized contracts from extracted data using our powerful Jinja2 template engine.",
      capabilities: [
        "Template-based contract generation",
        "Jinja2 template engine with security",
        "Multi-format output (PDF, DOCX, web)",
        "Template versioning with rollback capabilities"
      ],
      gradient: "from-purple-500 to-pink-500",
      bgGradient: "from-purple-50 to-pink-50 dark:from-purple-950/20 dark:to-pink-950/20"
    },
    {
      id: "compliance-validation",
      icon: Shield,
      title: "Compliance & Validation",
      subtitle: "Error Checking & Legal Requirements Database",
      description: "Ensure 100% compliance with automated validation and multi-jurisdiction legal requirements.",
      capabilities: [
        "Automated error and compliance checking",
        "Multi-jurisdiction support (US Federal, CA, TX, FL, NY, Canada)",
        "Risk assessment and factor identification",
        "Advanced business rule engine"
      ],
      gradient: "from-green-500 to-emerald-500",
      bgGradient: "from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20"
    },
    {
      id: "signature-tracking",
      icon: PenTool,
      title: "Multi-Party Signature Tracking",
      subtitle: "E-Signature Integration with Audit Trails",
      description: "Track signatures across multiple parties with comprehensive audit trails and automated reminders.",
      capabilities: [
        "E-signature integration with audit trails",
        "Real-time progress visualization",
        "Automated reminder system",
        "Complete signature history tracking"
      ],
      gradient: "from-orange-500 to-red-500",
      bgGradient: "from-orange-50 to-red-50 dark:from-orange-950/20 dark:to-red-950/20"
    },
    {
      id: "ai-agent-system",
      icon: Users,
      title: "Advanced AI Agent System",
      subtitle: "6 Specialized Agents with 30 Tools",
      description: "Multi-agent collaboration with CrewAI orchestration for comprehensive real estate workflows.",
      capabilities: [
        "6 specialized agents (Data Extraction, Contract Generator, Compliance Checker, Signature Tracker, Summary, Help)",
        "30 agent tools for comprehensive workflows",
        "CrewAI orchestration for multi-agent collaboration",
        "Real-time assistance and contextual Q&A"
      ],
      gradient: "from-indigo-500 to-purple-500",
      bgGradient: "from-indigo-50 to-purple-50 dark:from-indigo-950/20 dark:to-purple-950/20"
    }
  ]

  return (
    <section id="features" className="py-24 bg-background relative overflow-hidden">
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
            <Zap className="w-4 h-4" />
            <span>Powerful Features</span>
          </motion.div>
          
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              Revolutionary AI Platform
            </span>
          </h2>
          
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            Transform your real estate contract workflows with our comprehensive AI-powered platform 
            featuring specialized agents, automated processing, and intelligent validation.
          </p>
        </AnimatedSection>

        {/* Features Grid */}
        <StaggeredContainer className="space-y-16">
          {features.map((feature, index) => (
            <StaggeredItem key={feature.id}>
              <div className={`relative rounded-3xl p-8 bg-gradient-to-br ${feature.bgGradient} border border-border/50 backdrop-blur-sm`}>
                <div className={`grid grid-cols-1 lg:grid-cols-2 gap-8 items-center ${index % 2 === 1 ? 'lg:grid-flow-col-dense' : ''}`}>
                  {/* Content */}
                  <div className={index % 2 === 1 ? 'lg:col-start-2' : ''}>
                    <HoverAnimation>
                      <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r ${feature.gradient} text-white mb-6 shadow-lg`}>
                        <feature.icon className="w-8 h-8" />
                      </div>
                    </HoverAnimation>
                    
                    <h3 className="text-3xl font-bold text-foreground mb-2">
                      {feature.title}
                    </h3>
                    
                    <p className="text-lg font-medium text-muted-foreground mb-4">
                      {feature.subtitle}
                    </p>
                    
                    <p className="text-muted-foreground mb-6 leading-relaxed">
                      {feature.description}
                    </p>
                    
                    <div className="space-y-3">
                      {feature.capabilities.map((capability, capIndex) => (
                        <motion.div
                          key={capIndex}
                          initial={{ opacity: 0, x: -20 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.5, delay: capIndex * 0.1 }}
                          className="flex items-center space-x-3"
                        >
                          <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                          <span className="text-sm text-muted-foreground">{capability}</span>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Visual */}
                  <div className={index % 2 === 1 ? 'lg:col-start-1' : ''}>
                    <HoverAnimation scale={1.02}>
                      <div className="relative">
                        <div className={`bg-gradient-to-br ${feature.gradient} rounded-2xl p-8 shadow-2xl`}>
                          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 space-y-4">
                            <div className="flex items-center space-x-2 mb-4">
                              <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                              <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                              <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                              <div className="flex-1 bg-white/20 rounded-md h-4 ml-4"></div>
                            </div>
                            
                            {/* Feature-specific visualization */}
                            {feature.id === "document-processing" && (
                              <div className="space-y-3">
                                <div className="h-4 bg-blue-300/60 rounded animate-pulse"></div>
                                <div className="h-3 bg-white/40 rounded animate-pulse"></div>
                                <div className="h-3 bg-white/40 rounded w-3/4 animate-pulse"></div>
                                <div className="flex space-x-2 mt-4">
                                  <div className="w-8 h-8 bg-green-400/60 rounded flex items-center justify-center">
                                    <CheckCircle className="w-4 h-4 text-white" />
                                  </div>
                                  <div className="flex-1 h-8 bg-white/20 rounded flex items-center px-2">
                                    <span className="text-xs text-white/80">95% Confidence</span>
                                  </div>
                                </div>
                              </div>
                            )}
                            
                            {feature.id === "contract-generation" && (
                              <div className="space-y-3">
                                <div className="h-4 bg-purple-300/60 rounded animate-pulse"></div>
                                <div className="grid grid-cols-2 gap-2">
                                  <div className="h-12 bg-white/20 rounded flex items-center justify-center">
                                    <FileText className="w-6 h-6 text-white/80" />
                                  </div>
                                  <div className="h-12 bg-white/20 rounded flex items-center justify-center">
                                    <Database className="w-6 h-6 text-white/80" />
                                  </div>
                                </div>
                                <div className="h-3 bg-white/40 rounded w-2/3 animate-pulse"></div>
                              </div>
                            )}
                            
                            {feature.id === "compliance-validation" && (
                              <div className="space-y-3">
                                <div className="h-4 bg-green-300/60 rounded animate-pulse"></div>
                                <div className="flex items-center space-x-2">
                                  <Shield className="w-6 h-6 text-white/80" />
                                  <div className="flex-1 h-3 bg-white/40 rounded animate-pulse"></div>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Lock className="w-6 h-6 text-white/80" />
                                  <div className="flex-1 h-3 bg-white/40 rounded animate-pulse"></div>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Globe className="w-6 h-6 text-white/80" />
                                  <div className="flex-1 h-3 bg-white/40 rounded animate-pulse"></div>
                                </div>
                              </div>
                            )}
                            
                            {feature.id === "signature-tracking" && (
                              <div className="space-y-3">
                                <div className="h-4 bg-orange-300/60 rounded animate-pulse"></div>
                                <div className="space-y-2">
                                  <div className="flex items-center space-x-2">
                                    <div className="w-4 h-4 bg-green-400 rounded-full"></div>
                                    <div className="h-2 bg-white/40 rounded flex-1"></div>
                                  </div>
                                  <div className="flex items-center space-x-2">
                                    <div className="w-4 h-4 bg-yellow-400 rounded-full"></div>
                                    <div className="h-2 bg-white/40 rounded flex-1"></div>
                                  </div>
                                  <div className="flex items-center space-x-2">
                                    <div className="w-4 h-4 bg-gray-400 rounded-full"></div>
                                    <div className="h-2 bg-white/40 rounded flex-1"></div>
                                  </div>
                                </div>
                              </div>
                            )}
                            
                            {feature.id === "ai-agent-system" && (
                              <div className="space-y-3">
                                <div className="h-4 bg-indigo-300/60 rounded animate-pulse"></div>
                                <div className="grid grid-cols-3 gap-2">
                                  {[...Array(6)].map((_, i) => (
                                    <div key={i} className="h-8 bg-white/20 rounded flex items-center justify-center">
                                      <Users className="w-4 h-4 text-white/80" />
                                    </div>
                                  ))}
                                </div>
                                <div className="flex items-center space-x-2">
                                  <BarChart3 className="w-4 h-4 text-white/80" />
                                  <div className="h-2 bg-white/40 rounded flex-1 animate-pulse"></div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {/* Floating indicators */}
                        <motion.div
                          animate={{ y: [0, -10, 0] }}
                          transition={{ duration: 3, repeat: Infinity, delay: index * 0.5 }}
                          className={`absolute -top-4 -right-4 bg-gradient-to-r ${feature.gradient} text-white p-3 rounded-lg shadow-lg`}
                        >
                          <span className="text-sm font-semibold">AI Powered</span>
                        </motion.div>
                      </div>
                    </HoverAnimation>
                  </div>
                </div>
              </div>
            </StaggeredItem>
          ))}
        </StaggeredContainer>
      </div>
    </section>
  )
}
