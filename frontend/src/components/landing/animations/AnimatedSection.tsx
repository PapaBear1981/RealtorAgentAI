"use client"

import { motion, MotionProps } from "framer-motion"
import { ReactNode } from "react"
import { useScrollAnimation, animationConfig } from "./AnimationProvider"

interface AnimatedSectionProps {
  children: ReactNode
  animation?: "fadeIn" | "slideInLeft" | "slideInRight" | "scaleIn"
  delay?: number
  className?: string
  threshold?: number
}

export function AnimatedSection({ 
  children, 
  animation = "fadeIn", 
  delay = 0,
  className = "",
  threshold = 0.1
}: AnimatedSectionProps) {
  const { ref, isInView } = useScrollAnimation(threshold)
  
  const animationVariants = {
    ...animationConfig[animation],
    transition: {
      ...animationConfig[animation].transition,
      delay: delay
    }
  }

  return (
    <motion.div
      ref={ref}
      initial={animationVariants.initial}
      animate={isInView ? animationVariants.animate : animationVariants.initial}
      transition={animationVariants.transition}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// Staggered container for animating multiple children
interface StaggeredContainerProps {
  children: ReactNode
  className?: string
  staggerDelay?: number
  childDelay?: number
}

export function StaggeredContainer({ 
  children, 
  className = "",
  staggerDelay = 0.1,
  childDelay = 0.2
}: StaggeredContainerProps) {
  const { ref, isInView } = useScrollAnimation()

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: staggerDelay,
        delayChildren: childDelay
      }
    }
  }

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={containerVariants}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// Individual staggered item
interface StaggeredItemProps {
  children: ReactNode
  className?: string
}

export function StaggeredItem({ children, className = "" }: StaggeredItemProps) {
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: "easeOut" }
    }
  }

  return (
    <motion.div variants={itemVariants} className={className}>
      {children}
    </motion.div>
  )
}

// Parallax wrapper for subtle scroll effects
interface ParallaxWrapperProps {
  children: ReactNode
  offset?: number
  className?: string
}

export function ParallaxWrapper({ 
  children, 
  offset = 50,
  className = ""
}: ParallaxWrapperProps) {
  const { ref, isInView } = useScrollAnimation()

  return (
    <motion.div
      ref={ref}
      initial={{ y: 0 }}
      animate={isInView ? { y: -offset } : { y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// Hover animation wrapper
interface HoverAnimationProps {
  children: ReactNode
  scale?: number
  className?: string
}

export function HoverAnimation({ 
  children, 
  scale = 1.05,
  className = ""
}: HoverAnimationProps) {
  return (
    <motion.div
      whileHover={{ scale }}
      whileTap={{ scale: scale * 0.95 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
