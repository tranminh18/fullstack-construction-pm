import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../../api'
import type { Task, WorkItem } from '../../types'
import { useAuth } from '../../context/AuthContext'
import { Badge, Button, Card, EmptyState, ErrorText } from '../../components/ui'
import { Field, Modal, inputClass } from '../../components/Modal'
import { CAN_ASSIGN_TASK, can, formatDate } from '../../roles'

const STATUS_COLORS: Record<string, string> = { todo: 'slate', in_progress: 'blue', done: 'green' }

export default function TasksTab({ projectId }: { projectId: number }) {
  const { user } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [workItems, setWorkItems] = useState<WorkItem[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  function load() {
    setLoading(true)
    Promise.all([
      api.get<Task[]>(`/projects/${projectId}/tasks/`),
      api.get<WorkItem[]>(`/projects/${projectId}/workitems/`),
    ])
      .then(([t, w]) => {
        setTasks(t.data)
        setWorkItems(w.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(load, [projectId])

  const canAssign = can(user?.role, CAN_ASSIGN_TASK)

  return (
    <div>
      <div className="mb-4 flex justify-end">
        {canAssign && <Button onClick={() => setOpen(true)}>+ Giao việc</Button>}
      </div>
      {loading ? (
        <div className="text-slate-400">Đang tải...</div>
      ) : tasks.length === 0 ? (
        <EmptyState message={canAssign ? 'Chưa có công việc nào.' : 'Chưa có công việc nào được giao.'} />
      ) : (
        <div className="space-y-2">
          {tasks.map((t) => (
            <Card key={t.id} className="flex items-center justify-between py-3">
              <div>
                <div className="font-medium text-slate-800">{t.title}</div>
                <div className="text-sm text-slate-500">{t.description}</div>
              </div>
              <div className="flex items-center gap-3 text-sm text-slate-500">
                <span>Hạn: {formatDate(t.due_date)}</span>
                <Badge color={STATUS_COLORS[t.status]}>{t.status}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
      <CreateTaskModal
        open={open}
        projectId={projectId}
        workItems={workItems}
        onClose={() => setOpen(false)}
        onCreated={() => {
          setOpen(false)
          load()
        }}
      />
    </div>
  )
}

function CreateTaskModal({
  open,
  projectId,
  workItems,
  onClose,
  onCreated,
}: {
  open: boolean
  projectId: number
  workItems: WorkItem[]
  onClose: () => void
  onCreated: () => void
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [workItemId, setWorkItemId] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/tasks/`, {
        title,
        description: description || null,
        work_item_id: workItemId ? Number(workItemId) : null,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
      })
      setTitle('')
      setDescription('')
      setWorkItemId('')
      setDueDate('')
      onCreated()
    } catch {
      setError('Không tạo được công việc. Có thể vai trò của bạn không được phép giao việc.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Giao việc mới" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Tiêu đề">
          <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} required />
        </Field>
        <Field label="Mô tả">
          <textarea className={inputClass} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label="Hạng mục liên quan">
          <select className={inputClass} value={workItemId} onChange={(e) => setWorkItemId(e.target.value)}>
            <option value="">— Không gắn —</option>
            {workItems.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Hạn hoàn thành">
          <input className={inputClass} type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </Field>
        {error && <ErrorText>{error}</ErrorText>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Hủy
          </Button>
          <Button type="submit" disabled={busy || !title}>
            {busy ? 'Đang tạo...' : 'Giao việc'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
