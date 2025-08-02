"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"
import { assistantAgentService } from "@/services/assistantAgentService"
import { useAssistantAgentStore } from "@/stores/helpAgentStore"
import { useEffect, useRef, useState } from "react"

interface QuickAction {
  id: string
  label: string
  description: string
  prompt: string
  actionType?: 'command' | 'question'
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'fill-contract',
    label: "Fill Contract",
    description: "Fill out a contract using uploaded files",
    prompt: "Fill out the Purchase Agreement using information from the Johnson's files",
    actionType: 'command'
  },
  {
    id: 'extract-info',
    label: "Extract Info",
    description: "Extract information from documents",
    prompt: "Extract all the key information from the uploaded documents",
    actionType: 'command'
  },
  {
    id: 'send-signatures',
    label: "Send for Signatures",
    description: "Send contract for signatures",
    prompt: "Send the completed contract for signatures",
    actionType: 'command'
  },
  {
    id: 'whats-available',
    label: "What's Available?",
    description: "Show available files and contracts",
    prompt: "What files and contracts do I have available to work with?",
    actionType: 'question'
  }
]

export function HelpAgentSlideOut() {
  const {
    isOpen,
    messages,
    currentContext,
    isLoading,
    currentActions,
    togglePanel,
    addMessage,
    setLoading
  } = useAssistantAgentStore()

  const [inputValue, setInputValue] = useState('')
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

    // Add user message
    addMessage({
      type: 'user',
      content: content.trim()
    })

    setInputValue('')
    setLoading(true)

    try {
      // Try to parse as a command first
      const actionRequest = assistantAgentService.parseCommand(content.trim())

      if (actionRequest) {
        // This is a command - execute it
        addMessage({
          type: 'agent',
          content: `I'll help you ${actionRequest.description.toLowerCase()}. Let me get started on that right away!`,
          context: currentContext.page
        })

        // Execute the action
        const result = await assistantAgentService.executeAction(actionRequest)

        if (result.success) {
          addMessage({
            type: 'agent',
            content: `✅ **Task Completed Successfully!**

${formatActionResult(actionRequest.type, result.data)}

Is there anything else you'd like me to help you with?`,
            context: currentContext.page
          })
        } else {
          addMessage({
            type: 'agent',
            content: `❌ **Task Failed**

I encountered an error: ${result.error}

Would you like me to try again or help you with something else?`,
            context: currentContext.page
          })
        }
      } else {
        // This is a question - provide informational response
        setTimeout(() => {
          const agentResponse = generateAgentResponse(content.trim(), currentContext)
          addMessage({
            type: 'agent',
            content: agentResponse,
            context: currentContext.page
          })
        }, 1000)
      }
    } catch (error) {
      addMessage({
        type: 'agent',
        content: `I apologize, but I encountered an error processing your request. Please try again or rephrase your request.`,
        context: currentContext.page
      })
    } finally {
      setLoading(false)
    }
  }

  const formatActionResult = (actionType: string, data: any): string => {
    switch (actionType) {
      case 'contract_fill':
        return `**Contract Filled Successfully:**
• **Contract Type:** ${data.contractType}
• **Buyer:** ${data.filledFields.buyerName}
• **Seller:** ${data.filledFields.sellerName}
• **Property:** ${data.filledFields.propertyAddress}
• **Purchase Price:** ${data.filledFields.purchasePrice}
• **Closing Date:** ${data.filledFields.closingDate}

The contract has been populated with information from: ${data.sourceFiles.join(', ')}`

      case 'document_extract':
        return `**Information Extracted:**
• **Personal Info:** ${data.personalInfo.name}, ${data.personalInfo.email}
• **Property:** ${data.propertyInfo.address}
• **Price:** ${data.propertyInfo.price}
• **Financing:** Down payment ${data.financialInfo.downPayment}, Credit score ${data.financialInfo.creditScore}`

      case 'signature_send':
        return `**Signature Request Sent:**
• **Request ID:** ${data.signatureRequestId}
• **Recipients:** ${data.recipients.join(', ')}
• **Status:** ${data.status}
• **Expires:** ${new Date(data.expiresAt).toLocaleDateString()}`

      case 'review_request':
        return `**Review Request Submitted:**
• **Review ID:** ${data.reviewId}
• **Assigned To:** ${data.assignedTo}
• **Estimated Completion:** ${data.estimatedCompletion}`

      case 'file_search':
        return `**Search Results for "${data.query}":**
${data.results.map((result: any) => `• **${result.fileName}** (${result.relevance}% match)\n  ${result.excerpt}`).join('\n')}`

      default:
        return 'Task completed successfully!'
    }
  }

  const generateAgentResponse = (userInput: string, context: any): string => {
    const input = userInput.toLowerCase()

    if (input.includes("available") || input.includes("what") && (input.includes("files") || input.includes("contracts"))) {
      return `**Available Resources:**

**📁 Files in your system:**
${context.availableFiles?.map((file: string) => `• ${file}`).join('\n') || '• No files currently available'}

**📄 Contract Templates:**
${context.availableContracts?.map((contract: string) => `• ${contract}`).join('\n') || '• No contract templates available'}

**💡 What I can do for you:**
• **"Fill out [contract] using [files]"** - I'll extract info and populate contracts
• **"Extract information from [files]"** - I'll analyze and organize document data
• **"Send [contract] for signatures"** - I'll initiate the signature process
• **"Search for [information]"** - I'll find specific data in your files

Just tell me what you'd like me to do!`
    }

    if (input.includes("help") || input.includes("what can you do")) {
      return `**I'm your AI Assistant Agent!** I can actively perform tasks for you:

**🔧 Actions I can perform:**
• **Fill out contracts** using information from your uploaded files
• **Extract data** from documents and organize it for you
• **Send contracts** for review and signatures automatically
• **Search through** your files to find specific information
• **Coordinate workflows** between different parts of the system

**💬 Example commands:**
• *"Fill out the Purchase Agreement using the Johnson's files"*
• *"Extract all information from the uploaded documents"*
• *"Send the completed contract for signatures"*
• *"Search for property details in my files"*

**🎯 Quick Actions:**
Use the buttons above for common tasks, or just tell me what you'd like me to do in natural language!

I'm here to make your real estate workflow faster and more efficient. What would you like me to help you accomplish?`
    }

    // Default response for unrecognized questions
    return `I'm your AI Assistant Agent, and I can help you accomplish tasks automatically!

**🤖 I can perform actions like:**
• Fill out contracts using your uploaded files
• Extract and organize information from documents
• Send contracts for signatures and review
• Search through your files for specific information

**💡 Try saying something like:**
• *"Fill out a Purchase Agreement using the Johnson files"*
• *"Extract information from my uploaded documents"*
• *"Send this contract for signatures"*

Based on your current context${context?.documentName ? ` working on "${context.documentName}"` : ''} on the ${context?.page || 'current'} page, what would you like me to help you accomplish?`
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

  return (
    <>
      {/* Slide-out Panel */}
      <div
        className={`fixed top-0 right-0 h-full bg-white border-l shadow-xl transition-transform duration-300 ease-in-out z-40 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ width: '420px' }}
      >
        <Card className="h-full rounded-none border-0 flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b">
            <div className="flex items-center space-x-3">
              <Avatar className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600">
                <AvatarFallback className="text-white text-sm font-bold">🤖</AvatarFallback>
              </Avatar>
              <div>
                <CardTitle className="text-lg">AI Assistant Agent</CardTitle>
                <div className="flex items-center space-x-2 mt-1">
                  {currentContext?.page && (
                    <Badge variant="outline" className="text-xs">
                      {currentContext.page}
                    </Badge>
                  )}
                  {currentActions.filter(a => a.status === 'in_progress').length > 0 && (
                    <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-700">
                      {currentActions.filter(a => a.status === 'in_progress').length} active
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={togglePanel}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </Button>
          </CardHeader>

          <CardContent className="flex-1 flex flex-col space-y-4 min-h-0 p-4">
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
            <div className="flex-1 overflow-y-auto space-y-4 min-h-0">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg p-3 ${
                      message.type === 'user'
                        ? 'bg-blue-500 text-white'
                        : message.type === 'system'
                        ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
                        : message.type === 'action'
                        ? 'bg-green-50 text-green-800 border border-green-200'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                    <div
                      className={`text-xs mt-2 ${
                        message.type === 'user'
                          ? 'text-blue-100'
                          : message.type === 'system'
                          ? 'text-yellow-600'
                          : message.type === 'action'
                          ? 'text-green-600'
                          : 'text-gray-500'
                      }`}
                    >
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}

              {/* Active Actions Progress */}
              {currentActions.filter(action => action.status === 'in_progress').map((action) => (
                <div key={action.id} className="flex justify-start">
                  <div className="max-w-[85%] bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="text-sm text-blue-800">
                      <div className="flex items-center space-x-2 mb-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                        <span className="font-medium">{action.description}</span>
                      </div>
                      {action.progress !== undefined && (
                        <div className="w-full bg-blue-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${action.progress}%` }}
                          ></div>
                        </div>
                      )}
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
            <div className="flex space-x-2 pt-2 border-t">
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
                size="sm"
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

      {/* Toggle Tab/Handle */}
      <div
        className={`fixed top-1/2 right-0 transform -translate-y-1/2 transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : 'translate-x-0'
        }`}
      >
        <Button
          onClick={togglePanel}
          className={`rounded-l-lg rounded-r-none h-16 w-12 flex flex-col items-center justify-center shadow-lg transition-all duration-300 ${
            isOpen ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'
          }`}
          title={isOpen ? "Close AI Help" : "Open AI Help"}
        >
          <svg
            className={`w-5 h-5 text-white transition-transform duration-300 ${
              isOpen ? 'rotate-180' : 'rotate-0'
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="text-xs text-white mt-1 writing-mode-vertical">AI</span>
        </Button>
      </div>
    </>
  )
}
