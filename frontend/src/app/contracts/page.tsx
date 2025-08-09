"use client"

import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { Navigation } from "@/components/layout/Navigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import { useState } from "react"

interface ContractTemplate {
  id: string
  name: string
  description: string
  category: string
  variables: {
    name: string
    label: string
    type: 'text' | 'number' | 'date' | 'select' | 'textarea'
    required: boolean
    options?: string[]
    placeholder?: string
  }[]
  template: string
}

const CONTRACT_TEMPLATES: ContractTemplate[] = [
  {
    id: 'purchase-agreement',
    name: 'Residential Purchase Agreement',
    description: 'Standard residential real estate purchase agreement',
    category: 'Purchase',
    variables: [
      { name: 'buyerName', label: 'Buyer Name', type: 'text', required: true, placeholder: 'John Smith' },
      { name: 'sellerName', label: 'Seller Name', type: 'text', required: true, placeholder: 'Jane Doe' },
      { name: 'propertyAddress', label: 'Property Address', type: 'textarea', required: true, placeholder: '123 Main St, Anytown, ST 12345' },
      { name: 'purchasePrice', label: 'Purchase Price', type: 'number', required: true, placeholder: '350000' },
      { name: 'closingDate', label: 'Closing Date', type: 'date', required: true },
      { name: 'earnestMoney', label: 'Earnest Money', type: 'number', required: true, placeholder: '5000' },
      { name: 'financingType', label: 'Financing Type', type: 'select', required: true, options: ['Cash', 'Conventional', 'FHA', 'VA', 'Other'] },
    ],
    template: `RESIDENTIAL PURCHASE AGREEMENT

This Purchase Agreement is made between \{\{buyerName\}\} ("Buyer") and \{\{sellerName\}\} ("Seller") for the purchase of the property located at:

\{\{propertyAddress\}\}

PURCHASE TERMS:
- Purchase Price: $\{\{purchasePrice\}\}
- Earnest Money: $\{\{earnestMoney\}\}
- Financing: \{\{financingType\}\}
- Closing Date: \{\{closingDate\}\}

[Additional standard terms and conditions would follow...]`
  },
  {
    id: 'listing-agreement',
    name: 'Exclusive Listing Agreement',
    description: 'Exclusive right to sell listing agreement',
    category: 'Listing',
    variables: [
      { name: 'sellerName', label: 'Seller Name', type: 'text', required: true },
      { name: 'agentName', label: 'Agent Name', type: 'text', required: true },
      { name: 'brokerageName', label: 'Brokerage Name', type: 'text', required: true },
      { name: 'propertyAddress', label: 'Property Address', type: 'textarea', required: true },
      { name: 'listingPrice', label: 'Listing Price', type: 'number', required: true },
      { name: 'commission', label: 'Commission Rate (%)', type: 'number', required: true, placeholder: '6' },
      { name: 'listingPeriod', label: 'Listing Period (months)', type: 'number', required: true, placeholder: '6' },
    ],
    template: `EXCLUSIVE RIGHT TO SELL LISTING AGREEMENT

Seller: \{\{sellerName\}\}
Agent: \{\{agentName\}\}
Brokerage: \{\{brokerageName\}\}

Property: \{\{propertyAddress\}\}

LISTING TERMS:
- Listing Price: $\{\{listingPrice\}\}
- Commission: \{\{commission\}\}%
- Listing Period: \{\{listingPeriod\}\} months

[Additional terms and conditions would follow...]`
  }
]

export default function ContractsPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<ContractTemplate | null>(null)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [generatedContract, setGeneratedContract] = useState<string>('')
  const [activeTab, setActiveTab] = useState('templates')
  const { toast } = useToast()

  const handleTemplateSelect = (template: ContractTemplate) => {
    setSelectedTemplate(template)
    setFormData({})
    setGeneratedContract('')
    setActiveTab('variables')
  }

  const handleInputChange = (name: string, value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const generateContract = () => {
    if (!selectedTemplate) return

    let contract = selectedTemplate.template

    // Replace variables in template
    selectedTemplate.variables.forEach(variable => {
      const value = formData[variable.name] || `[${variable.label}]`
      const regex = new RegExp(`{{${variable.name}}}`, 'g')
      contract = contract.replace(regex, value)
    })

    setGeneratedContract(contract)
    setActiveTab('preview')

    toast({
      title: "Contract Generated",
      description: "Your contract has been generated successfully.",
    })
  }

  const isFormValid = () => {
    if (!selectedTemplate) return false
    return selectedTemplate.variables
      .filter(v => v.required)
      .every(v => formData[v.name]?.trim())
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <Navigation />

        {/* Page Header */}
        <header className="bg-card shadow-sm border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-6">
              <h1 className="text-3xl font-bold text-foreground">Contract Generator</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Generate standardized contracts from templates and extracted data
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="templates">Select Template</TabsTrigger>
                <TabsTrigger value="variables" disabled={!selectedTemplate}>Fill Variables</TabsTrigger>
                <TabsTrigger value="preview" disabled={!generatedContract}>Preview & Generate</TabsTrigger>
              </TabsList>

              {/* Template Selection */}
              <TabsContent value="templates" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Choose Contract Template</CardTitle>
                    <CardDescription>
                      Select from our library of standardized real estate contract templates
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {CONTRACT_TEMPLATES.map((template) => (
                        <Card
                          key={template.id}
                          className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                            selectedTemplate?.id === template.id ? 'ring-2 ring-primary' : ''
                          }`}
                          onClick={() => handleTemplateSelect(template)}
                        >
                          <CardHeader>
                            <div className="flex items-start justify-between">
                              <div>
                                <CardTitle className="text-lg">{template.name}</CardTitle>
                                <CardDescription className="mt-1">
                                  {template.description}
                                </CardDescription>
                              </div>
                              <Badge variant="secondary">{template.category}</Badge>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm text-muted-foreground">
                              {template.variables.length} variables to fill
                            </p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Variable Input */}
              <TabsContent value="variables" className="space-y-6">
                {selectedTemplate && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Fill Contract Variables</CardTitle>
                      <CardDescription>
                        Complete the required information for: {selectedTemplate.name}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {selectedTemplate.variables.map((variable) => (
                          <div key={variable.name} className="space-y-2">
                            <Label htmlFor={variable.name}>
                              {variable.label}
                              {variable.required && <span className="text-destructive ml-1">*</span>}
                            </Label>

                            {variable.type === 'text' && (
                              <Input
                                id={variable.name}
                                placeholder={variable.placeholder}
                                value={formData[variable.name] || ''}
                                onChange={(e) => handleInputChange(variable.name, e.target.value)}
                              />
                            )}

                            {variable.type === 'number' && (
                              <Input
                                id={variable.name}
                                type="number"
                                placeholder={variable.placeholder}
                                value={formData[variable.name] || ''}
                                onChange={(e) => handleInputChange(variable.name, e.target.value)}
                              />
                            )}

                            {variable.type === 'date' && (
                              <Input
                                id={variable.name}
                                type="date"
                                value={formData[variable.name] || ''}
                                onChange={(e) => handleInputChange(variable.name, e.target.value)}
                              />
                            )}

                            {variable.type === 'textarea' && (
                              <Textarea
                                id={variable.name}
                                placeholder={variable.placeholder}
                                value={formData[variable.name] || ''}
                                onChange={(e) => handleInputChange(variable.name, e.target.value)}
                                rows={3}
                              />
                            )}

                            {variable.type === 'select' && variable.options && (
                              <Select
                                value={formData[variable.name] || ''}
                                onValueChange={(value) => handleInputChange(variable.name, value)}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="Select an option" />
                                </SelectTrigger>
                                <SelectContent>
                                  {variable.options.map((option) => (
                                    <SelectItem key={option} value={option}>
                                      {option}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                        ))}
                      </div>

                      <div className="mt-6 flex justify-end">
                        <Button
                          onClick={generateContract}
                          disabled={!isFormValid()}
                        >
                          Generate Contract
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Contract Preview */}
              <TabsContent value="preview" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Generated Contract</CardTitle>
                    <CardDescription>
                      Review your generated contract and make any necessary adjustments
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="bg-card border border-border rounded-lg p-6 min-h-96">
                        <pre className="whitespace-pre-wrap font-mono text-sm text-foreground">
                          {generatedContract}
                        </pre>
                      </div>

                      <div className="flex justify-between">
                        <Button
                          variant="outline"
                          onClick={() => setActiveTab('variables')}
                        >
                          Edit Variables
                        </Button>
                        <div className="space-x-2">
                          <Button variant="outline">
                            Save Draft
                          </Button>
                          <Button>
                            Download PDF
                          </Button>
                        </div>
                      </div>
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
