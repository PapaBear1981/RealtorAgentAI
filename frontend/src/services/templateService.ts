/**
 * Template service for contract template management.
 * 
 * This service handles all template-related API calls including:
 * - Template CRUD operations
 * - Template schema management
 * - Template validation and preview
 * - Template versioning
 */

import { apiClient } from './apiClient'

export interface Template {
  id: string
  name: string
  version: string
  description?: string
  docx_key: string
  schema: Record<string, any>
  ruleset: Record<string, any>
  is_active: boolean
  usage_count: number
  created_at: string
  updated_at: string
}

export interface TemplateCreate {
  name: string
  version: string
  description?: string
  docx_key: string
  schema: Record<string, any>
  ruleset: Record<string, any>
}

export interface TemplateUpdate {
  name?: string
  description?: string
  schema?: Record<string, any>
  ruleset?: Record<string, any>
  is_active?: boolean
}

export interface TemplatePreview {
  template_id: string
  variables: Record<string, any>
  output_format: 'pdf' | 'docx'
}

export interface TemplatePreviewResult {
  preview_url: string
  expires_at: string
}

export interface TemplateVariable {
  name: string
  type: 'string' | 'number' | 'date' | 'boolean' | 'email'
  required: boolean
  description?: string
  default_value?: any
  validation?: {
    min?: number
    max?: number
    pattern?: string
    options?: string[]
  }
}

class TemplateService {
  /**
   * Get all templates
   */
  async getTemplates(activeOnly: boolean = true): Promise<Template[]> {
    const endpoint = activeOnly ? '/templates?active=true' : '/templates'
    const response = await apiClient.get<Template[]>(endpoint)
    return response.data
  }

  /**
   * Get a specific template by ID
   */
  async getTemplate(templateId: string): Promise<Template> {
    const response = await apiClient.get<Template>(`/templates/${templateId}`)
    return response.data
  }

  /**
   * Create a new template
   */
  async createTemplate(templateData: TemplateCreate): Promise<Template> {
    const response = await apiClient.post<Template>('/templates', templateData)
    return response.data
  }

  /**
   * Update an existing template
   */
  async updateTemplate(templateId: string, updates: TemplateUpdate): Promise<Template> {
    const response = await apiClient.patch<Template>(`/templates/${templateId}`, updates)
    return response.data
  }

  /**
   * Delete a template
   */
  async deleteTemplate(templateId: string): Promise<void> {
    await apiClient.delete(`/templates/${templateId}`)
  }

  /**
   * Generate template preview
   */
  async previewTemplate(preview: TemplatePreview): Promise<TemplatePreviewResult> {
    const response = await apiClient.post<TemplatePreviewResult>(
      `/templates/${preview.template_id}/preview`,
      {
        variables: preview.variables,
        output_format: preview.output_format,
      }
    )
    return response.data
  }

  /**
   * Upload template document
   */
  async uploadTemplateDocument(templateId: string, file: File): Promise<Template> {
    const response = await apiClient.uploadFile<Template>(
      `/templates/${templateId}/upload`,
      file
    )
    return response.data
  }

  /**
   * Get template variables from schema
   */
  getTemplateVariables(template: Template): TemplateVariable[] {
    const variables: TemplateVariable[] = []
    
    if (!template.schema?.properties) {
      return variables
    }

    for (const [name, schema] of Object.entries(template.schema.properties as Record<string, any>)) {
      variables.push({
        name,
        type: schema.type || 'string',
        required: template.schema.required?.includes(name) || false,
        description: schema.description,
        default_value: schema.default,
        validation: {
          min: schema.min,
          max: schema.max,
          pattern: schema.pattern,
          options: schema.enum,
        },
      })
    }

    return variables
  }

  /**
   * Validate template variables
   */
  validateTemplateVariables(
    variables: Record<string, any>,
    template: Template
  ): { valid: boolean; errors: string[]; warnings: string[] } {
    const errors: string[] = []
    const warnings: string[] = []

    // Check required fields
    if (template.schema.required) {
      for (const field of template.schema.required) {
        if (!variables[field] || variables[field] === '') {
          errors.push(`Required field '${field}' is missing`)
        }
      }
    }

    // Check field validation rules
    if (template.ruleset?.validation_rules) {
      for (const [field, rules] of Object.entries(template.ruleset.validation_rules as Record<string, any>)) {
        const value = variables[field]
        
        if (value !== undefined && value !== null && value !== '') {
          if (rules.min !== undefined && Number(value) < rules.min) {
            errors.push(`${field} must be at least ${rules.min}`)
          }
          
          if (rules.max !== undefined && Number(value) > rules.max) {
            errors.push(`${field} must be at most ${rules.max}`)
          }

          if (rules.pattern && !new RegExp(rules.pattern).test(String(value))) {
            errors.push(`${field} format is invalid`)
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
   * Get template categories
   */
  getTemplateCategories(): string[] {
    return [
      'Purchase Agreement',
      'Listing Agreement',
      'Lease Agreement',
      'Property Disclosure',
      'Inspection Report',
      'Addendum',
      'Amendment',
      'Other',
    ]
  }

  /**
   * Search templates
   */
  async searchTemplates(query: string): Promise<Template[]> {
    const response = await apiClient.get<Template[]>(`/templates/search?q=${encodeURIComponent(query)}`)
    return response.data
  }

  /**
   * Get popular templates
   */
  async getPopularTemplates(limit: number = 10): Promise<Template[]> {
    const response = await apiClient.get<Template[]>(`/templates/popular?limit=${limit}`)
    return response.data
  }

  /**
   * Clone a template
   */
  async cloneTemplate(templateId: string, newName: string): Promise<Template> {
    const response = await apiClient.post<Template>(`/templates/${templateId}/clone`, {
      name: newName,
    })
    return response.data
  }

  /**
   * Get template usage statistics
   */
  async getTemplateStats(templateId: string): Promise<{
    usage_count: number
    recent_usage: Array<{ date: string; count: number }>
    popular_variables: Array<{ name: string; usage_percentage: number }>
  }> {
    const response = await apiClient.get(`/templates/${templateId}/stats`)
    return response.data
  }

  /**
   * Format template variable type for display
   */
  formatVariableType(type: string): string {
    const typeMap = {
      string: 'Text',
      number: 'Number',
      date: 'Date',
      boolean: 'Yes/No',
      email: 'Email',
    }

    return typeMap[type as keyof typeof typeMap] || type
  }

  /**
   * Generate default variables for template
   */
  generateDefaultVariables(template: Template): Record<string, any> {
    const variables: Record<string, any> = {}
    
    if (template.schema?.properties) {
      for (const [name, schema] of Object.entries(template.schema.properties as Record<string, any>)) {
        if (schema.default !== undefined) {
          variables[name] = schema.default
        } else {
          // Set appropriate default based on type
          switch (schema.type) {
            case 'string':
              variables[name] = ''
              break
            case 'number':
              variables[name] = 0
              break
            case 'boolean':
              variables[name] = false
              break
            case 'date':
              variables[name] = new Date().toISOString().split('T')[0]
              break
            default:
              variables[name] = ''
          }
        }
      }
    }

    return variables
  }

  /**
   * Check if template is compatible with deal type
   */
  isTemplateCompatible(template: Template, dealType: string): boolean {
    // This would be based on template metadata or naming conventions
    const templateName = template.name.toLowerCase()
    const dealTypeLower = dealType.toLowerCase()

    if (dealTypeLower.includes('purchase') && templateName.includes('purchase')) {
      return true
    }
    
    if (dealTypeLower.includes('lease') && templateName.includes('lease')) {
      return true
    }
    
    if (dealTypeLower.includes('listing') && templateName.includes('listing')) {
      return true
    }

    return true // Default to compatible if no specific rules
  }
}

export const templateService = new TemplateService()
export default templateService
