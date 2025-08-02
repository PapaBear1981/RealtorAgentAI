"use client"

import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/hooks/use-toast"
import { useState } from "react"

interface SignatureParty {
  id: string
  name: string
  email: string
  role: string
  status: 'pending' | 'signed' | 'declined' | 'expired'
  signedAt?: string
  ipAddress?: string
}

interface SignatureRequest {
  id: string
  documentName: string
  documentType: string
  createdAt: string
  dueDate: string
  status: 'draft' | 'sent' | 'in-progress' | 'completed' | 'expired'
  parties: SignatureParty[]
  completionPercentage: number
  lastActivity: string
}

const MOCK_SIGNATURE_REQUESTS: SignatureRequest[] = [
  {
    id: '1',
    documentName: 'Purchase Agreement - 123 Main St',
    documentType: 'Purchase Agreement',
    createdAt: '2024-01-15',
    dueDate: '2024-01-30',
    status: 'in-progress',
    lastActivity: '2 hours ago',
    completionPercentage: 66,
    parties: [
      {
        id: '1',
        name: 'John Smith',
        email: 'john.smith@email.com',
        role: 'Buyer',
        status: 'signed',
        signedAt: '2024-01-16T10:30:00Z',
        ipAddress: '192.168.1.100'
      },
      {
        id: '2',
        name: 'Jane Doe',
        email: 'jane.doe@email.com',
        role: 'Seller',
        status: 'signed',
        signedAt: '2024-01-16T14:15:00Z',
        ipAddress: '192.168.1.101'
      },
      {
        id: '3',
        name: 'Mike Johnson',
        email: 'mike.johnson@realty.com',
        role: 'Agent',
        status: 'pending'
      }
    ]
  },
  {
    id: '2',
    documentName: 'Listing Agreement - 456 Oak Ave',
    documentType: 'Listing Agreement',
    createdAt: '2024-01-10',
    dueDate: '2024-01-25',
    status: 'completed',
    lastActivity: '3 days ago',
    completionPercentage: 100,
    parties: [
      {
        id: '4',
        name: 'Sarah Wilson',
        email: 'sarah.wilson@email.com',
        role: 'Seller',
        status: 'signed',
        signedAt: '2024-01-12T09:00:00Z',
        ipAddress: '192.168.1.102'
      },
      {
        id: '5',
        name: 'Tom Brown',
        email: 'tom.brown@realty.com',
        role: 'Agent',
        status: 'signed',
        signedAt: '2024-01-12T11:30:00Z',
        ipAddress: '192.168.1.103'
      }
    ]
  },
  {
    id: '3',
    documentName: 'Property Disclosure - 789 Pine St',
    documentType: 'Disclosure',
    createdAt: '2024-01-20',
    dueDate: '2024-02-05',
    status: 'sent',
    lastActivity: '1 day ago',
    completionPercentage: 0,
    parties: [
      {
        id: '6',
        name: 'Robert Davis',
        email: 'robert.davis@email.com',
        role: 'Seller',
        status: 'pending'
      },
      {
        id: '7',
        name: 'Lisa Garcia',
        email: 'lisa.garcia@email.com',
        role: 'Buyer',
        status: 'pending'
      }
    ]
  }
]

export default function SignaturesPage() {
  const [signatureRequests] = useState<SignatureRequest[]>(MOCK_SIGNATURE_REQUESTS)
  const [selectedRequest, setSelectedRequest] = useState<SignatureRequest | null>(null)
  const { toast } = useToast()

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'default'
      case 'in-progress': return 'secondary'
      case 'sent': return 'outline'
      case 'expired': return 'destructive'
      default: return 'secondary'
    }
  }

  const getPartyStatusColor = (status: string) => {
    switch (status) {
      case 'signed': return 'default'
      case 'pending': return 'secondary'
      case 'declined': return 'destructive'
      case 'expired': return 'destructive'
      default: return 'secondary'
    }
  }

  const sendReminder = (partyId: string) => {
    toast({
      title: "Reminder Sent",
      description: "A reminder email has been sent to the signer.",
    })
  }

  const resendDocument = (requestId: string) => {
    toast({
      title: "Document Resent",
      description: "The signature request has been resent to all pending parties.",
    })
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        <Navigation />

        {/* Page Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <h1 className="text-3xl font-bold text-gray-900">Signature Tracker</h1>
              <p className="text-sm text-gray-600 mt-1">
                Track multi-party signatures with audit trails and notifications
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Signature Requests List */}
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Signature Requests</CardTitle>
                    <CardDescription>
                      Manage and track all your signature requests
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {signatureRequests.map((request) => (
                        <div
                          key={request.id}
                          className={`border rounded-lg p-4 cursor-pointer transition-colors hover:bg-gray-50 ${
                            selectedRequest?.id === request.id ? 'ring-2 ring-blue-500' : ''
                          }`}
                          onClick={() => setSelectedRequest(request)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h3 className="font-medium text-gray-900">{request.documentName}</h3>
                              <p className="text-sm text-gray-600 mt-1">{request.documentType}</p>

                              <div className="flex items-center space-x-4 mt-3">
                                <Badge variant={getStatusColor(request.status)}>
                                  {request.status.replace('-', ' ')}
                                </Badge>
                                <span className="text-sm text-gray-500">
                                  Due: {new Date(request.dueDate).toLocaleDateString()}
                                </span>
                                <span className="text-sm text-gray-500">
                                  Last activity: {request.lastActivity}
                                </span>
                              </div>

                              {/* Progress */}
                              <div className="mt-3">
                                <div className="flex justify-between text-sm text-gray-600 mb-1">
                                  <span>Completion Progress</span>
                                  <span>{request.completionPercentage}%</span>
                                </div>
                                <Progress value={request.completionPercentage} className="h-2" />
                              </div>

                              {/* Party Avatars */}
                              <div className="flex items-center space-x-2 mt-3">
                                <span className="text-sm text-gray-600">Parties:</span>
                                {request.parties.map((party) => (
                                  <div key={party.id} className="flex items-center space-x-1">
                                    <Avatar className="w-6 h-6">
                                      <AvatarFallback className="text-xs">
                                        {party.name.split(' ').map(n => n[0]).join('')}
                                      </AvatarFallback>
                                    </Avatar>
                                    <Badge
                                      variant={getPartyStatusColor(party.status)}
                                      className="text-xs"
                                    >
                                      {party.status}
                                    </Badge>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Request Details */}
              <div className="lg:col-span-1">
                {selectedRequest ? (
                  <Card>
                    <CardHeader>
                      <CardTitle>Request Details</CardTitle>
                      <CardDescription>
                        {selectedRequest.documentName}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {/* Document Info */}
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Document Information</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">Type:</span>
                              <span>{selectedRequest.documentType}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Created:</span>
                              <span>{new Date(selectedRequest.createdAt).toLocaleDateString()}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Due Date:</span>
                              <span>{new Date(selectedRequest.dueDate).toLocaleDateString()}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Status:</span>
                              <Badge variant={getStatusColor(selectedRequest.status)}>
                                {selectedRequest.status.replace('-', ' ')}
                              </Badge>
                            </div>
                          </div>
                        </div>

                        {/* Parties */}
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Signing Parties</h4>
                          <div className="space-y-3">
                            {selectedRequest.parties.map((party) => (
                              <div key={party.id} className="border rounded-lg p-3">
                                <div className="flex items-start justify-between">
                                  <div className="flex items-center space-x-3">
                                    <Avatar className="w-8 h-8">
                                      <AvatarFallback>
                                        {party.name.split(' ').map(n => n[0]).join('')}
                                      </AvatarFallback>
                                    </Avatar>
                                    <div>
                                      <p className="font-medium text-sm">{party.name}</p>
                                      <p className="text-xs text-gray-600">{party.role}</p>
                                      <p className="text-xs text-gray-500">{party.email}</p>
                                    </div>
                                  </div>
                                  <Badge variant={getPartyStatusColor(party.status)}>
                                    {party.status}
                                  </Badge>
                                </div>

                                {party.signedAt && (
                                  <div className="mt-2 text-xs text-gray-500">
                                    <p>Signed: {new Date(party.signedAt).toLocaleString()}</p>
                                    {party.ipAddress && <p>IP: {party.ipAddress}</p>}
                                  </div>
                                )}

                                {party.status === 'pending' && (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="mt-2 w-full"
                                    onClick={() => sendReminder(party.id)}
                                  >
                                    Send Reminder
                                  </Button>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="space-y-2">
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={() => resendDocument(selectedRequest.id)}
                          >
                            Resend Document
                          </Button>
                          <Button variant="outline" className="w-full">
                            Download Audit Trail
                          </Button>
                          <Button variant="outline" className="w-full">
                            View Document
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardContent className="flex items-center justify-center h-64">
                      <p className="text-gray-500">Select a signature request to view details</p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
