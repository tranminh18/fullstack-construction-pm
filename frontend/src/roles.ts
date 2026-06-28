import type { UserRole } from './types'

export const ROLE_LABELS: Record<UserRole, string> = {
  homeowner: 'Chủ đầu tư',
  construction_company: 'Công ty xây dựng',
  contractor: 'Nhà thầu',
  site_manager: 'Quản lý công trình',
  worker: 'Công nhân',
}

// Ma trận phân quyền nghiệp vụ — phải khớp với app/security.py (CAN_*).
// Dùng để ẩn/hiện nút trên UI; backend vẫn là nơi chốt quyền cuối cùng.
export const CAN_ASSIGN_TASK: UserRole[] = ['construction_company', 'contractor', 'site_manager']
export const CAN_ACCEPT_WORK: UserRole[] = ['construction_company', 'site_manager']
export const CAN_APPROVE_CHANGE_ORDER: UserRole[] = ['homeowner', 'construction_company']
export const CAN_SETTLE_PAYMENT: UserRole[] = ['homeowner', 'construction_company']

export function can(role: UserRole | undefined, allowed: UserRole[]): boolean {
  return role !== undefined && allowed.includes(role)
}

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  planning: 'Lập kế hoạch',
  active: 'Đang thi công',
  delayed: 'Chậm tiến độ',
  completed: 'Hoàn thành',
}

export function formatCurrency(value?: number | null): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value)
}

export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('vi-VN')
}
