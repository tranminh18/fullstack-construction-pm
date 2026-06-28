import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../../api'
import type { AuditLog, ProjectMember } from '../../types'
import { Badge, Button, Card, EmptyState, ErrorText } from '../../components/ui'
import { Field, Modal, inputClass } from '../../components/Modal'
import { formatDate } from '../../roles'

export function MembersTab({ projectId }: { projectId: number }) {
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  function load() {
    setLoading(true)
    api.get<ProjectMember[]>(`/projects/${projectId}/members`).then((r) => setMembers(r.data)).finally(() => setLoading(false))
  }

  useEffect(load, [projectId])

  if (loading) return <div className="text-slate-400">Đang tải...</div>

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <Button onClick={() => setOpen(true)}>+ Thêm thành viên</Button>
      </div>
      {members.length === 0 ? (
        <EmptyState message="Chưa có thành viên." />
      ) : (
        <div className="space-y-2">
          {members.map((m) => (
            <Card key={m.id} className="flex items-center justify-between py-3">
              <span className="text-sm text-slate-700">User #{m.user_id}</span>
              <Badge color="blue">{m.role}</Badge>
            </Card>
          ))}
        </div>
      )}
      <AddMemberModal open={open} projectId={projectId} onClose={() => setOpen(false)} onDone={() => { setOpen(false); load() }} />
    </div>
  )
}

function AddMemberModal({ open, projectId, onClose, onDone }: { open: boolean; projectId: number; onClose: () => void; onDone: () => void }) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('member')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/members`, { user_email: email, role })
      setEmail(''); onDone()
    } catch {
      setError('Không thêm được thành viên. Kiểm tra email hoặc quyền của bạn.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Thêm thành viên" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Email người dùng"><input className={inputClass} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
        <Field label="Vai trò trong dự án">
          <select className={inputClass} value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="member">Thành viên</option>
            <option value="manager">Quản lý</option>
          </select>
        </Field>
        {error && <ErrorText>{error}</ErrorText>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
          <Button type="submit" disabled={busy || !email}>Thêm</Button>
        </div>
      </form>
    </Modal>
  )
}

export function AuditTab({ projectId }: { projectId: number }) {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<AuditLog[]>(`/projects/${projectId}/audit-logs`).then((r) => setLogs(r.data)).finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <div className="text-slate-400">Đang tải...</div>
  if (logs.length === 0) return <EmptyState message="Chưa có nhật ký hoạt động." />

  return (
    <div className="space-y-2">
      {logs.map((l) => (
        <Card key={l.id} className="flex items-center justify-between py-2.5">
          <div>
            <span className="font-mono text-sm text-slate-700">{l.action}</span>
            <span className="ml-2 text-xs text-slate-400">{l.entity_type}</span>
          </div>
          <span className="text-xs text-slate-400">{formatDate(l.created_at)}</span>
        </Card>
      ))}
    </div>
  )
}
