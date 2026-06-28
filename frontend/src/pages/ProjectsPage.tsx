import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { Project } from '../types'
import { Badge, Button, Card, EmptyState, ErrorText, PageTitle } from '../components/ui'
import { Field, Modal, inputClass } from '../components/Modal'
import { PROJECT_STATUS_LABELS, formatCurrency } from '../roles'

const STATUS_COLORS: Record<string, string> = {
  planning: 'slate',
  active: 'blue',
  delayed: 'red',
  completed: 'green',
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  function load() {
    setLoading(true)
    api
      .get<Project[]>('/projects/')
      .then((r) => setProjects(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  return (
    <div>
      <PageTitle
        title="Dự án"
        subtitle="Các công trình bạn sở hữu hoặc tham gia"
        action={<Button onClick={() => setOpen(true)}>+ Tạo dự án</Button>}
      />
      {loading ? (
        <div className="text-slate-400">Đang tải...</div>
      ) : projects.length === 0 ? (
        <EmptyState message="Chưa có dự án nào. Tạo dự án đầu tiên để bắt đầu." />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`}>
              <Card className="transition hover:border-brand-400 hover:shadow">
                <div className="flex items-start justify-between">
                  <h3 className="font-semibold text-slate-900">{p.name}</h3>
                  <Badge color={STATUS_COLORS[p.status]}>{PROJECT_STATUS_LABELS[p.status] ?? p.status}</Badge>
                </div>
                <p className="mt-1 line-clamp-2 text-sm text-slate-500">{p.description || 'Không có mô tả'}</p>
                <div className="mt-3 text-sm text-slate-600">Ngân sách: {formatCurrency(p.budget)}</div>
              </Card>
            </Link>
          ))}
        </div>
      )}
      <CreateProjectModal
        open={open}
        onClose={() => setOpen(false)}
        onCreated={() => {
          setOpen(false)
          load()
        }}
      />
    </div>
  )
}

function CreateProjectModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [budget, setBudget] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post('/projects/', {
        name,
        description: description || null,
        budget: budget ? Number(budget) : null,
      })
      setName('')
      setDescription('')
      setBudget('')
      onCreated()
    } catch {
      setError('Không tạo được dự án. Vui lòng thử lại.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Tạo dự án mới" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Tên công trình">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Mô tả">
          <textarea className={inputClass} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label="Ngân sách (VND)">
          <input className={inputClass} type="number" value={budget} onChange={(e) => setBudget(e.target.value)} />
        </Field>
        {error && <ErrorText>{error}</ErrorText>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Hủy
          </Button>
          <Button type="submit" disabled={busy || !name}>
            {busy ? 'Đang tạo...' : 'Tạo dự án'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
