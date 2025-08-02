"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useToast } from "@/hooks/use-toast"

interface Message {
  id: string
  type: 'user' | 'agent'
  content: string
  timestamp: string
  context?: string
}

interface QuickAction {
  id: string
  label: string
  description: string
  prompt: string
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'whats-left',
    label: "What's left?",
    description: "Get a checklist of remaining tasks",
    prompt: "What tasks are still pending for this contract?"
  },
  {
    id: 'explain-clause',
    label: "Explain clause",
    description: "Get explanation of contract clauses",
    prompt: "Can you explain the financing contingency clause?"
  },
  {
    id: 'summarize-changes',
    label: "Summarize changes",
    description: "Get summary of recent changes",
    prompt: "What changes were made in the latest version?"
  },
  {
    id: 'compliance-check',
    label: "Compliance check",
    description: "Check for compliance issues",
    prompt: "Are there any compliance issues I should be aware of?"
  }
]

interface HelpAgentModalProps {
  isOpen: boolean
  onClose: () => void
  context?: {
    page: string
    dealId?: string
    contractId?: string
    documentName?: string
  }
}

export function HelpAgentModal({ isOpen, onClose, context }: HelpAgentModalProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'agent',
      content: `Hello! I'm your AI assistant for real estate contracts. I can help you with questions about your current deal, explain contract clauses, check what's left to complete, and guide you through the process.

${context?.documentName ? `I can see you're working on "${context.documentName}".` : ''} How can I help you today?`,
      timestamp: new Date().toISOString(),
      context: context?.page
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    // Simulate AI response
    setTimeout(() => {
      const agentResponse = generateAgentResponse(content.trim(), context)
      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'agent',
        content: agentResponse,
        timestamp: new Date().toISOString(),
        context: context?.page
      }

      setMessages(prev => [...prev, agentMessage])
      setIsLoading(false)
    }, 1500)
  }

  const generateAgentResponse = (userInput: string, context?: any): string => {
    const input = userInput.toLowerCase()

    if (input.includes("what's left") || input.includes("remaining") || input.includes("pending")) {
      return `Based on your current contract, here's what's still needed:

**Pending Tasks:**
• ✅ Document upload - Complete
• ✅ Contract generation - Complete  
• 🔄 Review and approval - In progress
• ⏳ Signature collection - Waiting (3 parties)
• ⏳ Final compliance check - Pending

**Next Steps:**
1. Complete the review process (currently on version 2)
2. Address any outstanding comments
3. Send for signatures once approved
4. Schedule final walkthrough

Would you like me to explain any of these steps in detail?`
    }

    if (input.includes("explain") && (input.includes("clause") || input.includes("contingency") || input.includes("financing"))) {
      return `**Financing Contingency Clause Explanation:**

This clause protects the buyer by allowing them to cancel the contract if they cannot secure financing within the specified timeframe (typically 30 days).

**Key Points:**
• Buyer must apply for financing within 3-5 business days
• Lender commitment required within 30 days
• If financing is denied, buyer can cancel without penalty
• Earnest money is returned if contingency is not met

**Your Contract:**
• Financing contingency: 30 days from acceptance
• Loan type: Conventional
• Down payment: Based on your financing terms

This is a standard protection - would you like me to explain any other clauses?`
    }

    if (input.includes("changes") || input.includes("version") || input.includes("summary")) {
      return `**Recent Changes Summary (Version 2):**

**Modified:**
• Purchase price increased from $350,000 to $365,000
• Reason: Market adjustment based on comparable sales

**Added:**
• Home warranty provision - Seller provides 1-year warranty
• Covers major systems and appliances

**Impact:**
• Total contract value increased by $15,000
• Additional buyer protection with warranty
• No change to closing timeline

**Status:** Currently under review by all parties

Would you like me to explain the reasoning behind any of these changes?`
    }

    if (input.includes("compliance") || input.includes("issues") || input.includes("problems")) {
      return `**Compliance Check Results:**

**✅ All Clear:**
• Required disclosures - Complete
• Signature requirements - Properly defined
• Date validations - All dates are logical
• Financial terms - Properly structured

**⚠️ Minor Recommendations:**
• Consider adding specific home warranty company name
• Verify property tax proration method
• Confirm title company selection

**📋 Regulatory Compliance:**
• RESPA requirements - Met
• State disclosure requirements - Complete
• E-signature compliance - Ready

No critical issues found. The contract meets all standard requirements.`
    }

    // Default response
    return `I understand you're asking about "${userInput}". 

Based on your current context${context?.documentName ? ` working on "${context.documentName}"` : ''}, I can help you with:

• **Contract questions** - Explain clauses, terms, and conditions
• **Process guidance** - What to do next, timeline expectations  
• **Compliance checks** - Ensure everything meets requirements
• **Status updates** - Track progress and pending items

Could you be more specific about what you'd like to know? You can also use the quick action buttons for common questions.`
  }

  const handleQuickAction = (action: QuickAction) => {
    sendMessage(action.prompt)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(inputValue)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[80vh] flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="flex items-center space-x-3">
            <Avatar className="w-8 h-8 bg-blue-500">
              <AvatarFallback className="text-white text-sm">AI</AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="text-lg">AI Contract Assistant</CardTitle>
              <p className="text-sm text-gray-600">
                {context?.page && (
                  <Badge variant="outline" className="text-xs">
                    {context.page}
                  </Badge>
                )}
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col space-y-4 min-h-0">
          {/* Quick Actions */}
          <div className="grid grid-cols-2 gap-2">
            {QUICK_ACTIONS.map((action) => (
              <Button
                key={action.id}
                variant="outline"
                size="sm"
                className="text-left h-auto p-2"
                onClick={() => handleQuickAction(action)}
                disabled={isLoading}
              >
                <div>
                  <div className="font-medium text-xs">{action.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{action.description}</div>
                </div>
              </Button>
            ))}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 min-h-0 max-h-96">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    message.type === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                  <div
                    className={`text-xs mt-2 ${
                      message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}
                  >
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg p-3">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                    <span className="text-sm text-gray-600">AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="flex space-x-2">
            <Input
              placeholder="Ask me anything about your contract..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              className="flex-1"
            />
            <Button 
              onClick={() => sendMessage(inputValue)}
              disabled={!inputValue.trim() || isLoading}
            >
              Send
            </Button>
          </div>

          <div className="text-xs text-gray-500 text-center">
            Press Enter to send • This AI assistant provides guidance but not legal advice
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
