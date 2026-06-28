import { useEffect, useState } from 'react'
import { api } from '../../api'
import type { ProjectDashboard } from '../../types'
import { Card, EmptyState } from '../../components/ui'
import { formatCurrency } from '../../roles'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-900">{value}</div>
    </Card>
  )
}

export default function DashboardTab({ projectId }: { projectId: number }) {
  const [data, setData] = useState<ProjectDashboard | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<ProjectDashboard>(`/projects/${projectId}/dashboard`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <div className="text-slate-400">Đang tải...</div>
  if (!data) return <EmptyState message="Không có dữ liệu dashboard." />

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Tiến độ" value={`${data.completion_percent}%`} />
        <Stat label="Ngân sách" value={formatCurrency(data.budget)} />
        <Stat label="Tổng chi phí" value={formatCurrency(data.total_cost)} />
        <Stat label="Công nợ" value={formatCurrency(data.outstanding_balance)} />
        <Stat label="Hạng mục" value={`${data.completed_work_items}/${data.work_item_count} xong`} />
        <Stat label="Việc quá hạn" value={String(data.overdue_tasks)} />
        <Stat label="Ảnh hiện trường" value={String(data.photo_count)} />
        <Stat label="Thành viên" value={String(data.member_count)} />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <div className="mb-2 text-sm font-medium text-slate-700">Công việc</div>
          {Object.entries(data.task_counts).map(([k, v]) => (
            <div key={k} className="flex justify-between text-sm text-slate-600">
              <span>{k}</span>
              <span className="font-medium">{v}</span>
            </div>
          ))}
        </Card>
        <Card>
          <div className="mb-2 text-sm font-medium text-slate-700">Vấn đề</div>
          {Object.entries(data.issue_counts).map(([k, v]) => (
            <div key={k} className="flex justify-between text-sm text-slate-600">
              <span>{k}</span>
              <span className="font-medium">{v}</span>
            </div>
          ))}
        </Card>
        <Card>
          <div className="mb-2 text-sm font-medium text-slate-700">Phát sinh</div>
          {Object.entries(data.change_order_counts).map(([k, v]) => (
            <div key={k} className="flex justify-between text-sm text-slate-600">
              <span>{k}</span>
              <span className="font-medium">{v}</span>
            </div>
          ))}
          <div className="mt-2 border-t border-slate-100 pt-2 text-sm text-slate-600">
            Giá trị: {formatCurrency(data.change_order_value)}
          </div>
        </Card>
      </div>
    </div>
  )
}
