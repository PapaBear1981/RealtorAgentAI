"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { useToast } from "@/hooks/use-toast"

interface User {
  id: string
  name: string
  email: string
  role: 'admin' | 'agent' | 'tc' | 'signer'
  status: 'active' | 'inactive'
  lastLogin: string
  createdAt: string
}

interface Template {
  id: string
  name: string
  version: string
  category: string
  status: 'active' | 'draft' | 'archived'
  lastModified: string
  author: string
  usageCount: number
}

interface AuditLog {
  id: string
  timestamp: string
  user: string
  action: string
  resource: string
  details: string
  ipAddress: string
}

const MOCK_USERS: User[] = [
  {
    id: '1',
    name: 'John Smith',
    email: 'john.smith@realty.com',
    role: 'agent',
    status: 'active',
    lastLogin: '2024-01-16T10:30:00Z',
    createdAt: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    name: 'Jane Doe',
    email: 'jane.doe@realty.com',
    role: 'agent',
    status: 'active',
    lastLogin: '2024-01-16T14:15:00Z',
    createdAt: '2024-01-02T00:00:00Z'
  },
  {
    id: '3',
    name: 'Mike Johnson',
    email: 'mike.johnson@realty.com',
    role: 'tc',
    status: 'active',
    lastLogin: '2024-01-15T16:45:00Z',
    createdAt: '2024-01-03T00:00:00Z'
  }
]

const MOCK_TEMPLATES: Template[] = [
  {
    id: '1',
    name: 'Residential Purchase Agreement',
    version: '2.1',
    category: 'Purchase',
    status: 'active',
    lastModified: '2024-01-15T12:00:00Z',
    author: 'Admin User',
    usageCount: 45
  },
  {
    id: '2',
    name: 'Listing Agreement',
    version: '1.8',
    category: 'Listing',
    status: 'active',
    lastModified: '2024-01-10T09:30:00Z',
    author: 'Admin User',
    usageCount: 32
  }
]

const MOCK_AUDIT_LOGS: AuditLog[] = [
  {
    id: '1',
    timestamp: '2024-01-16T15:30:00Z',
    user: 'john.smith@realty.com',
    action: 'CONTRACT_GENERATED',
    resource: 'Purchase Agreement - 123 Main St',
    details: 'Generated contract from template',
    ipAddress: '192.168.1.100'
  },
  {
    id: '2',
    timestamp: '2024-01-16T14:15:00Z',
    user: 'jane.doe@realty.com',
    action: 'DOCUMENT_UPLOADED',
    resource: 'Property Disclosure.pdf',
    details: 'Uploaded document for processing',
    ipAddress: '192.168.1.101'
  }
]

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>(MOCK_USERS)
  const [templates, setTemplates] = useState<Template[]>(MOCK_TEMPLATES)
  const [auditLogs] = useState<AuditLog[]>(MOCK_AUDIT_LOGS)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [isEditingUser, setIsEditingUser] = useState(false)
  const { toast } = useToast()

  const handleUserStatusToggle = (userId: string) => {
    setUsers(prev => prev.map(user => 
      user.id === userId 
        ? { ...user, status: user.status === 'active' ? 'inactive' : 'active' }
        : user
    ))
    
    toast({
      title: "User Status Updated",
      description: "User status has been changed successfully.",
    })
  }

  const handleTemplateStatusChange = (templateId: string, newStatus: 'active' | 'draft' | 'archived') => {
    setTemplates(prev => prev.map(template => 
      template.id === templateId 
        ? { ...template, status: newStatus }
        : template
    ))
    
    toast({
      title: "Template Status Updated",
      description: "Template status has been changed successfully.",
    })
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'default'
      case 'agent': return 'secondary'
      case 'tc': return 'outline'
      default: return 'secondary'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'default'
      case 'inactive': return 'destructive'
      case 'draft': return 'secondary'
      case 'archived': return 'outline'
      default: return 'secondary'
    }
  }

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        
        {/* Page Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
              <p className="text-sm text-gray-600 mt-1">
                Manage users, templates, system configuration, and audit trails
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <Tabs defaultValue="users" className="space-y-6">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="users">User Management</TabsTrigger>
                <TabsTrigger value="templates">Templates</TabsTrigger>
                <TabsTrigger value="system">System Config</TabsTrigger>
                <TabsTrigger value="audit">Audit Logs</TabsTrigger>
              </TabsList>

              {/* User Management */}
              <TabsContent value="users" className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2">
                    <Card>
                      <CardHeader>
                        <CardTitle>Users ({users.length})</CardTitle>
                        <CardDescription>
                          Manage user accounts and permissions
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          {users.map((user) => (
                            <div 
                              key={user.id}
                              className={`border rounded-lg p-4 cursor-pointer transition-colors hover:bg-gray-50 ${
                                selectedUser?.id === user.id ? 'ring-2 ring-blue-500' : ''
                              }`}
                              onClick={() => setSelectedUser(user)}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-3">
                                  <Avatar className="w-10 h-10">
                                    <AvatarFallback>
                                      {user.name.split(' ').map(n => n[0]).join('')}
                                    </AvatarFallback>
                                  </Avatar>
                                  <div>
                                    <h3 className="font-medium">{user.name}</h3>
                                    <p className="text-sm text-gray-600">{user.email}</p>
                                    <p className="text-xs text-gray-500">
                                      Last login: {new Date(user.lastLogin).toLocaleString()}
                                    </p>
                                  </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <Badge variant={getRoleColor(user.role)}>
                                    {user.role}
                                  </Badge>
                                  <Badge variant={getStatusColor(user.status)}>
                                    {user.status}
                                  </Badge>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleUserStatusToggle(user.id)
                                    }}
                                  >
                                    {user.status === 'active' ? 'Deactivate' : 'Activate'}
                                  </Button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="lg:col-span-1">
                    {selectedUser ? (
                      <Card>
                        <CardHeader>
                          <CardTitle>User Details</CardTitle>
                          <CardDescription>
                            {selectedUser.name}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            <div>
                              <Label htmlFor="name">Name</Label>
                              <Input id="name" value={selectedUser.name} readOnly />
                            </div>
                            <div>
                              <Label htmlFor="email">Email</Label>
                              <Input id="email" value={selectedUser.email} readOnly />
                            </div>
                            <div>
                              <Label htmlFor="role">Role</Label>
                              <Select value={selectedUser.role}>
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="admin">Admin</SelectItem>
                                  <SelectItem value="agent">Agent</SelectItem>
                                  <SelectItem value="tc">Transaction Coordinator</SelectItem>
                                  <SelectItem value="signer">Signer</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div>
                              <Label>Status</Label>
                              <div className="mt-1">
                                <Badge variant={getStatusColor(selectedUser.status)}>
                                  {selectedUser.status}
                                </Badge>
                              </div>
                            </div>
                            <div>
                              <Label>Created</Label>
                              <p className="text-sm text-gray-600 mt-1">
                                {new Date(selectedUser.createdAt).toLocaleDateString()}
                              </p>
                            </div>
                            <Button className="w-full">
                              Save Changes
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ) : (
                      <Card>
                        <CardContent className="flex items-center justify-center h-64">
                          <p className="text-gray-500">Select a user to view details</p>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              </TabsContent>

              {/* Template Management */}
              <TabsContent value="templates" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Contract Templates ({templates.length})</CardTitle>
                    <CardDescription>
                      Manage contract templates and versions
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {templates.map((template) => (
                        <div key={template.id} className="border rounded-lg p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <h3 className="font-medium">{template.name}</h3>
                              <p className="text-sm text-gray-600">Version {template.version}</p>
                              <p className="text-xs text-gray-500">
                                Modified: {new Date(template.lastModified).toLocaleString()} by {template.author}
                              </p>
                              <p className="text-xs text-gray-500">
                                Used {template.usageCount} times
                              </p>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Badge variant="outline">{template.category}</Badge>
                              <Badge variant={getStatusColor(template.status)}>
                                {template.status}
                              </Badge>
                              <Select
                                value={template.status}
                                onValueChange={(value: 'active' | 'draft' | 'archived') => 
                                  handleTemplateStatusChange(template.id, value)
                                }
                              >
                                <SelectTrigger className="w-32">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="active">Active</SelectItem>
                                  <SelectItem value="draft">Draft</SelectItem>
                                  <SelectItem value="archived">Archived</SelectItem>
                                </SelectContent>
                              </Select>
                              <Button variant="outline" size="sm">
                                Edit
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* System Configuration */}
              <TabsContent value="system" className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>AI Model Configuration</CardTitle>
                      <CardDescription>
                        Configure AI model routing and settings
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="primary-model">Primary Model</Label>
                          <Select defaultValue="gpt-4">
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="gpt-4">GPT-4</SelectItem>
                              <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                              <SelectItem value="claude-3">Claude 3</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label htmlFor="fallback-model">Fallback Model</Label>
                          <Select defaultValue="gpt-3.5-turbo">
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                              <SelectItem value="claude-3">Claude 3</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label htmlFor="token-limit">Token Limit</Label>
                          <Input id="token-limit" type="number" defaultValue="4000" />
                        </div>
                        <Button>Save Configuration</Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>System Settings</CardTitle>
                      <CardDescription>
                        General system configuration
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="max-file-size">Max File Size (MB)</Label>
                          <Input id="max-file-size" type="number" defaultValue="10" />
                        </div>
                        <div>
                          <Label htmlFor="session-timeout">Session Timeout (hours)</Label>
                          <Input id="session-timeout" type="number" defaultValue="8" />
                        </div>
                        <div>
                          <Label htmlFor="backup-retention">Backup Retention (days)</Label>
                          <Input id="backup-retention" type="number" defaultValue="30" />
                        </div>
                        <Button>Save Settings</Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              {/* Audit Logs */}
              <TabsContent value="audit" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Audit Trail ({auditLogs.length})</CardTitle>
                    <CardDescription>
                      System activity and security audit logs
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {auditLogs.map((log) => (
                        <div key={log.id} className="border rounded-lg p-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center space-x-2">
                                <Badge variant="outline">{log.action}</Badge>
                                <span className="text-sm font-medium">{log.user}</span>
                              </div>
                              <p className="text-sm text-gray-600 mt-1">{log.resource}</p>
                              <p className="text-xs text-gray-500 mt-1">{log.details}</p>
                              <p className="text-xs text-gray-400 mt-1">
                                IP: {log.ipAddress}
                              </p>
                            </div>
                            <div className="text-xs text-gray-500">
                              {new Date(log.timestamp).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
