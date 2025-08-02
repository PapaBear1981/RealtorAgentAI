// User and Authentication Types
export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'agent' | 'tc' | 'signer'
  created_at: string
  disabled?: boolean
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

// Deal and Contract Types
export interface Deal {
  id: string
  title: string
  status: 'draft' | 'active' | 'pending' | 'completed' | 'cancelled'
  owner_id: string
  created_at: string
  updated_at: string
}

export interface Contract {
  id: string
  deal_id: string
  template_id: string
  status: 'draft' | 'review' | 'sent' | 'signed' | 'void'
  variables: Record<string, any> | null
  created_at: string
  updated_at: string
}

// Upload and File Types
export interface Upload {
  id: string
  deal_id: string
  filename: string
  content_type: string
  s3_key: string
  pages?: number
  ocr: boolean
  created_at: string
  owner_id: string
}

// Signature Types
export interface Signer {
  id: string
  contract_id: string
  party_role: string
  name: string
  email: string
  phone?: string
  order: number
  status: 'pending' | 'sent' | 'viewed' | 'signed' | 'declined'
}

export interface SignEvent {
  id: string
  signer_id: string
  type: string
  ip?: string
  user_agent?: string
  timestamp: string
  metadata?: Record<string, any>
}

// Validation Types
export interface Validation {
  id: string
  contract_id: string
  rule_id: string
  severity: 'blocker' | 'warn' | 'info'
  ok: boolean
  detail: string
  created_at: string
}

// Template Types
export interface Template {
  id: string
  name: string
  version: string
  docx_key: string
  schema: Record<string, any>
  ruleset: Record<string, any>
}

// API Response Types
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// Form Types
export interface LoginForm {
  email: string
  password: string
}

export interface FileUploadForm {
  files: File[]
  deal_id?: string
  document_type?: string
}
