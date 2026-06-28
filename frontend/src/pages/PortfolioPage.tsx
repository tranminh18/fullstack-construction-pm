import { useEffect, useState } from 'react'
import { api } from '../api'
import type { PortfolioDashboard } from '../types'
import { Card, PageTitle } from '../components/ui'
import { formatCurrency } from '../roles'

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </Card>
  )
}

export default function PortfolioPage() {
  const [data, setData] = useState<PortfolioDashboard | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<PortfolioDashboard>('/dashboard')
      .then((r) => setData(r.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-slate-400">Đang tải...</div>
  if (!data) return <div className="text-slate-400">Không có dữ liệu.</div>

  return (
    <div>
      <PageTitle title="Tổng quan" subtitle="Bức tranh toàn bộ các dự án bạn tham gia" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat label="Số dự án" value={String(data.project_count)} />
        <Stat label="Tổng ngân sách" value={formatCurrency(data.total_budget)} />
        <Stat label="Tổng chi phí" value={formatCurrency(data.total_cost)} />
        <Stat label="Đã thanh toán" value={formatCurrency(data.total_paid)} />
        <Stat label="Công nợ còn lại" value={formatCurrency(data.outstanding_balance)} />
        <Stat label="Vấn đề đang mở" value={String(data.open_issues)} hint={`${data.pending_change_orders} phát sinh chờ duyệt`} />
      </div>
    </div>
  )
}
