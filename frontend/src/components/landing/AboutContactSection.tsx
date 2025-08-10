"use client"

import { motion } from "framer-motion"
import { 
  Mail, 
  Phone, 
  MapPin, 
  Calendar, 
  Send, 
  CheckCircle,
  Target,
  Users,
  Lightbulb,
  Heart,
  Globe,
  Clock
} from "lucide-react"
import { AnimatedSection, StaggeredContainer, StaggeredItem, HoverAnimation } from "./animations/AnimatedSection"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

export function AboutContactSection() {
  const companyValues = [
    {
      icon: Target,
      title: "Innovation First",
      description: "We leverage cutting-edge AI to solve real-world problems in real estate"
    },
    {
      icon: Users,
      title: "Customer Success",
      description: "Your success is our success - we're committed to your growth"
    },
    {
      icon: Lightbulb,
      title: "Continuous Learning",
      description: "We constantly evolve our platform based on user feedback and industry needs"
    },
    {
      icon: Heart,
      title: "Ethical AI",
      description: "We build responsible AI that augments human capabilities, not replaces them"
    }
  ]

  const contactMethods = [
    {
      icon: Mail,
      title: "Email Support",
      description: "Get help from our expert team",
      contact: "support@realtoragentai.com",
      availability: "24/7 Response"
    },
    {
      icon: Phone,
      title: "Phone Support",
      description: "Speak directly with our specialists",
      contact: "+1 (555) 123-4567",
      availability: "Mon-Fri 9AM-6PM EST"
    },
    {
      icon: Calendar,
      title: "Schedule Demo",
      description: "Book a personalized demonstration",
      contact: "Book a 30-min demo",
      availability: "Available Daily"
    },
    {
      icon: MapPin,
      title: "Office Location",
      description: "Visit our headquarters",
      contact: "San Francisco, CA",
      availability: "By Appointment"
    }
  ]

  return (
    <section className="py-24 bg-background relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* About Us Section */}
        <div id="about" className="mb-24">
          <AnimatedSection animation="fadeIn" className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center space-x-2 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 px-4 py-2 rounded-full text-sm font-medium mb-6"
            >
              <Globe className="w-4 h-4" />
              <span>About RealtorAgentAI</span>
            </motion.div>
            
            <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
              <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                Revolutionizing Real Estate
              </span>
            </h2>
            
            <p className="text-xl text-muted-foreground max-w-4xl mx-auto leading-relaxed">
              We're on a mission to transform the real estate industry through intelligent automation. 
              Our AI-powered platform empowers professionals to focus on what matters most - building 
              relationships and closing deals - while we handle the complex, time-consuming paperwork.
            </p>
          </AnimatedSection>

          {/* Company Vision */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-16">
            <AnimatedSection animation="slideInLeft">
              <div className="space-y-6">
                <h3 className="text-3xl font-bold text-foreground">
                  Our Vision
                </h3>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  We envision a future where real estate professionals can focus entirely on their clients, 
                  while AI handles the administrative burden. By automating document processing, contract 
                  generation, and compliance checking, we're creating more time for what truly matters - 
                  human connections and exceptional service.
                </p>
                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0" />
                    <span className="text-muted-foreground">Founded by real estate and AI experts</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0" />
                    <span className="text-muted-foreground">Trusted by 10,000+ professionals</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0" />
                    <span className="text-muted-foreground">Processing millions of documents annually</span>
                  </div>
                </div>
              </div>
            </AnimatedSection>

            <AnimatedSection animation="slideInRight">
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950/20 dark:to-purple-950/20 rounded-3xl p-8 border border-border/50 backdrop-blur-sm">
                <div className="grid grid-cols-2 gap-6">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-indigo-600 dark:text-indigo-400 mb-2">
                      2023
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Company Founded
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-purple-600 dark:text-purple-400 mb-2">
                      10K+
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Active Users
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-pink-600 dark:text-pink-400 mb-2">
                      500+
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Partner Agencies
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-cyan-600 dark:text-cyan-400 mb-2">
                      99.9%
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Uptime SLA
                    </div>
                  </div>
                </div>
              </div>
            </AnimatedSection>
          </div>

          {/* Company Values */}
          <StaggeredContainer className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {companyValues.map((value, index) => (
              <StaggeredItem key={value.title}>
                <HoverAnimation>
                  <div className="bg-card border border-border/50 rounded-2xl p-6 text-center backdrop-blur-sm h-full">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-500 text-white mb-4 shadow-lg">
                      <value.icon className="w-8 h-8" />
                    </div>
                    
                    <h4 className="text-xl font-bold text-foreground mb-3">
                      {value.title}
                    </h4>
                    
                    <p className="text-muted-foreground leading-relaxed">
                      {value.description}
                    </p>
                  </div>
                </HoverAnimation>
              </StaggeredItem>
            ))}
          </StaggeredContainer>
        </div>

        {/* Contact Section */}
        <div id="contact">
          <AnimatedSection animation="fadeIn" className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center space-x-2 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-4 py-2 rounded-full text-sm font-medium mb-6"
            >
              <Mail className="w-4 h-4" />
              <span>Get In Touch</span>
            </motion.div>
            
            <h2 className="text-4xl sm:text-5xl font-bold text-foreground mb-6">
              <span className="bg-gradient-to-r from-green-600 via-blue-600 to-purple-600 bg-clip-text text-transparent">
                Ready to Get Started?
              </span>
            </h2>
            
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
              Have questions or ready to transform your real estate workflow? 
              We're here to help you get started with RealtorAgentAI.
            </p>
          </AnimatedSection>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            {/* Contact Methods */}
            <AnimatedSection animation="slideInLeft">
              <div className="space-y-6">
                <h3 className="text-2xl font-bold text-foreground mb-6">
                  Multiple Ways to Connect
                </h3>
                
                <StaggeredContainer className="space-y-4">
                  {contactMethods.map((method, index) => (
                    <StaggeredItem key={method.title}>
                      <HoverAnimation>
                        <div className="flex items-start space-x-4 p-4 rounded-xl bg-card border border-border/50 backdrop-blur-sm">
                          <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-r from-green-500 to-blue-500 flex items-center justify-center text-white">
                            <method.icon className="w-6 h-6" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-foreground mb-1">
                              {method.title}
                            </h4>
                            <p className="text-sm text-muted-foreground mb-2">
                              {method.description}
                            </p>
                            <div className="text-sm font-medium text-blue-600 dark:text-blue-400">
                              {method.contact}
                            </div>
                            <div className="flex items-center space-x-1 text-xs text-muted-foreground mt-1">
                              <Clock className="w-3 h-3" />
                              <span>{method.availability}</span>
                            </div>
                          </div>
                        </div>
                      </HoverAnimation>
                    </StaggeredItem>
                  ))}
                </StaggeredContainer>
              </div>
            </AnimatedSection>

            {/* Contact Form */}
            <AnimatedSection animation="slideInRight">
              <div className="bg-card border border-border/50 rounded-3xl p-8 backdrop-blur-sm">
                <h3 className="text-2xl font-bold text-foreground mb-6">
                  Send us a Message
                </h3>
                
                <form className="space-y-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-2">
                        First Name
                      </label>
                      <Input placeholder="John" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-2">
                        Last Name
                      </label>
                      <Input placeholder="Doe" />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Email Address
                    </label>
                    <Input type="email" placeholder="john@example.com" />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Company
                    </label>
                    <Input placeholder="Your Real Estate Company" />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Message
                    </label>
                    <Textarea 
                      placeholder="Tell us about your needs and how we can help..."
                      rows={4}
                    />
                  </div>
                  
                  <HoverAnimation>
                    <Button 
                      type="submit" 
                      size="lg" 
                      className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white"
                    >
                      <Send className="w-5 h-5 mr-2" />
                      Send Message
                    </Button>
                  </HoverAnimation>
                </form>
              </div>
            </AnimatedSection>
          </div>
        </div>
      </div>
    </section>
  )
}
