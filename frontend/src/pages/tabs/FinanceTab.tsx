import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../../api'
import type { ChangeOrder, CostEntry, PaymentRecord } from '../../types'
import { useAuth } from '../../context/AuthContext'
import { Badge, Button, Card, EmptyState, ErrorText } from '../../components/ui'
import { Field, Modal, inputClass } from '../../components/Modal'
import { CAN_APPROVE_CHANGE_ORDER, CAN_SETTLE_PAYMENT, can, formatCurrency } from '../../roles'

const CO_COLORS: Record<string, string> = { pending: 'yellow', approved: 'green', rejected: 'red' }
const PAY_COLORS: Record<string, string> = { pending: 'yellow', paid: 'green' }

export default function FinanceTab({ projectId }: { projectId: number }) {
  const { user } = useAuth()
  const [changeOrders, setChangeOrders] = useState<ChangeOrder[]>([])
  const [costs, setCosts] = useState<CostEntry[]>([])
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [coOpen, setCoOpen] = useState(false)
  const [costOpen, setCostOpen] = useState(false)
  const [payOpen, setPayOpen] = useState(false)

  function load() {
    setLoading(true)
    Promise.all([
      api.get<ChangeOrder[]>(`/projects/${projectId}/change-orders`),
      api.get<CostEntry[]>(`/projects/${projectId}/costs`),
      api.get<PaymentRecord[]>(`/projects/${projectId}/payments`),
    ])
      .then(([co, c, p]) => {
        setChangeOrders(co.data)
        setCosts(c.data)
        setPayments(p.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(load, [projectId])

  async function approve(id: number) {
    await api.patch(`/change-orders/${id}/approve`)
    load()
  }

  async function settle(id: number) {
    await api.patch(`/payments/${id}/settle`)
    load()
  }

  if (loading) return <div className="text-slate-400">Đang tải...</div>

  const canApprove = can(user?.role, CAN_APPROVE_CHANGE_ORDER)
  const canSettle = can(user?.role, CAN_SETTLE_PAYMENT)

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Phát sinh (Change Orders)</h3>
          <Button onClick={() => setCoOpen(true)}>+ Tạo phát sinh</Button>
        </div>
        {changeOrders.length === 0 ? (
          <EmptyState message="Chưa có phát sinh nào." />
        ) : (
          <div className="space-y-2">
            {changeOrders.map((co) => (
              <Card key={co.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium text-slate-800">{co.title}</div>
                  <div className="text-sm text-slate-500">{formatCurrency(co.amount_change)}</div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge color={CO_COLORS[co.status]}>{co.status}</Badge>
                  {canApprove && co.status === 'pending' && (
                    <Button onClick={() => approve(co.id)}>Duyệt</Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Chi phí</h3>
          <Button onClick={() => setCostOpen(true)}>+ Ghi chi phí</Button>
        </div>
        {costs.length === 0 ? (
          <EmptyState message="Chưa có khoản chi phí nào." />
        ) : (
          <div className="space-y-2">
            {costs.map((c) => (
              <Card key={c.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium text-slate-800">{c.category}</div>
                  <div className="text-sm text-slate-500">{c.note}</div>
                </div>
                <div className="font-medium text-slate-700">{formatCurrency(c.amount)}</div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Thanh toán</h3>
          <Button onClick={() => setPayOpen(true)}>+ Tạo thanh toán</Button>
        </div>
        {payments.length === 0 ? (
          <EmptyState message="Chưa có khoản thanh toán nào." />
        ) : (
          <div className="space-y-2">
            {payments.map((p) => (
              <Card key={p.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium text-slate-800">{p.payee_name}</div>
                  <div className="text-sm text-slate-500">{formatCurrency(p.amount)}</div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge color={PAY_COLORS[p.status]}>{p.status}</Badge>
                  {canSettle && p.status !== 'paid' && <Button onClick={() => settle(p.id)}>Tất toán</Button>}
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <ChangeOrderModal open={coOpen} projectId={projectId} onClose={() => setCoOpen(false)} onDone={() => { setCoOpen(false); load() }} />
      <CostModal open={costOpen} projectId={projectId} onClose={() => setCostOpen(false)} onDone={() => { setCostOpen(false); load() }} />
      <PaymentModal open={payOpen} projectId={projectId} onClose={() => setPayOpen(false)} onDone={() => { setPayOpen(false); load() }} />
    </div>
  )
}

function ChangeOrderModal({ open, projectId, onClose, onDone }: { open: boolean; projectId: number; onClose: () => void; onDone: () => void }) {
  const [title, setTitle] = useState('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/change-orders`, { title, amount_change: amount ? Number(amount) : 0 })
      setTitle(''); setAmount(''); onDone()
    } catch {
      setError('Không tạo được phát sinh.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Tạo phát sinh" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Tiêu đề"><input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} required /></Field>
        <Field label="Giá trị thay đổi (VND)"><input className={inputClass} type="number" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
        {error && <ErrorText>{error}</ErrorText>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
          <Button type="submit" disabled={busy || !title}>Tạo</Button>
        </div>
      </form>
    </Modal>
  )
}

function CostModal({ open, projectId, onClose, onDone }: { open: boolean; projectId: number; onClose: () => void; onDone: () => void }) {
  const [category, setCategory] = useState('materials')
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/costs`, { category, amount: Number(amount), note: note || null })
      setAmount(''); setNote(''); onDone()
    } catch {
      setError('Không ghi được chi phí. Có thể vai trò của bạn không được phép.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Ghi chi phí" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Hạng mục chi phí">
          <select className={inputClass} value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="materials">Vật tư</option>
            <option value="labor">Nhân công</option>
            <option value="equipment">Thiết bị</option>
            <option value="other">Khác</option>
          </select>
        </Field>
        <Field label="Số tiền (VND)"><input className={inputClass} type="number" value={amount} onChange={(e) => setAmount(e.target.value)} required /></Field>
        <Field label="Ghi chú"><input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        {error && <ErrorText>{error}</ErrorText>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
          <Button type="submit" disabled={busy || !amount}>Lưu</Button>
        </div>
      </form>
    </Modal>
  )
}

function PaymentModal({ open, projectId, onClose, onDone }: { open: boolean; projectId: number; onClose: () => void; onDone: () => void }) {
  const [payeeName, setPayeeName] = useState('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/payments`, { payee_name: payeeName, amount: Number(amount) })
      setPayeeName(''); setAmount(''); onDone()
    } catch {
      setError('Không tạo được thanh toán. Có thể vai trò của bạn không được phép.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="Tạo thanh toán" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Người nhận"><input className={inputClass} value={payeeName} onChange={(e) => setPayeeName(e.target.value)} required /></Field>
        <Field label="Số tiền (VND)"><input className={inputClass} type="number" value={amount} onChange={(e) => setAmount(e.target.value)} required /></Field>
        {error && <ErrorText>{error}</ErrorText>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
          <Button type="submit" disabled={busy || !payeeName || !amount}>Tạo</Button>
        </div>
      </form>
    </Modal>
  )
}
