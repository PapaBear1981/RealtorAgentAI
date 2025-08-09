"use client"

import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/hooks/use-toast"
import { useDocumentProcessingUpdates } from "@/hooks/useWebSocket"
import { documentService } from "@/services/documentService"
import { useCallback, useEffect, useState } from "react"
import { useDropzone } from "react-dropzone"

interface UploadedFile {
  id: string
  file: File
  preview?: string
  type?: string
  status: 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  extractedData?: {
    title?: string
    parties?: string[]
    propertyAddress?: string
    contractType?: string
    keyTerms?: string[]
  }
}

const DOCUMENT_TYPES = [
  { value: 'purchase-agreement', label: 'Purchase Agreement' },
  { value: 'listing-agreement', label: 'Listing Agreement' },
  { value: 'lease-agreement', label: 'Lease Agreement' },
  { value: 'disclosure', label: 'Property Disclosure' },
  { value: 'inspection-report', label: 'Inspection Report' },
  { value: 'appraisal', label: 'Appraisal Report' },
  { value: 'title-document', label: 'Title Document' },
  { value: 'other', label: 'Other' },
]

export default function DocumentsPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const { toast } = useToast()

  // WebSocket integration for real-time document processing updates
  useDocumentProcessingUpdates((update) => {
    setUploadedFiles(prev => prev.map(file => {
      if (file.id === update.document_id) {
        return {
          ...file,
          status: update.status,
          progress: update.progress || file.progress,
          extractedData: update.extracted_data || file.extractedData,
        }
      }
      return file
    }))

    // Show toast notifications for status changes
    if (update.status === 'completed') {
      toast({
        title: "Document processed",
        description: "Document processing completed successfully.",
      })
    } else if (update.status === 'error') {
      toast({
        title: "Processing failed",
        description: update.error_message || "Document processing failed.",
        variant: "destructive",
      })
    }
  })

  // Load existing documents on component mount
  useEffect(() => {
    const loadExistingDocuments = async () => {
      try {
        const documents = await documentService.getDocuments()

        const existingFiles: UploadedFile[] = documents.map(doc => ({
          id: doc.id,
          file: new File([], doc.original_filename, { type: doc.content_type }),
          status: doc.status as 'uploading' | 'processing' | 'completed' | 'error',
          progress: doc.status === 'completed' ? 100 : 0,
          type: documentService.getFileTypeCategory(doc.content_type),
        }))

        // Load processing results for completed documents
        for (const file of existingFiles) {
          if (file.status === 'completed') {
            try {
              const processingResult = await documentService.getProcessingResult(file.id)
              if (processingResult) {
                file.extractedData = processingResult.extracted_data
              }
            } catch (error) {
              console.warn(`Failed to load processing result for ${file.id}:`, error)
            }
          }
        }

        setUploadedFiles(existingFiles)
      } catch (error) {
        console.error('Failed to load existing documents:', error)
        toast({
          title: "Failed to load documents",
          description: "Could not load existing documents. Please refresh the page.",
          variant: "destructive",
        })
      } finally {
        setIsLoading(false)
      }
    }

    loadExistingDocuments()
  }, [])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    // Validate files before upload
    const validFiles = acceptedFiles.filter(file => {
      const validation = documentService.validateFile(file)
      if (!validation.valid) {
        toast({
          title: "File validation failed",
          description: `${file.name}: ${validation.error}`,
          variant: "destructive",
        })
        return false
      }
      return true
    })

    if (validFiles.length === 0) return

    // Create initial file entries
    const newFiles: UploadedFile[] = validFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      status: 'uploading',
      progress: 0,
    }))

    setUploadedFiles(prev => [...prev, ...newFiles])

    // Upload files with real API calls
    newFiles.forEach(uploadedFile => {
      handleFileUpload(uploadedFile)
    })

    toast({
      title: "Files uploading",
      description: `${validFiles.length} file(s) started uploading.`,
    })
  }, [toast])

  const handleFileUpload = async (uploadedFile: UploadedFile) => {
    try {
      // Upload file with progress tracking
      const documentUpload = await documentService.uploadFile(
        uploadedFile.file,
        undefined, // dealId - could be passed from props or context
        (progress) => {
          setUploadedFiles(prev => prev.map(file =>
            file.id === uploadedFile.id
              ? { ...file, progress: progress.percentage }
              : file
          ))
        }
      )

      // Update file status to processing
      setUploadedFiles(prev => prev.map(file =>
        file.id === uploadedFile.id
          ? {
              ...file,
              status: 'processing',
              progress: 0,
              id: documentUpload.id // Use real document ID
            }
          : file
      ))

      // Start document processing
      try {
        const processingResult = await documentService.processDocument(documentUpload.id)

        // Update with extracted data
        setUploadedFiles(prev => prev.map(file =>
          file.id === uploadedFile.id || file.id === documentUpload.id
            ? {
                ...file,
                id: documentUpload.id,
                status: 'completed',
                progress: 100,
                extractedData: processingResult.extracted_data,
                type: documentService.getFileTypeCategory(documentUpload.content_type)
              }
            : file
        ))

        toast({
          title: "Document processed",
          description: `${uploadedFile.file.name} has been processed successfully.`,
        })

      } catch (processingError) {
        console.error('Document processing failed:', processingError)

        // Mark as completed but without extracted data
        setUploadedFiles(prev => prev.map(file =>
          file.id === uploadedFile.id || file.id === documentUpload.id
            ? {
                ...file,
                id: documentUpload.id,
                status: 'completed',
                progress: 100,
                type: documentService.getFileTypeCategory(documentUpload.content_type)
              }
            : file
        ))

        toast({
          title: "Processing incomplete",
          description: `${uploadedFile.file.name} uploaded but processing failed.`,
          variant: "destructive",
        })
      }

    } catch (uploadError) {
      console.error('File upload failed:', uploadError)

      setUploadedFiles(prev => prev.map(file =>
        file.id === uploadedFile.id
          ? { ...file, status: 'error', progress: 0 }
          : file
      ))

      toast({
        title: "Upload failed",
        description: `Failed to upload ${uploadedFile.file.name}: ${uploadError instanceof Error ? uploadError.message : 'Unknown error'}`,
        variant: "destructive",
      })
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: documentService.getSupportedFileTypes(),
    maxSize: 10 * 1024 * 1024, // 10MB
  })

  const removeFile = async (fileId: string) => {
    try {
      // Only delete from backend if it's a real document (not just a local upload)
      const fileToRemove = uploadedFiles.find(f => f.id === fileId)
      if (fileToRemove && fileToRemove.status !== 'uploading') {
        await documentService.deleteDocument(fileId)
      }

      setUploadedFiles(prev => {
        const fileToRemove = prev.find(f => f.id === fileId)
        if (fileToRemove?.preview) {
          URL.revokeObjectURL(fileToRemove.preview)
        }
        return prev.filter(f => f.id !== fileId)
      })

      toast({
        title: "File removed",
        description: "Document has been deleted successfully.",
      })
    } catch (error) {
      console.error('Failed to delete file:', error)
      toast({
        title: "Delete failed",
        description: `Failed to delete document: ${error instanceof Error ? error.message : 'Unknown error'}`,
        variant: "destructive",
      })
    }
  }

  const updateFileType = (fileId: string, type: string) => {
    setUploadedFiles(prev => prev.map(file =>
      file.id === fileId ? { ...file, type } : file
    ))
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <Navigation />

        {/* Page Header */}
        <header className="bg-card shadow-sm border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <h1 className="text-3xl font-bold text-foreground">Document Intake</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Upload and process real estate documents with AI-powered extraction
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            {/* Loading State */}
            {isLoading && (
              <Card className="mb-8">
                <CardContent className="p-8 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                  <p className="text-muted-foreground">Loading existing documents...</p>
                </CardContent>
              </Card>
            )}

            {/* Upload Area */}
            {!isLoading && (
              <Card className="mb-8">
              <CardHeader>
                <CardTitle>Upload Documents</CardTitle>
                <CardDescription>
                  Drag and drop files or click to select. Supported formats: PDF, DOC, DOCX, Images, TXT (Max 10MB)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    isDragActive
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <input {...getInputProps()} />
                  <div className="space-y-4">
                    <div className="mx-auto w-12 h-12 text-muted-foreground">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    {isDragActive ? (
                      <p className="text-primary">Drop the files here...</p>
                    ) : (
                      <div>
                        <p className="text-foreground">Drag and drop files here, or click to select</p>
                        <p className="text-sm text-muted-foreground mt-1">PDF, DOC, DOCX, Images, TXT up to 10MB</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
            )}

            {/* Uploaded Files */}
            {uploadedFiles.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Uploaded Documents ({uploadedFiles.length})</CardTitle>
                  <CardDescription>
                    Track the processing status and review extracted information
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {uploadedFiles.map((uploadedFile) => (
                      <div key={uploadedFile.id} className="border rounded-lg p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3">
                              <div className="flex-shrink-0">
                                {uploadedFile.preview ? (
                                  <img
                                    src={uploadedFile.preview}
                                    alt="Preview"
                                    className="w-12 h-12 object-cover rounded"
                                  />
                                ) : (
                                  <div className="w-12 h-12 bg-muted rounded flex items-center justify-center">
                                    <svg className="w-6 h-6 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                  </div>
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-foreground truncate">
                                  {uploadedFile.file.name}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  {documentService.formatFileSize(uploadedFile.file.size)}
                                </p>
                              </div>
                              <div className="flex items-center space-x-2">
                                <Badge variant={
                                  uploadedFile.status === 'completed' ? 'default' :
                                  uploadedFile.status === 'error' ? 'destructive' :
                                  'secondary'
                                }>
                                  {uploadedFile.status}
                                </Badge>
                                {uploadedFile.type && (
                                  <Badge variant="outline">
                                    {DOCUMENT_TYPES.find(t => t.value === uploadedFile.type)?.label}
                                  </Badge>
                                )}
                              </div>
                            </div>

                            {/* Progress Bar */}
                            {(uploadedFile.status === 'uploading' || uploadedFile.status === 'processing') && (
                              <div className="mt-3">
                                <div className="flex justify-between text-sm text-muted-foreground mb-1">
                                  <span>
                                    {uploadedFile.status === 'uploading' ? 'Uploading...' : 'Processing...'}
                                  </span>
                                  <span>{Math.round(uploadedFile.progress)}%</span>
                                </div>
                                <Progress value={uploadedFile.progress} className="h-2" />
                              </div>
                            )}

                            {/* Extracted Data */}
                            {uploadedFile.status === 'completed' && uploadedFile.extractedData && (
                              <div className="mt-4 p-3 bg-muted rounded-lg">
                                <h4 className="text-sm font-medium text-foreground mb-2">Extracted Information</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                  <div>
                                    <span className="font-medium text-foreground">Title:</span>
                                    <p className="text-muted-foreground">{uploadedFile.extractedData.title}</p>
                                  </div>
                                  <div>
                                    <span className="font-medium text-foreground">Property:</span>
                                    <p className="text-muted-foreground">{uploadedFile.extractedData.propertyAddress}</p>
                                  </div>
                                  <div className="md:col-span-2">
                                    <span className="font-medium text-foreground">Parties:</span>
                                    <p className="text-muted-foreground">{uploadedFile.extractedData.parties?.join(', ')}</p>
                                  </div>
                                  <div className="md:col-span-2">
                                    <span className="font-medium text-foreground">Key Terms:</span>
                                    <ul className="text-muted-foreground list-disc list-inside">
                                      {uploadedFile.extractedData.keyTerms?.map((term, index) => (
                                        <li key={index}>{term}</li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(uploadedFile.id)}
                            className="ml-4"
                          >
                            Remove
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
