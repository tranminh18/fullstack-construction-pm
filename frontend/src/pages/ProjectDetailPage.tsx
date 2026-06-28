import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import type { Project } from '../types'
import { Badge, PageTitle } from '../components/ui'
import { PROJECT_STATUS_LABELS, formatCurrency } from '../roles'
import DashboardTab from './tabs/DashboardTab'
import WbsTab from './tabs/WbsTab'
import TasksTab from './tabs/TasksTab'
import FinanceTab from './tabs/FinanceTab'
import SiteTab from './tabs/SiteTab'
import { AuditTab, MembersTab } from './tabs/MetaTabs'

const TABS = [
  { key: 'dashboard', label: 'Tổng quan' },
  { key: 'wbs', label: 'Hạng mục (WBS)' },
  { key: 'tasks', label: 'Công việc' },
  { key: 'finance', label: 'Tài chính' },
  { key: 'site', label: 'Hiện trường' },
  { key: 'members', label: 'Thành viên' },
  { key: 'audit', label: 'Nhật ký' },
] as const

type TabKey = (typeof TABS)[number]['key']

export default function ProjectDetailPage() {
  const { id } = useParams()
  const projectId = Number(id)
  const [project, setProject] = useState<Project | null>(null)
  const [tab, setTab] = useState<TabKey>('dashboard')

  useEffect(() => {
    api.get<Project>(`/projects/${projectId}`).then((r) => setProject(r.data))
  }, [projectId])

  return (
    <div>
      <Link to="/projects" className="mb-4 inline-block text-sm text-brand-600 hover:underline">
        ← Quay lại danh sách
      </Link>
      <PageTitle
        title={project?.name ?? 'Đang tải...'}
        subtitle={project?.description ?? undefined}
        action={
          project && (
            <div className="flex items-center gap-3">
              <Badge color="blue">{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>
              <span className="text-sm text-slate-500">Ngân sách: {formatCurrency(project.budget)}</span>
            </div>
          )
        }
      />
      <div className="mb-6 flex flex-wrap gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === t.key ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'dashboard' && <DashboardTab projectId={projectId} />}
      {tab === 'wbs' && <WbsTab projectId={projectId} />}
      {tab === 'tasks' && <TasksTab projectId={projectId} />}
      {tab === 'finance' && <FinanceTab projectId={projectId} />}
      {tab === 'site' && <SiteTab projectId={projectId} />}
      {tab === 'members' && <MembersTab projectId={projectId} />}
      {tab === 'audit' && <AuditTab projectId={projectId} />}
    </div>
  )
}
