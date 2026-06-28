// Các kiểu dữ liệu khớp với schema backend (app/models.py)

export type UserRole =
  | 'homeowner'
  | 'construction_company'
  | 'contractor'
  | 'site_manager'
  | 'worker'

export interface User {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

export type ProjectStatus = 'planning' | 'active' | 'delayed' | 'completed'

export interface Project {
  id: number
  name: string
  description?: string | null
  start_date?: string | null
  end_date?: string | null
  budget?: number | null
  status: ProjectStatus
  owner_id: number
}

export interface ProjectMember {
  id: number
  project_id: number
  user_id: number
  role: string
}

export interface WorkItem {
  id: number
  project_id: number
  parent_id?: number | null
  name: string
  description?: string | null
  budget?: number | null
  progress: number
  is_completed: boolean
}

export interface WorkItemTree extends WorkItem {
  children: WorkItemTree[]
}

export interface Task {
  id: number
  project_id: number
  work_item_id?: number | null
  assignee_id?: number | null
  title: string
  description?: string | null
  due_date?: string | null
  priority: number
  status: string
  estimated_hours?: number | null
}

export interface ChangeOrder {
  id: number
  project_id: number
  requested_by_id: number
  approved_by_id?: number | null
  approved_at?: string | null
  title: string
  description?: string | null
  amount_change: number
  status: string
  created_at: string
}

export interface SiteReport {
  id: number
  project_id: number
  created_by_id: number
  report_type: string
  description: string
  created_at: string
}

export interface Issue {
  id: number
  project_id: number
  reported_by_id: number
  title: string
  description: string
  severity: string
  status: string
  created_at: string
  resolved_at?: string | null
}

export interface AcceptanceRecord {
  id: number
  project_id: number
  work_item_id?: number | null
  accepted_by_id: number
  quantity: number
  status: string
  notes?: string | null
  accepted_at: string
}

export interface CostEntry {
  id: number
  project_id: number
  work_item_id?: number | null
  created_by_id: number
  category: string
  amount: number
  note?: string | null
  cost_date: string
}

export interface PaymentRecord {
  id: number
  project_id: number
  created_by_id: number
  payee_name: string
  amount: number
  payment_method: string
  status: string
  paid_at?: string | null
  note?: string | null
}

export interface ProjectPhoto {
  id: number
  project_id: number
  site_report_id?: number | null
  filename: string
  description?: string | null
  uploaded_at: string
}

export interface AuditLog {
  id: number
  actor_id?: number | null
  project_id?: number | null
  action: string
  entity_type: string
  entity_id?: number | null
  metadata_json?: string | null
  created_at: string
}

export interface ProjectDashboard {
  project_id: number
  project_name: string
  budget?: number | null
  total_cost: number
  total_paid: number
  outstanding_balance: number
  budget_variance?: number | null
  completion_percent: number
  work_item_count: number
  completed_work_items: number
  task_counts: Record<string, number>
  overdue_tasks: number
  issue_counts: Record<string, number>
  change_order_counts: Record<string, number>
  change_order_value: number
  photo_count: number
  site_report_count: number
  member_count: number
  members_by_role: Record<string, number>
  generated_at: string
}

export interface PortfolioDashboard {
  project_count: number
  total_budget: number
  total_cost: number
  total_paid: number
  outstanding_balance: number
  open_issues: number
  pending_change_orders: number
  generated_at: string
}
