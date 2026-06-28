import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../../api'
import type { AcceptanceRecord, Issue, ProjectPhoto, SiteReport, WorkItem } from '../../types'
import { useAuth } from '../../context/AuthContext'
import { Badge, Button, Card, EmptyState, ErrorText } from '../../components/ui'
import { Field, Modal, inputClass } from '../../components/Modal'
import { CAN_ACCEPT_WORK, can, formatCurrency, formatDate } from '../../roles'

const SEVERITY_COLORS: Record<string, string> = { low: 'slate', medium: 'yellow', high: 'red' }

export default function SiteTab({ projectId }: { projectId: number }) {
  const { user } = useAuth()
  const [reports, setReports] = useState<SiteReport[]>([])
  const [issues, setIssues] = useState<Issue[]>([])
  const [acceptances, setAcceptances] = useState<AcceptanceRecord[]>([])
  const [photos, setPhotos] = useState<ProjectPhoto[]>([])
  const [workItems, setWorkItems] = useState<WorkItem[]>([])
  const [loading, setLoading] = useState(true)
  const [reportOpen, setReportOpen] = useState(false)
  const [issueOpen, setIssueOpen] = useState(false)
  const [acceptOpen, setAcceptOpen] = useState(false)

  function load() {
    setLoading(true)
    Promise.all([
      api.get<SiteReport[]>(`/projects/${projectId}/reports`),
      api.get<Issue[]>(`/projects/${projectId}/issues`),
      api.get<AcceptanceRecord[]>(`/projects/${projectId}/acceptances`),
      api.get<ProjectPhoto[]>(`/projects/${projectId}/photos/`),
      api.get<WorkItem[]>(`/projects/${projectId}/workitems/`),
    ])
      .then(([r, i, a, p, w]) => {
        setReports(r.data)
        setIssues(i.data)
        setAcceptances(a.data)
        setPhotos(p.data)
        setWorkItems(w.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(load, [projectId])

  async function resolveIssue(id: number) {
    await api.patch(`/issues/${id}/resolve`)
    load()
  }

  async function uploadPhoto(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    await api.post(`/projects/${projectId}/photos/`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
    load()
  }

  if (loading) return <div className="text-slate-400">Đang tải...</div>

  const canAccept = can(user?.role, CAN_ACCEPT_WORK)

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Báo cáo hiện trường</h3>
          <Button onClick={() => setReportOpen(true)}>+ Báo cáo</Button>
        </div>
        {reports.length === 0 ? (
          <EmptyState message="Chưa có báo cáo hiện trường." />
        ) : (
          <div className="space-y-2">
            {reports.map((r) => (
              <Card key={r.id} className="py-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-slate-700">{r.report_type}</span>
                  <span className="text-xs text-slate-400">{formatDate(r.created_at)}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{r.description}</p>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Vấn đề / Sự cố</h3>
          <Button onClick={() => setIssueOpen(true)}>+ Báo vấn đề</Button>
        </div>
        {issues.length === 0 ? (
          <EmptyState message="Chưa có vấn đề nào." />
        ) : (
          <div className="space-y-2">
            {issues.map((i) => (
              <Card key={i.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium text-slate-800">{i.title}</div>
                  <div className="text-sm text-slate-500">{i.description}</div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge color={SEVERITY_COLORS[i.severity]}>{i.severity}</Badge>
                  <Badge color={i.status === 'resolved' ? 'green' : 'yellow'}>{i.status}</Badge>
                  {i.status !== 'resolved' && <Button variant="secondary" onClick={() => resolveIssue(i.id)}>Giải quyết</Button>}
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Nghiệm thu khối lượng</h3>
          {canAccept && <Button onClick={() => setAcceptOpen(true)}>+ Nghiệm thu</Button>}
        </div>
        {acceptances.length === 0 ? (
          <EmptyState message="Chưa có biên bản nghiệm thu." />
        ) : (
          <div className="space-y-2">
            {acceptances.map((a) => (
              <Card key={a.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium text-slate-800">Khối lượng: {formatCurrency(a.quantity)}</div>
                  <div className="text-sm text-slate-500">{a.notes}</div>
                </div>
                <Badge color="green">{a.status}</Badge>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Ảnh hiện trường ({photos.length})</h3>
          <label className="inline-flex cursor-pointer items-center rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700">
            + Tải ảnh
            <input type="file" className="hidden" accept="image/*" onChange={uploadPhoto} />
          </label>
        </div>
        {photos.length === 0 ? (
          <EmptyState message="Chưa có ảnh hiện trường nào." />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {photos.map((p) => (
              <Card key={p.id} className="p-3">
                <div className="flex h-24 items-center justify-center rounded bg-slate-100 text-3xl">🏗️</div>
                <div className="mt-2 truncate text-xs text-slate-500" title={p.filename}>{p.filename}</div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <ReportModal open={reportOpen} projectId={projectId} onClose={() => setReportOpen(false)} onDone={() => { setReportOpen(false); load() }} />
      <IssueModal open={issueOpen} projectId={projectId} onClose={() => setIssueOpen(false)} onDone={() => { setIssueOpen(false); load() }} />
      <AcceptanceModal open={acceptOpen} projectId={projectId} workItems={workItems} onClose={() => setAcceptOpen(false)} onDone={() => { setAcceptOpen(false); load() }} />
    </div>
  )
}

function ReportModal({ open, projectId, onClose, onDone }: { open: boolean; projectId: number; onClose: () => void; onDone: () => void }) {
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await api.post(`/projects/${projectId}/reports`, { report_type: 'site_update', description })
      setDescription(''); onDone()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Báo cáo hiện trường" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Nội dung báo cáo"><textarea className={inputClass} rows={4} value={description} onChange={(e) => setDescription(e.target.value)} required /></Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
          <Button type="submit" disabled={busy || !description}>Gửi</Button>
        </div>
      </form>
    </Modal>
  )
}

function IssueModal({ open, projectId, onClose, onDone }: { open: boolean; projectId: number; onClose: () => void; onDone: () => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState('medium')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await api.post(`/projects/${projectId}/issues`, { title, description, severity })
      setTitle(''); setDescription(''); onDone()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Báo vấn đề / sự cố" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Tiêu đề"><input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} required /></Field>
        <Field label="Mô tả"><textarea className={inputClass} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} required /></Field>
        <Field label="Mức độ">
          <select className={inputClass} value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="low">Thấp</option>
            <option value="medium">Trung bình</option>
            <option value="high">Cao</option>
          </select>
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
          <Button type="submit" disabled={busy || !title}>Gửi</Button>
        </div>
      </form>
    </Modal>
  )
}

function AcceptanceModal({ open, projectId, workItems, onClose, onDone }: { open: boolean; projectId: number; workItems: WorkItem[]; onClose: () => void; onDone: () => void }) {
  const [workItemId, setWorkItemId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/acceptances`, {
        work_item_id: workItemId ? Number(workItemId) : null,
        quantity: Number(quantity),
        notes: notes || null,
      })
      setQuantity(''); setNotes(''); onDone()
    } catch {
      setError('Không tạo được nghiệm thu. Có thể vai trò của bạn không được phép.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Nghiệm thu khối lượng" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Hạng mục">
          <select className={inputClass} value={workItemId} onChange={(e) => setWorkItemId(e.target.value)}>
            <option value="">— Không gắn —</option>
            {workItems.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Khối lượng / giá trị"><input className={inputClass} type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} required /></Field>
        <Field label="Ghi chú"><input className={inputClass} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        {error && <ErrorText>{error}</ErrorText>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
          <Button type="submit" disabled={busy || !quantity}>Nghiệm thu</Button>
        </div>
      </form>
    </Modal>
  )
}
