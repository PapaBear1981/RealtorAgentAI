"use client"

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { useToast } from "@/hooks/use-toast"

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
  const { toast } = useToast()

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      status: 'uploading',
      progress: 0,
    }))

    setUploadedFiles(prev => [...prev, ...newFiles])

    // Simulate upload and processing
    newFiles.forEach(uploadedFile => {
      simulateFileProcessing(uploadedFile.id)
    })

    toast({
      title: "Files uploaded",
      description: `${acceptedFiles.length} file(s) uploaded successfully.`,
    })
  }, [toast])

  const simulateFileProcessing = (fileId: string) => {
    // Simulate upload progress
    let progress = 0
    const uploadInterval = setInterval(() => {
      progress += Math.random() * 30
      if (progress >= 100) {
        progress = 100
        clearInterval(uploadInterval)
        
        // Move to processing
        setUploadedFiles(prev => prev.map(file => 
          file.id === fileId 
            ? { ...file, status: 'processing', progress: 0 }
            : file
        ))

        // Simulate processing
        setTimeout(() => {
          const mockExtractedData = {
            title: 'Residential Purchase Agreement',
            parties: ['John Smith (Buyer)', 'Jane Doe (Seller)'],
            propertyAddress: '123 Main St, Anytown, ST 12345',
            contractType: 'Purchase Agreement',
            keyTerms: ['Purchase Price: $350,000', 'Closing Date: 30 days', 'Contingencies: Inspection, Financing']
          }

          setUploadedFiles(prev => prev.map(file => 
            file.id === fileId 
              ? { 
                  ...file, 
                  status: 'completed', 
                  progress: 100,
                  extractedData: mockExtractedData,
                  type: 'purchase-agreement'
                }
              : file
          ))
        }, 2000)
      } else {
        setUploadedFiles(prev => prev.map(file => 
          file.id === fileId 
            ? { ...file, progress }
            : file
        ))
      }
    }, 200)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
      'text/plain': ['.txt'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  })

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => {
      const fileToRemove = prev.find(f => f.id === fileId)
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview)
      }
      return prev.filter(f => f.id !== fileId)
    })
  }

  const updateFileType = (fileId: string, type: string) => {
    setUploadedFiles(prev => prev.map(file => 
      file.id === fileId ? { ...file, type } : file
    ))
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        
        {/* Page Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <h1 className="text-3xl font-bold text-gray-900">Document Intake</h1>
              <p className="text-sm text-gray-600 mt-1">
                Upload and process real estate documents with AI-powered extraction
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            {/* Upload Area */}
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
                      ? 'border-blue-400 bg-blue-50' 
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <input {...getInputProps()} />
                  <div className="space-y-4">
                    <div className="mx-auto w-12 h-12 text-gray-400">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    {isDragActive ? (
                      <p className="text-blue-600">Drop the files here...</p>
                    ) : (
                      <div>
                        <p className="text-gray-600">Drag and drop files here, or click to select</p>
                        <p className="text-sm text-gray-500 mt-1">PDF, DOC, DOCX, Images, TXT up to 10MB</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

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
                                  <div className="w-12 h-12 bg-gray-200 rounded flex items-center justify-center">
                                    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                  </div>
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {uploadedFile.file.name}
                                </p>
                                <p className="text-sm text-gray-500">
                                  {(uploadedFile.file.size / 1024 / 1024).toFixed(2)} MB
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
                                <div className="flex justify-between text-sm text-gray-600 mb-1">
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
                              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                                <h4 className="text-sm font-medium text-gray-900 mb-2">Extracted Information</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                  <div>
                                    <span className="font-medium text-gray-700">Title:</span>
                                    <p className="text-gray-600">{uploadedFile.extractedData.title}</p>
                                  </div>
                                  <div>
                                    <span className="font-medium text-gray-700">Property:</span>
                                    <p className="text-gray-600">{uploadedFile.extractedData.propertyAddress}</p>
                                  </div>
                                  <div className="md:col-span-2">
                                    <span className="font-medium text-gray-700">Parties:</span>
                                    <p className="text-gray-600">{uploadedFile.extractedData.parties?.join(', ')}</p>
                                  </div>
                                  <div className="md:col-span-2">
                                    <span className="font-medium text-gray-700">Key Terms:</span>
                                    <ul className="text-gray-600 list-disc list-inside">
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
