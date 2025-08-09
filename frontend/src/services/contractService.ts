/**
 * Contract service for contract management operations.
 * 
 * This service handles all contract-related API calls including:
 * - Contract CRUD operations
 * - Template-based contract generation
 * - Contract status management
 * - Version control and history
 */

import { apiClient } from './apiClient'

export interface Contract {
  id: string
  deal_id: string
  template_id: string
  status: 'draft' | 'review' | 'sent' | 'signed' | 'void'
  variables: Record<string, any> | null
  created_at: string
  updated_at: string
  deal?: {
    id: string
    title: string
    property_address?: string
    owner_id: string
  }
  template?: {
    id: string
    name: string
    version: string
  }
}

export interface ContractCreate {
  deal_id: string
  template_id: string
  variables?: Record<string, any>
}

export interface ContractUpdate {
  status?: 'draft' | 'review' | 'sent' | 'signed' | 'void'
  variables?: Record<string, any>
}

export interface ContractGeneration {
  contract_id: string
  output_format: 'pdf' | 'docx'
  variables: Record<string, any>
}

export interface ContractGenerationResult {
  contract_id: string
  file_url: string
  file_size: number
  generated_at: string
}

export interface ContractVersion {
  id: string
  contract_id: string
  version_number: number
  changes: Record<string, any>
  created_at: string
  created_by: string
}

class ContractService {
  /**
   * Get all contracts for the current user
   */
  async getContracts(dealId?: string): Promise<Contract[]> {
    const endpoint = dealId ? `/contracts?deal_id=${dealId}` : '/contracts'
    const response = await apiClient.get<Contract[]>(endpoint)
    return response.data
  }

  /**
   * Get a specific contract by ID
   */
  async getContract(contractId: string): Promise<Contract> {
    const response = await apiClient.get<Contract>(`/contracts/${contractId}`)
    return response.data
  }

  /**
   * Create a new contract
   */
  async createContract(contractData: ContractCreate): Promise<Contract> {
    const response = await apiClient.post<Contract>('/contracts', contractData)
    return response.data
  }

  /**
   * Update an existing contract
   */
  async updateContract(contractId: string, updates: ContractUpdate): Promise<Contract> {
    const response = await apiClient.patch<Contract>(`/contracts/${contractId}`, updates)
    return response.data
  }

  /**
   * Delete a contract
   */
  async deleteContract(contractId: string): Promise<void> {
    await apiClient.delete(`/contracts/${contractId}`)
  }

  /**
   * Generate a contract document
   */
  async generateContract(generation: ContractGeneration): Promise<ContractGenerationResult> {
    const response = await apiClient.post<ContractGenerationResult>(
      `/contracts/${generation.contract_id}/generate`,
      {
        output_format: generation.output_format,
        variables: generation.variables,
      }
    )
    return response.data
  }

  /**
   * Get contract versions/history
   */
  async getContractVersions(contractId: string): Promise<ContractVersion[]> {
    const response = await apiClient.get<ContractVersion[]>(`/contracts/${contractId}/versions`)
    return response.data
  }

  /**
   * Update contract status
   */
  async updateContractStatus(
    contractId: string, 
    status: 'draft' | 'review' | 'sent' | 'signed' | 'void'
  ): Promise<Contract> {
    return this.updateContract(contractId, { status })
  }

  /**
   * Fill contract variables
   */
  async fillContractVariables(
    contractId: string, 
    variables: Record<string, any>
  ): Promise<Contract> {
    return this.updateContract(contractId, { variables })
  }

  /**
   * Get contracts by status
   */
  async getContractsByStatus(status: string): Promise<Contract[]> {
    const response = await apiClient.get<Contract[]>(`/contracts?status=${status}`)
    return response.data
  }

  /**
   * Search contracts
   */
  async searchContracts(query: string): Promise<Contract[]> {
    const response = await apiClient.get<Contract[]>(`/contracts/search?q=${encodeURIComponent(query)}`)
    return response.data
  }

  /**
   * Download generated contract
   */
  async downloadContract(contractId: string, format: 'pdf' | 'docx' = 'pdf'): Promise<void> {
    await apiClient.downloadFile(`/contracts/${contractId}/download?format=${format}`)
  }

  /**
   * Validate contract variables against template schema
   */
  validateContractVariables(variables: Record<string, any>, templateSchema: Record<string, any>): {
    valid: boolean
    errors: string[]
    warnings: string[]
  } {
    const errors: string[] = []
    const warnings: string[] = []

    // Check required fields
    if (templateSchema.required) {
      for (const field of templateSchema.required) {
        if (!variables[field] || variables[field] === '') {
          errors.push(`Required field '${field}' is missing`)
        }
      }
    }

    // Check field types and validation rules
    if (templateSchema.properties) {
      for (const [field, schema] of Object.entries(templateSchema.properties as Record<string, any>)) {
        const value = variables[field]
        
        if (value !== undefined && value !== null && value !== '') {
          // Type validation
          if (schema.type === 'number' && isNaN(Number(value))) {
            errors.push(`Field '${field}' must be a number`)
          }
          
          if (schema.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            errors.push(`Field '${field}' must be a valid email address`)
          }

          // Range validation
          if (schema.min !== undefined && Number(value) < schema.min) {
            errors.push(`Field '${field}' must be at least ${schema.min}`)
          }
          
          if (schema.max !== undefined && Number(value) > schema.max) {
            errors.push(`Field '${field}' must be at most ${schema.max}`)
          }

          // Length validation
          if (schema.minLength !== undefined && String(value).length < schema.minLength) {
            warnings.push(`Field '${field}' should be at least ${schema.minLength} characters`)
          }
          
          if (schema.maxLength !== undefined && String(value).length > schema.maxLength) {
            errors.push(`Field '${field}' must be at most ${schema.maxLength} characters`)
          }
        }
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    }
  }

  /**
   * Format contract status for display
   */
  formatContractStatus(status: string): { label: string; color: string } {
    const statusMap = {
      draft: { label: 'Draft', color: 'gray' },
      review: { label: 'Under Review', color: 'yellow' },
      sent: { label: 'Sent for Signature', color: 'blue' },
      signed: { label: 'Signed', color: 'green' },
      void: { label: 'Void', color: 'red' },
    }

    return statusMap[status as keyof typeof statusMap] || { label: status, color: 'gray' }
  }

  /**
   * Calculate contract completion percentage
   */
  calculateCompletionPercentage(contract: Contract, templateSchema?: Record<string, any>): number {
    if (!contract.variables || !templateSchema?.properties) {
      return 0
    }

    const totalFields = Object.keys(templateSchema.properties).length
    const filledFields = Object.values(contract.variables).filter(
      value => value !== null && value !== undefined && value !== ''
    ).length

    return Math.round((filledFields / totalFields) * 100)
  }

  /**
   * Get next suggested status based on current status
   */
  getNextStatus(currentStatus: string): string | null {
    const statusFlow = {
      draft: 'review',
      review: 'sent',
      sent: 'signed',
      signed: null,
      void: null,
    }

    return statusFlow[currentStatus as keyof typeof statusFlow] || null
  }
}

export const contractService = new ContractService()
export default contractService
