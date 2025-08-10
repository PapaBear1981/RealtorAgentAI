"use client"

import { motion } from "framer-motion"
import { 
  Clock, 
  Shield, 
  DollarSign, 
  Users, 
  TrendingUp, 
  CheckCircle,
  Star,
  Target,
  Zap,
  Award
} from "lucide-react"
import { AnimatedSection, StaggeredContainer, StaggeredItem, HoverAnimation } from "./animations/AnimatedSection"

export function BenefitsSection() {
  const userTypes = [
    {
      id: "agents-brokers",
      title: "Real Estate Agents & Brokers",
      icon: Users,
      gradient: "from-blue-500 to-cyan-500",
      bgGradient: "from-blue-50 to-cyan-50 dark:from-blue-950/20 dark:to-cyan-950/20",
      benefits: [
        { icon: Clock, title: "Save 80% Time", description: "Automate document processing and contract generation" },
        { icon: DollarSign, title: "Increase Revenue", description: "Handle 3x more transactions with same resources" },
        { icon: Shield, title: "Zero Compliance Risk", description: "Automated validation ensures 100% compliance" },
        { icon: TrendingUp, title: "Faster Closings", description: "Streamlined workflows reduce closing time by 50%" }
      ]
    },
    {
      id: "coordinators",
      title: "Transaction Coordinators",
      icon: Target,
      gradient: "from-purple-500 to-pink-500",
      bgGradient: "from-purple-50 to-pink-50 dark:from-purple-950/20 dark:to-pink-950/20",
      benefits: [
        { icon: Zap, title: "Instant Processing", description: "AI extracts data from documents in seconds" },
        { icon: CheckCircle, title: "Error-Free Contracts", description: "Automated validation catches all mistakes" },
        { icon: Users, title: "Multi-Party Tracking", description: "Real-time signature status across all parties" },
        { icon: Star, title: "Client Satisfaction", description: "Faster, more accurate service delivery" }
      ]
    },
    {
      id: "compliance-admins",
      title: "Compliance Officers & Admins",
      icon: Award,
      gradient: "from-green-500 to-emerald-500",
      bgGradient: "from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20",
      benefits: [
        { icon: Shield, title: "Regulatory Compliance", description: "Multi-jurisdiction support with automatic updates" },
        { icon: TrendingUp, title: "Audit Trails", description: "Complete documentation for regulatory reviews" },
        { icon: CheckCircle, title: "Risk Mitigation", description: "AI identifies potential compliance issues early" },
        { icon: Award, title: "Quality Assurance", description: "Consistent, standardized contract quality" }
      ]
    }
  ]

  const overallBenefits = [
    {
      icon: Clock,
      title: "80% Time Savings",
      description: "Automate repetitive tasks and focus on high-value activities",
      metric: "Average 6 hours saved per transaction"
    },
    {
      icon: Shield,
      title: "100% Compliance",
      description: "Multi-jurisdiction validation ensures regulatory compliance",
      metric: "Zero compliance violations reported"
    },
    {
      icon: DollarSign,
      title: "3x ROI Increase",
      description: "Handle more transactions with same resources",
      metric: "Average $50K additional revenue per agent"
    },
    {
      icon: TrendingUp,
      title: "50% Faster Closings",
      description: "Streamlined workflows accelerate transaction completion",
      metric: "Average 15 days faster closing time"
    }
  ]

  return (
    <section id="benefits" className="py-24 bg-gradient-to-br from-background via-accent/5 to-background relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <AnimatedSection animation="fadeIn" className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center space-x-2 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-4 py-2 rounded-full text-sm font-medium mb-6"
          >
            <TrendingUp className="w-4 h-4" />
            <span>Proven Benefits</span>
          </motion.div>
          
          <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
            <span className="bg-gradient-to-r from-green-600 via-blue-600 to-purple-600 bg-clip-text text-transparent">
              Transform Your Business
            </span>
          </h2>
          
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            Join thousands of real estate professionals who have revolutionized their workflows 
            and dramatically increased their productivity with our AI-powered platform.
          </p>
        </AnimatedSection>

        {/* Overall Benefits Grid */}
        <StaggeredContainer className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
          {overallBenefits.map((benefit, index) => (
            <StaggeredItem key={benefit.title}>
              <HoverAnimation>
                <div className="bg-card border border-border/50 rounded-2xl p-6 text-center backdrop-blur-sm">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r from-blue-500 to-purple-500 text-white mb-4 shadow-lg">
                    <benefit.icon className="w-8 h-8" />
                  </div>
                  
                  <h3 className="text-2xl font-bold text-foreground mb-2">
                    {benefit.title}
                  </h3>
                  
                  <p className="text-muted-foreground mb-3 leading-relaxed">
                    {benefit.description}
                  </p>
                  
                  <div className="text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-3 py-1 rounded-full">
                    {benefit.metric}
                  </div>
                </div>
              </HoverAnimation>
            </StaggeredItem>
          ))}
        </StaggeredContainer>

        {/* Role-Based Benefits */}
        <div className="space-y-16">
          <AnimatedSection animation="fadeIn" className="text-center">
            <h3 className="text-3xl font-bold text-foreground mb-4">
              Benefits by Role
            </h3>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Discover how RealtorAgentAI transforms workflows for every role in your organization
            </p>
          </AnimatedSection>

          <StaggeredContainer className="space-y-12">
            {userTypes.map((userType, index) => (
              <StaggeredItem key={userType.id}>
                <div className={`relative rounded-3xl p-8 bg-gradient-to-br ${userType.bgGradient} border border-border/50 backdrop-blur-sm`}>
                  <div className={`grid grid-cols-1 lg:grid-cols-3 gap-8 items-center ${index % 2 === 1 ? 'lg:grid-flow-col-dense' : ''}`}>
                    {/* User Type Header */}
                    <div className={index % 2 === 1 ? 'lg:col-start-3' : ''}>
                      <HoverAnimation>
                        <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r ${userType.gradient} text-white mb-6 shadow-lg`}>
                          <userType.icon className="w-8 h-8" />
                        </div>
                      </HoverAnimation>
                      
                      <h4 className="text-2xl font-bold text-foreground mb-4">
                        {userType.title}
                      </h4>
                      
                      <p className="text-muted-foreground leading-relaxed">
                        Specialized benefits designed for your unique workflow and responsibilities
                      </p>
                    </div>
                    
                    {/* Benefits Grid */}
                    <div className={`lg:col-span-2 ${index % 2 === 1 ? 'lg:col-start-1' : ''}`}>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {userType.benefits.map((benefit, benefitIndex) => (
                          <motion.div
                            key={benefit.title}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: benefitIndex * 0.1 }}
                            className="bg-white/50 dark:bg-black/20 rounded-xl p-4 backdrop-blur-sm border border-white/20 dark:border-white/10"
                          >
                            <div className="flex items-start space-x-3">
                              <div className={`flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-r ${userType.gradient} flex items-center justify-center`}>
                                <benefit.icon className="w-5 h-5 text-white" />
                              </div>
                              <div>
                                <h5 className="font-semibold text-foreground mb-1">
                                  {benefit.title}
                                </h5>
                                <p className="text-sm text-muted-foreground">
                                  {benefit.description}
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </StaggeredItem>
            ))}
          </StaggeredContainer>
        </div>

        {/* Call to Action */}
        <AnimatedSection animation="fadeIn" className="text-center mt-16">
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-8 text-white">
            <h3 className="text-3xl font-bold mb-4">
              Ready to Transform Your Business?
            </h3>
            <p className="text-xl mb-6 opacity-90">
              Join thousands of professionals already saving time and increasing revenue
            </p>
            <HoverAnimation>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-white text-blue-600 px-8 py-4 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transition-all duration-300"
              >
                Start Your Free Trial Today
              </motion.button>
            </HoverAnimation>
          </div>
        </AnimatedSection>
      </div>
    </section>
  )
}
