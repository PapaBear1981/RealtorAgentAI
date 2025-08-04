"use client"

import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import { useCallback, useEffect, useState } from "react"

interface Comment {
  id: string
  author: string
  content: string
  timestamp: string
  lineNumber?: number
  resolved: boolean
  replies: Comment[]
}

interface Change {
  id: string
  type: 'addition' | 'deletion' | 'modification'
  lineNumber: number
  oldText?: string
  newText?: string
  author: string
  timestamp: string
}

interface Version {
  id: string
  number: number
  title: string
  author: string
  timestamp: string
  changes: Change[]
  status: 'draft' | 'review' | 'approved' | 'rejected' | 'changes_requested'
  content: string
}

const VERSION_1_TEXT = `RESIDENTIAL PURCHASE AGREEMENT

This Purchase Agreement is made between John Smith ("Buyer") and Jane Doe ("Seller") for the purchase of the property located at:

123 Main Street, Anytown, ST 12345

PURCHASE TERMS:
- Purchase Price: $350,000
- Earnest Money: $5,000
- Financing: Conventional
- Closing Date: February 15, 2024

ADDITIONAL TERMS:
- Property sold "as is" with right to inspect
- Seller to provide clear title
- Buyer responsible for all inspections

CONTINGENCIES:
- Financing contingency: 30 days
- Inspection contingency: 10 days
- Appraisal contingency: 21 days

This agreement is binding upon execution by all parties.

Buyer: _________________ Date: _________
John Smith

Seller: _________________ Date: _________
Jane Doe`

const VERSION_2_TEXT = `RESIDENTIAL PURCHASE AGREEMENT

This Purchase Agreement is made between John Smith ("Buyer") and Jane Doe ("Seller") for the purchase of the property located at:

123 Main Street, Anytown, ST 12345

PURCHASE TERMS:
- Purchase Price: $365,000
- Earnest Money: $5,000
- Financing: Conventional
- Closing Date: February 15, 2024

ADDITIONAL TERMS:
- Property sold "as is" with right to inspect
- Seller to provide clear title
- Buyer responsible for all inspections
- Seller agrees to provide home warranty for one year.

CONTINGENCIES:
- Financing contingency: 30 days
- Inspection contingency: 10 days
- Appraisal contingency: 21 days

This agreement is binding upon execution by all parties.

Buyer: _________________ Date: _________
John Smith

Seller: _________________ Date: _________
Jane Doe`

const MOCK_VERSIONS: Version[] = [
  {
    id: '1',
    number: 1,
    title: 'Initial Draft',
    author: 'John Smith',
    timestamp: '2024-01-15T10:00:00Z',
    status: 'approved',
    changes: [],
    content: VERSION_1_TEXT,
  },
  {
    id: '2',
    number: 2,
    title: 'Updated Purchase Price',
    author: 'Jane Doe',
    timestamp: '2024-01-16T14:30:00Z',
    status: 'review',
    changes: [
      {
        id: '1',
        type: 'modification',
        lineNumber: 15,
        oldText: 'Purchase Price: $350,000',
        newText: 'Purchase Price: $365,000',
        author: 'Jane Doe',
        timestamp: '2024-01-16T14:30:00Z',
      },
      {
        id: '2',
        type: 'addition',
        lineNumber: 25,
        newText: 'Seller agrees to provide home warranty for one year.',
        author: 'Jane Doe',
        timestamp: '2024-01-16T14:30:00Z',
      },
    ],
    content: VERSION_2_TEXT,
  },
]

const MOCK_COMMENTS: Comment[] = [
  {
    id: '1',
    author: 'Mike Johnson',
    content: 'The price increase looks reasonable given the current market conditions.',
    timestamp: '2024-01-16T15:00:00Z',
    lineNumber: 15,
    resolved: false,
    replies: [
      {
        id: '2',
        author: 'John Smith',
        content: 'Agreed. The appraisal supports this value.',
        timestamp: '2024-01-16T15:30:00Z',
        resolved: false,
        replies: []
      }
    ]
  },
  {
    id: '3',
    author: 'Sarah Wilson',
    content: 'Should we specify which home warranty company?',
    timestamp: '2024-01-16T16:00:00Z',
    lineNumber: 25,
    resolved: false,
    replies: []
  }
]


export default function ReviewPage() {
  const [versions, setVersions] = useState<Version[]>(MOCK_VERSIONS)
  const [selectedVersion, setSelectedVersion] = useState<Version>(MOCK_VERSIONS[1])
  const [comments, setComments] = useState<Comment[]>(MOCK_COMMENTS)
  const [newComment, setNewComment] = useState('')
  const [selectedLine, setSelectedLine] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState('redline')
  const [replyingTo, setReplyingTo] = useState<string | null>(null)
  const [replyContent, setReplyContent] = useState('')
  const { toast } = useToast()

  const previousVersion = versions.find(v => v.number === selectedVersion.number - 1)

  const selectVersion = (id: string) => {
    const version = versions.find(v => v.id === id)
    if (version) setSelectedVersion(version)
  }

  const updateVersionStatus = (status: Version['status']) => {
    setVersions(prev => prev.map(v => (v.id === selectedVersion.id ? { ...v, status } : v)))
    setSelectedVersion(prev => ({ ...prev, status }))
  }

  const handleApprove = () => {
    updateVersionStatus('approved')
    toast({
      title: "Version Approved",
      description: "The contract version has been approved successfully.",
    })
  }

  const handleRequestChanges = () => {
    updateVersionStatus('changes_requested')
    toast({
      title: "Changes Requested",
      description: "Change request has been sent to the author.",
      variant: "destructive",
    })
  }

  const addReply = (parentId: string) => {
    if (!replyContent.trim()) return

    const reply: Comment = {
      id: `reply-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      author: 'Current User',
      content: replyContent,
      timestamp: new Date().toISOString(),
      resolved: false,
      replies: [],
    }

    const addReplyToComment = (commentsList: Comment[]): Comment[] =>
      commentsList.map(c => {
        if (c.id === parentId) {
          return { ...c, replies: [...c.replies, reply] }
        }
        return { ...c, replies: addReplyToComment(c.replies) }
      })

    setComments(prev => addReplyToComment(prev))
    setReplyContent('')
    setReplyingTo(null)

    toast({
      title: "Reply Added",
      description: "Your reply has been added to the discussion.",
    })
  }

  const renderBeforeAfter = (before: Version, after: Version) => {
    const beforeLines = before.content.split('\n')
    const afterLines = after.content.split('\n')
    const maxLines = Math.max(beforeLines.length, afterLines.length)

    return Array.from({ length: maxLines }, (_, i) => {
      const beforeLine = beforeLines[i] || ''
      const afterLine = afterLines[i] || ''
      const changed = beforeLine !== afterLine
      return (
        <div key={i} className="grid grid-cols-2 gap-4 py-1 px-2">
          <div
            className={`flex space-x-2 rounded px-2 ${
              changed ? 'bg-red-50 line-through text-red-800' : 'text-gray-900'
            }`}
          >
            <span className="text-xs text-gray-400 w-8 select-none">{i + 1}</span>
            <span className="flex-1">{beforeLine}</span>
          </div>
          <div
            className={`flex space-x-2 rounded px-2 ${
              changed ? 'bg-green-50 text-green-800' : 'text-gray-900'
            }`}
          >
            <span className="text-xs text-gray-400 w-8 select-none">{i + 1}</span>
            <span className="flex-1">{afterLine}</span>
          </div>
        </div>
      )
    })
  }

  // Keyboard shortcuts
  const handleKeyPress = useCallback((event: KeyboardEvent) => {
    if (event.ctrlKey || event.metaKey) return

    switch (event.key.toLowerCase()) {
      case 'a':
        event.preventDefault()
        handleApprove()
        break
      case 'r':
        event.preventDefault()
        handleRequestChanges()
        break
    }
  }, [handleApprove, handleRequestChanges])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress)
    return () => document.removeEventListener('keydown', handleKeyPress)
  }, [handleKeyPress])

  const addComment = () => {
    if (!newComment.trim()) return

    const comment: Comment = {
      id: `comment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      author: 'Current User',
      content: newComment,
      timestamp: new Date().toISOString(),
      lineNumber: selectedLine || undefined,
      resolved: false,
      replies: []
    }

    setComments(prev => [...prev, comment])
    setNewComment('')
    setSelectedLine(null)

    toast({
      title: "Comment Added",
      description: "Your comment has been added to the review.",
    })
  }

  const getLineComments = (lineNumber: number) => {
    return comments.filter(comment => comment.lineNumber === lineNumber)
  }

  const renderContractWithChanges = () => {
    const lines = selectedVersion.content.split('\n')
    const changes = selectedVersion.changes

    return lines.map((line, index) => {
      const lineNumber = index + 1
      const lineChanges = changes.filter(change => change.lineNumber === lineNumber)
      const lineComments = getLineComments(lineNumber)

      return (
        <div key={lineNumber} className="group relative">
          <div
            className={`flex items-start space-x-4 py-1 px-2 rounded hover:bg-gray-50 cursor-pointer ${
              selectedLine === lineNumber ? 'bg-blue-50' : ''
            }`}
            onClick={() => setSelectedLine(lineNumber)}
          >
            <span className="text-xs text-gray-400 w-8 flex-shrink-0 select-none">
              {lineNumber}
            </span>
            <div className="flex-1">
              {lineChanges.map(change => (
                <div key={change.id} className="mb-1">
                  {change.type === 'deletion' && change.oldText && (
                    <div className="bg-red-100 text-red-800 px-2 py-1 rounded line-through">
                      {change.oldText}
                    </div>
                  )}
                  {change.type === 'addition' && change.newText && (
                    <div className="bg-green-100 text-green-800 px-2 py-1 rounded">
                      {change.newText}
                    </div>
                  )}
                  {change.type === 'modification' && (
                    <div className="space-y-1">
                      {change.oldText && (
                        <div className="bg-red-100 text-red-800 px-2 py-1 rounded line-through">
                          {change.oldText}
                        </div>
                      )}
                      {change.newText && (
                        <div className="bg-green-100 text-green-800 px-2 py-1 rounded">
                          {change.newText}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {lineChanges.length === 0 && (
                <div className="text-gray-900">{line}</div>
              )}

              {/* Line Comments */}
              {lineComments.length > 0 && (
                <div className="mt-2 space-y-2">
              {lineComments.map(comment => (
                <div key={comment.id} className="bg-yellow-50 border-l-4 border-yellow-400 p-2 rounded">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900">{comment.author}</span>
                    <span className="text-xs text-gray-500">
                      {new Date(comment.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">{comment.content}</p>
                  <div className="mt-1">
                    <Button variant="link" size="xs" onClick={() => setReplyingTo(comment.id)}>
                      Reply
                    </Button>
                  </div>
                  {replyingTo === comment.id && (
                    <div className="mt-2 space-y-2">
                      <Textarea
                        rows={2}
                        value={replyContent}
                        onChange={(e) => setReplyContent(e.target.value)}
                        placeholder="Write a reply..."
                      />
                      <div className="flex space-x-2">
                        <Button
                          size="sm"
                          onClick={() => addReply(comment.id)}
                          disabled={!replyContent.trim()}
                        >
                          Send
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setReplyingTo(null)
                            setReplyContent('')
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                  {comment.replies.length > 0 && (
                    <div className="mt-2 ml-4 space-y-1">
                      {comment.replies.map(reply => (
                        <div key={reply.id} className="bg-white p-2 rounded border">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-gray-800">{reply.author}</span>
                            <span className="text-xs text-gray-500">
                              {new Date(reply.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-xs text-gray-600">{reply.content}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
                </div>
              )}
            </div>

            {/* Comment indicator */}
            {lineComments.length > 0 && (
              <div className="flex-shrink-0">
                <Badge variant="secondary" className="text-xs">
                  {lineComments.length}
                </Badge>
              </div>
            )}
          </div>
        </div>
      )
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
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">Contract Review</h1>
                  <p className="text-sm text-gray-600 mt-1">
                    Review changes, add comments, and approve contract versions
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant="secondary">Keyboard: A = Approve, R = Request Changes</Badge>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Main Content */}
              <div className="lg:col-span-3">
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="redline">Redline View</TabsTrigger>
                    <TabsTrigger value="versions">Version History</TabsTrigger>
                    <TabsTrigger value="comments">All Comments</TabsTrigger>
                  </TabsList>

                  <TabsContent value="redline" className="space-y-6">
                    <Card>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle>Version {selectedVersion.number}: {selectedVersion.title}</CardTitle>
                            <CardDescription>
                              By {selectedVersion.author} on {new Date(selectedVersion.timestamp).toLocaleString()}
                            </CardDescription>
                          </div>
                          <Badge
                            variant={
                              selectedVersion.status === 'approved'
                                ? 'default'
                                : selectedVersion.status === 'rejected' || selectedVersion.status === 'changes_requested'
                                  ? 'destructive'
                                  : 'secondary'
                            }
                          >
                            {selectedVersion.status}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <Tabs defaultValue="unified">
                          <TabsList className="grid w-full grid-cols-2 mb-4">
                            <TabsTrigger value="unified">Redline</TabsTrigger>
                            <TabsTrigger value="split">Before/After</TabsTrigger>
                          </TabsList>
                          <TabsContent value="unified">
                            <div className="bg-white border rounded-lg p-4 font-mono text-sm max-h-96 overflow-y-auto">
                              {renderContractWithChanges()}
                            </div>
                          </TabsContent>
                          <TabsContent value="split">
                            {previousVersion ? (
                              <div className="bg-white border rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
                                {renderBeforeAfter(previousVersion, selectedVersion)}
                              </div>
                            ) : (
                              <div className="text-sm text-gray-600">No previous version for comparison</div>
                            )}
                          </TabsContent>
                        </Tabs>

                        <div className="mt-6 flex justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-600">
                              {selectedVersion.changes.length} changes in this version
                            </span>
                          </div>
                          <div className="flex space-x-2">
                            <Button
                              variant="destructive"
                              onClick={handleRequestChanges}
                              className="flex items-center space-x-1"
                            >
                              <span>Request Changes</span>
                              <kbd className="ml-1 px-1 py-0.5 text-xs bg-red-200 rounded">R</kbd>
                            </Button>
                            <Button onClick={handleApprove} className="flex items-center space-x-1">
                              <span>Approve</span>
                              <kbd className="ml-1 px-1 py-0.5 text-xs bg-green-200 rounded">A</kbd>
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="versions" className="space-y-6">
                    <Card>
                      <CardHeader>
                        <CardTitle>Version History</CardTitle>
                        <CardDescription>
                          Track all changes and revisions to this contract
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          {versions.map((version) => (
                            <div
                              key={version.id}
                              className={`border rounded-lg p-4 cursor-pointer transition-colors hover:bg-gray-50 ${
                                selectedVersion.id === version.id ? 'ring-2 ring-blue-500' : ''
                              }`}
                              onClick={() => selectVersion(version.id)}
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <h3 className="font-medium">Version {version.number}: {version.title}</h3>
                                  <p className="text-sm text-gray-600">
                                    By {version.author} on {new Date(version.timestamp).toLocaleString()}
                                  </p>
                                  <p className="text-sm text-gray-500 mt-1">
                                    {version.changes.length} changes
                                  </p>
                                </div>
                                <Badge
                                  variant={
                                    version.status === 'approved'
                                      ? 'default'
                                      : version.status === 'rejected' || version.status === 'changes_requested'
                                        ? 'destructive'
                                        : 'secondary'
                                  }
                                >
                                  {version.status}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                    {previousVersion && (
                      <Card>
                        <CardHeader>
                          <CardTitle>Version Diff</CardTitle>
                          <CardDescription>
                            Comparing version {selectedVersion.number} with version {previousVersion.number}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="bg-white border rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
                            {renderBeforeAfter(previousVersion, selectedVersion)}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </TabsContent>

                  <TabsContent value="comments" className="space-y-6">
                    <Card>
                      <CardHeader>
                        <CardTitle>All Comments</CardTitle>
                        <CardDescription>
                          Review and respond to all comments on this contract
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          {comments.map((comment) => (
                            <div key={comment.id} className="border rounded-lg p-4">
                              <div className="flex items-start space-x-3">
                                <Avatar className="w-8 h-8">
                                  <AvatarFallback>
                                    {comment.author.split(' ').map(n => n[0]).join('')}
                                  </AvatarFallback>
                                </Avatar>
                                <div className="flex-1">
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center space-x-2">
                                      <span className="font-medium text-sm">{comment.author}</span>
                                      {comment.lineNumber && (
                                        <Badge variant="outline" className="text-xs">
                                          Line {comment.lineNumber}
                                        </Badge>
                                      )}
                                    </div>
                                    <span className="text-xs text-gray-500">
                                      {new Date(comment.timestamp).toLocaleString()}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-700">{comment.content}</p>
                                  <div className="mt-1">
                                    <Button variant="link" size="xs" onClick={() => setReplyingTo(comment.id)}>
                                      Reply
                                    </Button>
                                  </div>

                                  {replyingTo === comment.id && (
                                    <div className="mt-2 space-y-2">
                                      <Textarea
                                        rows={2}
                                        value={replyContent}
                                        onChange={(e) => setReplyContent(e.target.value)}
                                        placeholder="Write a reply..."
                                      />
                                      <div className="flex space-x-2">
                                        <Button
                                          size="sm"
                                          onClick={() => addReply(comment.id)}
                                          disabled={!replyContent.trim()}
                                        >
                                          Send
                                        </Button>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => {
                                            setReplyingTo(null)
                                            setReplyContent('')
                                          }}
                                        >
                                          Cancel
                                        </Button>
                                      </div>
                                    </div>
                                  )}

                                  {comment.replies.length > 0 && (
                                    <div className="mt-3 ml-4 space-y-2">
                                      {comment.replies.map(reply => (
                                        <div key={reply.id} className="bg-gray-50 p-3 rounded">
                                          <div className="flex items-center justify-between mb-1">
                                            <span className="text-xs font-medium">{reply.author}</span>
                                            <span className="text-xs text-gray-500">
                                              {new Date(reply.timestamp).toLocaleString()}
                                            </span>
                                          </div>
                                          <p className="text-xs text-gray-600">{reply.content}</p>
                                        </div>
                                      ))}
                                    </div>
                                  )}
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

              {/* Sidebar */}
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader>
                    <CardTitle>Add Comment</CardTitle>
                    <CardDescription>
                      {selectedLine ? `Comment on line ${selectedLine}` : 'General comment'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <Textarea
                        placeholder="Enter your comment..."
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        rows={4}
                      />
                      <div className="flex justify-between items-center">
                        {selectedLine && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedLine(null)}
                          >
                            Clear line selection
                          </Button>
                        )}
                        <Button onClick={addComment} disabled={!newComment.trim()}>
                          Add Comment
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="mt-6">
                  <CardHeader>
                    <CardTitle>Review Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Comments:</span>
                        <span className="font-medium">{comments.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Unresolved:</span>
                        <span className="font-medium text-orange-600">
                          {comments.filter(c => !c.resolved).length}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Changes:</span>
                        <span className="font-medium">{selectedVersion.changes.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Status:</span>
                        <Badge
                          variant={
                            selectedVersion.status === 'approved'
                              ? 'default'
                              : selectedVersion.status === 'rejected' || selectedVersion.status === 'changes_requested'
                                ? 'destructive'
                                : 'secondary'
                          }
                        >
                          {selectedVersion.status}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
