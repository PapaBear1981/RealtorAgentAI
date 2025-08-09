/**
 * Document service for file upload and processing operations.
 * 
 * This service handles all document-related API calls including:
 * - File upload to MinIO storage
 * - Document processing and AI extraction
 * - File management and metadata
 */

import { apiClient } from './apiClient'

export interface DocumentUpload {
  id: string
  filename: string
  original_filename: string
  content_type: string
  file_size: number
  file_type: string
  status: 'uploading' | 'processing' | 'completed' | 'error'
  storage_path: string
  owner_id: string
  deal_id?: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

export interface DocumentProcessingResult {
  id: string
  document_id: string
  extracted_data: {
    title?: string
    parties?: string[]
    property_address?: string
    contract_type?: string
    key_terms?: string[]
    personal_info?: {
      name?: string
      email?: string
      phone?: string
    }
    property_info?: {
      address?: string
      price?: string
      sqft?: string
      bedrooms?: string
      bathrooms?: string
    }
    financial_info?: {
      down_payment?: string
      loan_amount?: string
      credit_score?: string
    }
  }
  processing_time: number
  confidence_score: number
  created_at: string
}

export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}

class DocumentService {
  /**
   * Upload a file to the server
   */
  async uploadFile(
    file: File,
    dealId?: string,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<DocumentUpload> {
    const formData = new FormData()
    formData.append('file', file)
    if (dealId) {
      formData.append('deal_id', dealId)
    }

    // Create XMLHttpRequest for progress tracking
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      
      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          const progress: UploadProgress = {
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100)
          }
          onProgress(progress)
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText)
            resolve(response)
          } catch (error) {
            reject(new Error('Invalid response format'))
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`))
        }
      })

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed: Network error'))
      })

      // Set up request
      const baseUrl = apiClient.getBaseUrl()
      xhr.open('POST', `${baseUrl}/files/upload`)
      
      // Add auth header
      const token = localStorage.getItem('auth-token') // Fallback token retrieval
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      }

      xhr.send(formData)
    })
  }

  /**
   * Get document by ID
   */
  async getDocument(documentId: string): Promise<DocumentUpload> {
    const response = await apiClient.get<DocumentUpload>(`/files/${documentId}`)
    return response.data
  }

  /**
   * Get all documents for a user
   */
  async getDocuments(dealId?: string): Promise<DocumentUpload[]> {
    const endpoint = dealId ? `/files?deal_id=${dealId}` : '/files'
    const response = await apiClient.get<DocumentUpload[]>(endpoint)
    return response.data
  }

  /**
   * Process document with AI extraction
   */
  async processDocument(documentId: string): Promise<DocumentProcessingResult> {
    const response = await apiClient.post<DocumentProcessingResult>(
      `/files/${documentId}/process`
    )
    return response.data
  }

  /**
   * Get processing result for a document
   */
  async getProcessingResult(documentId: string): Promise<DocumentProcessingResult | null> {
    try {
      const response = await apiClient.get<DocumentProcessingResult>(
        `/files/${documentId}/processing-result`
      )
      return response.data
    } catch (error) {
      // Return null if no processing result exists yet
      return null
    }
  }

  /**
   * Delete a document
   */
  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/files/${documentId}`)
  }

  /**
   * Download a document
   */
  async downloadDocument(documentId: string, filename?: string): Promise<void> {
    await apiClient.downloadFile(`/files/${documentId}/download`, filename)
  }

  /**
   * Update document metadata
   */
  async updateDocument(
    documentId: string,
    updates: Partial<Pick<DocumentUpload, 'filename' | 'file_type'>>
  ): Promise<DocumentUpload> {
    const response = await apiClient.patch<DocumentUpload>(`/files/${documentId}`, updates)
    return response.data
  }

  /**
   * Get supported file types
   */
  getSupportedFileTypes(): Record<string, string[]> {
    return {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
      'text/plain': ['.txt'],
    }
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File, maxSizeBytes: number = 10 * 1024 * 1024): { valid: boolean; error?: string } {
    // Check file size
    if (file.size > maxSizeBytes) {
      return {
        valid: false,
        error: `File size exceeds ${Math.round(maxSizeBytes / 1024 / 1024)}MB limit`
      }
    }

    // Check file type
    const supportedTypes = this.getSupportedFileTypes()
    const isSupported = Object.keys(supportedTypes).some(type => {
      if (type.endsWith('/*')) {
        return file.type.startsWith(type.replace('/*', '/'))
      }
      return file.type === type
    })

    if (!isSupported) {
      return {
        valid: false,
        error: 'File type not supported'
      }
    }

    return { valid: true }
  }

  /**
   * Get file type category
   */
  getFileTypeCategory(contentType: string): string {
    if (contentType.startsWith('image/')) return 'image'
    if (contentType.includes('pdf')) return 'document'
    if (contentType.includes('word') || contentType.includes('document')) return 'document'
    if (contentType.includes('text')) return 'text'
    return 'other'
  }

  /**
   * Format file size for display
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes'
    
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }
}

export const documentService = new DocumentService()
export default documentService
