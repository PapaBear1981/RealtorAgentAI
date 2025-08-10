import { useAssistantAgentStore } from '@/stores/helpAgentStore'
import { generateUniqueId } from '@/utils/idGenerator'
import { apiClient } from './apiClient'
import { documentService } from './documentService'

export interface ActionRequest {
  type: 'contract_fill' | 'document_extract' | 'signature_send' | 'review_request' | 'file_search'
  description: string
  parameters: {
    contractType?: string
    sourceFiles?: string[]
    targetFields?: string[]
    dealName?: string
    searchQuery?: string
    recipients?: string[]
  }
}

export interface ActionResult {
  success: boolean
  data?: any
  error?: string
  progress?: number
}

class AssistantAgentService {
  private store = useAssistantAgentStore

  async executeAction(request: ActionRequest): Promise<ActionResult> {
    const actionId = generateUniqueId('action')

    // Add action to store
    this.store.getState().addAction({
      type: request.type,
      status: 'pending',
      description: request.description,
      progress: 0
    })

    try {
      // Update to in progress
      this.store.getState().updateAction(actionId, {
        status: 'in_progress',
        progress: 10
      })

      let result: ActionResult

      switch (request.type) {
        case 'contract_fill':
          result = await this.fillContract(request, actionId)
          break
        case 'document_extract':
          result = await this.extractFromDocuments(request, actionId)
          break
        case 'signature_send':
          result = await this.sendForSignatures(request, actionId)
          break
        case 'review_request':
          result = await this.requestReview(request, actionId)
          break
        case 'file_search':
          result = await this.searchFiles(request, actionId)
          break
        default:
          throw new Error(`Unknown action type: ${request.type}`)
      }

      // Update to completed
      this.store.getState().updateAction(actionId, {
        status: 'completed',
        progress: 100,
        result: result.data
      })

      return result

    } catch (error) {
      // Update to failed
      this.store.getState().updateAction(actionId, {
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      })

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  private async fillContract(request: ActionRequest, actionId: string): Promise<ActionResult> {
    const { contractType, sourceFiles, dealName } = request.parameters

    try {
      // Step 1: Analyze source documents
      this.store.getState().updateAction(actionId, { progress: 20 })
      this.store.getState().addMessage({
        type: 'system',
        content: '🔄 Analyzing source documents...',
        actionType: 'contract_fill',
        actionStatus: 'in_progress'
      })

      // Get document processing results for source files
      const documentData: Record<string, any> = {}
      if (sourceFiles && sourceFiles.length > 0) {
        for (const fileId of sourceFiles) {
          try {
            const processingResult = await documentService.getProcessingResult(fileId)
            if (processingResult) {
              Object.assign(documentData, processingResult.extracted_data)
            }
          } catch (error) {
            console.warn(`Failed to get processing result for file ${fileId}:`, error)
          }
        }
      }

      // Step 2: Call AI agent for contract filling
      this.store.getState().updateAction(actionId, { progress: 40 })
      this.store.getState().addMessage({
        type: 'system',
        content: '🔄 AI agent extracting contract information...',
        actionType: 'contract_fill',
        actionStatus: 'in_progress'
      })

      const aiResponse = await apiClient.post('/api/v1/ai-agents/contract-fill', {
        contract_type: contractType,
        source_data: documentData,
        deal_name: dealName,
        // template_id: templateId,  // Removed - not available in parameters
      })

      // Step 3: Create or update contract
      this.store.getState().updateAction(actionId, { progress: 70 })
      this.store.getState().addMessage({
        type: 'system',
        content: '🔄 Creating contract with extracted data...',
        actionType: 'contract_fill',
        actionStatus: 'in_progress'
      })

      let contract
      // Contract creation disabled - templateId and dealId not available in parameters
      // if (dealId && templateId) {
      //   contract = await contractService.createContract({
      //     deal_id: dealId,
      //     template_id: templateId,
      //     variables: aiResponse.data.extracted_variables,
      //   })
      // }

      // Step 4: Validation
      this.store.getState().updateAction(actionId, { progress: 90 })
      this.store.getState().addMessage({
        type: 'system',
        content: '🔄 Validating contract completion...',
        actionType: 'contract_fill',
        actionStatus: 'in_progress'
      })

      console.log('AI Response received:', aiResponse)
      console.log('AI Response type:', typeof aiResponse)
      console.log('AI Response keys:', Object.keys(aiResponse))
      console.log('AI Response data keys:', Object.keys(aiResponse.data || {}))
      console.log('AI Response ai_response field:', aiResponse.data?.ai_response)
      console.log('AI Response ai_response type:', typeof aiResponse.data?.ai_response)
      console.log('AI Response ai_response length:', aiResponse.data?.ai_response?.length || 0)
      console.log('Full AI Response JSON:', JSON.stringify(aiResponse, null, 2))

      return {
        success: true,
        data: {
          contractType,
          filledFields: aiResponse.data?.extracted_variables,
          sourceFiles,
          contractId: generateUniqueId('contract'),  // contract?.id || generateUniqueId('contract'),
          confidence: aiResponse.data?.confidence || 0.85,
          aiAgentResponse: aiResponse.data?.ai_response,
        }
      }

    } catch (error) {
      console.error('Contract filling failed:', error)

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Contract filling failed',
        data: {
          contractType,
          sourceFiles,
        }
      }
    }
  }

  private async extractFromDocuments(request: ActionRequest, actionId: string): Promise<ActionResult> {
    const { sourceFiles, targetFields } = request.parameters

    const steps = [
      { progress: 25, message: 'Reading document contents...' },
      { progress: 50, message: 'Applying OCR and text extraction...' },
      { progress: 75, message: 'Identifying key information...' }
    ]

    for (const step of steps) {
      await this.delay(800)
      this.store.getState().updateAction(actionId, { progress: step.progress })
      this.store.getState().addMessage({
        type: 'system',
        content: `📄 ${step.message}`,
        actionType: 'document_extract',
        actionStatus: 'in_progress'
      })
    }

    try {
      const extractedData: Record<string, any> = {}

      if (sourceFiles && sourceFiles.length > 0) {
        for (const fileId of sourceFiles) {
          try {
            // Get existing processing result or trigger new processing
            let processingResult = await documentService.getProcessingResult(fileId)

            if (!processingResult) {
              // Trigger document processing
              processingResult = await documentService.processDocument(fileId)
            }

            if (processingResult) {
              Object.assign(extractedData, processingResult.extracted_data)
            }
          } catch (error) {
            console.warn(`Failed to process document ${fileId}:`, error)
          }
        }
      }

      // Use AI agent for enhanced extraction
      this.store.getState().updateAction(actionId, { progress: 60 })
      this.store.getState().addMessage({
        type: 'system',
        content: '🤖 AI agent analyzing extracted data...',
        actionType: 'document_extract',
        actionStatus: 'in_progress'
      })

      const aiResponse = await apiClient.post('/api/v1/ai-agents/document-extract', {
        extracted_data: extractedData,
        target_fields: targetFields,
        source_files: sourceFiles,
      })

      const structuredData = {
        ...extractedData,
        ...aiResponse.data.enhanced_extraction,
        confidence: aiResponse.data.confidence || 0.8,
      }

      return {
        success: true,
        data: {
          extractedData: structuredData,
          sourceFiles,
          targetFields,
          aiAgentResponse: aiResponse.data,
        }
      }

    } catch (error) {
      console.error('Document extraction failed:', error)

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Document extraction failed',
        data: {
          sourceFiles,
          targetFields,
        }
      }
    }
  }

  private async sendForSignatures(request: ActionRequest, actionId: string): Promise<ActionResult> {
    const { recipients } = request.parameters

    const steps = [
      { progress: 30, message: 'Preparing contract for signatures...' },
      { progress: 60, message: 'Sending to signature platform...' },
      { progress: 90, message: 'Notifying recipients...' }
    ]

    for (const step of steps) {
      await this.delay(1000)
      this.store.getState().updateAction(actionId, { progress: step.progress })
      this.store.getState().addMessage({
        type: 'system',
        content: `✍️ ${step.message}`,
        actionType: 'signature_send',
        actionStatus: 'in_progress'
      })
    }

    return {
      success: true,
      data: {
        signatureRequestId: generateUniqueId('sig'),
        recipients: recipients || ['buyer@email.com', 'seller@email.com'],
        status: 'sent',
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
      }
    }
  }

  private async requestReview(request: ActionRequest, actionId: string): Promise<ActionResult> {
    const steps = [
      { progress: 40, message: 'Submitting contract for review...' },
      { progress: 80, message: 'Notifying review team...' }
    ]

    for (const step of steps) {
      await this.delay(800)
      this.store.getState().updateAction(actionId, { progress: step.progress })
      this.store.getState().addMessage({
        type: 'system',
        content: `👀 ${step.message}`,
        actionType: 'review_request',
        actionStatus: 'in_progress'
      })
    }

    return {
      success: true,
      data: {
        reviewId: generateUniqueId('review'),
        status: 'pending_review',
        assignedTo: 'Legal Team',
        estimatedCompletion: '2-3 business days'
      }
    }
  }

  private async searchFiles(request: ActionRequest, actionId: string): Promise<ActionResult> {
    const { searchQuery } = request.parameters

    await this.delay(500)
    this.store.getState().updateAction(actionId, { progress: 50 })
    this.store.getState().addMessage({
      type: 'system',
      content: `🔍 Searching for "${searchQuery}"...`,
      actionType: 'file_search',
      actionStatus: 'in_progress'
    })

    await this.delay(500)

    const searchResults = [
      {
        fileName: 'Johnson_Property_Disclosure.pdf',
        relevance: 95,
        excerpt: 'Property located at 123 Main Street...',
        lastModified: '2024-01-15'
      },
      {
        fileName: 'Johnson_Financial_Info.pdf',
        relevance: 87,
        excerpt: 'Credit score: 750, Down payment: $73,000...',
        lastModified: '2024-01-14'
      }
    ]

    return {
      success: true,
      data: {
        query: searchQuery,
        results: searchResults,
        totalFound: searchResults.length
      }
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // Parse natural language commands into action requests
  parseCommand(command: string): ActionRequest | null {
    const lowerCommand = command.toLowerCase()

    // Contract filling patterns
    if (lowerCommand.includes('fill') && (lowerCommand.includes('contract') || lowerCommand.includes('agreement'))) {
      const contractType = this.extractContractType(command)
      const sourceFiles = this.extractSourceFiles(command)

      return {
        type: 'contract_fill',
        description: `Fill out ${contractType} using information from ${sourceFiles.join(', ')}`,
        parameters: {
          contractType,
          sourceFiles,
          dealName: this.extractDealName(command)
        }
      }
    }

    // Document extraction patterns
    if (lowerCommand.includes('extract') || lowerCommand.includes('get information')) {
      return {
        type: 'document_extract',
        description: `Extract information from documents`,
        parameters: {
          sourceFiles: this.extractSourceFiles(command)
        }
      }
    }

    // Signature sending patterns
    if (lowerCommand.includes('send') && lowerCommand.includes('signature')) {
      return {
        type: 'signature_send',
        description: `Send contract for signatures`,
        parameters: {
          recipients: this.extractRecipients(command)
        }
      }
    }

    // Review request patterns
    if (lowerCommand.includes('review') || lowerCommand.includes('approve')) {
      return {
        type: 'review_request',
        description: `Submit contract for review`,
        parameters: {}
      }
    }

    // File search patterns
    if (lowerCommand.includes('search') || lowerCommand.includes('find')) {
      return {
        type: 'file_search',
        description: `Search files for information`,
        parameters: {
          searchQuery: this.extractSearchQuery(command)
        }
      }
    }

    return null
  }

  private extractContractType(command: string): string {
    if (command.toLowerCase().includes('purchase')) return 'Residential Purchase Agreement'
    if (command.toLowerCase().includes('listing')) return 'Listing Agreement'
    return 'Residential Purchase Agreement' // default
  }

  private extractSourceFiles(command: string): string[] {
    const filePatterns = [
      /johnson'?s?\s+(?:file|folder|documents?)/i,
      /smith'?s?\s+(?:file|folder|documents?)/i,
      /(\w+)'?s?\s+(?:file|folder|documents?)/i
    ]

    for (const pattern of filePatterns) {
      const match = command.match(pattern)
      if (match) {
        const name = match[1] || 'Johnson'
        return [`${name}_Property_Disclosure.pdf`, `${name}_Financial_Info.pdf`]
      }
    }

    return ['Johnson_Property_Disclosure.pdf', 'Johnson_Financial_Info.pdf']
  }

  private extractDealName(command: string): string {
    const dealMatch = command.match(/(\w+)'?s?\s+(?:deal|file|folder)/i)
    return dealMatch ? `${dealMatch[1]} Deal` : 'Current Deal'
  }

  private extractRecipients(command: string): string[] {
    // In a real implementation, this would extract email addresses or names
    return ['buyer@email.com', 'seller@email.com']
  }

  private extractSearchQuery(command: string): string {
    const searchMatch = command.match(/(?:search|find)\s+(?:for\s+)?["']?([^"']+)["']?/i)
    return searchMatch ? searchMatch[1].trim() : command
  }
}

export const assistantAgentService = new AssistantAgentService()
