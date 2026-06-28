import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../../api'
import type { WorkItemTree } from '../../types'
import { Badge, Button, Card, EmptyState, ErrorText } from '../../components/ui'
import { Field, Modal, inputClass } from '../../components/Modal'

export default function WbsTab({ projectId }: { projectId: number }) {
  const [tree, setTree] = useState<WorkItemTree[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [parentId, setParentId] = useState<number | null>(null)
  const [progressItem, setProgressItem] = useState<WorkItemTree | null>(null)

  function load() {
    setLoading(true)
    api
      .get<WorkItemTree[]>(`/projects/${projectId}/workitems/tree`)
      .then((r) => setTree(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(load, [projectId])

  function openCreate(parent: number | null) {
    setParentId(parent)
    setCreateOpen(true)
  }

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <Button onClick={() => openCreate(null)}>+ Hạng mục gốc</Button>
      </div>
      {loading ? (
        <div className="text-slate-400">Đang tải...</div>
      ) : tree.length === 0 ? (
        <EmptyState message="Chưa có hạng mục nào. Tạo hạng mục gốc để bắt đầu phân rã công việc (WBS)." />
      ) : (
        <Card>
          <div className="space-y-1">
            {tree.map((node) => (
              <WbsNode key={node.id} node={node} depth={0} onAddChild={openCreate} onUpdateProgress={setProgressItem} />
            ))}
          </div>
        </Card>
      )}
      <CreateWorkItemModal
        open={createOpen}
        projectId={projectId}
        parentId={parentId}
        onClose={() => setCreateOpen(false)}
        onCreated={() => {
          setCreateOpen(false)
          load()
        }}
      />
      <ProgressModal
        item={progressItem}
        onClose={() => setProgressItem(null)}
        onUpdated={() => {
          setProgressItem(null)
          load()
        }}
      />
    </div>
  )
}

function WbsNode({
  node,
  depth,
  onAddChild,
  onUpdateProgress,
}: {
  node: WorkItemTree
  depth: number
  onAddChild: (parentId: number) => void
  onUpdateProgress: (item: WorkItemTree) => void
}) {
  return (
    <div>
      <div className="flex items-center gap-3 rounded-md py-2 hover:bg-slate-50" style={{ paddingLeft: depth * 24 + 8 }}>
        <span className="flex-1 text-sm font-medium text-slate-800">
          {node.name}
          {node.is_completed && <span className="ml-2 align-middle"><Badge color="green">Hoàn thành</Badge></span>}
        </span>
        <div className="w-40">
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full bg-brand-500" style={{ width: `${Math.min(node.progress, 100)}%` }} />
          </div>
        </div>
        <span className="w-12 text-right text-sm text-slate-600">{node.progress}%</span>
        <Button variant="ghost" onClick={() => onUpdateProgress(node)}>
          Tiến độ
        </Button>
        <Button variant="ghost" onClick={() => onAddChild(node.id)}>
          + Con
        </Button>
      </div>
      {node.children.map((child) => (
        <WbsNode key={child.id} node={child} depth={depth + 1} onAddChild={onAddChild} onUpdateProgress={onUpdateProgress} />
      ))}
    </div>
  )
}

function CreateWorkItemModal({
  open,
  projectId,
  parentId,
  onClose,
  onCreated,
}: {
  open: boolean
  projectId: number
  parentId: number | null
  onClose: () => void
  onCreated: () => void
}) {
  const [name, setName] = useState('')
  const [budget, setBudget] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/workitems/`, {
        name,
        budget: budget ? Number(budget) : null,
        parent_id: parentId,
      })
      setName('')
      setBudget('')
      onCreated()
    } catch {
      setError('Không tạo được hạng mục.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title={parentId ? 'Thêm hạng mục con' : 'Thêm hạng mục gốc'} onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label="Tên hạng mục">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
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
            {busy ? 'Đang tạo...' : 'Tạo'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function ProgressModal({
  item,
  onClose,
  onUpdated,
}: {
  item: WorkItemTree | null
  onClose: () => void
  onUpdated: () => void
}) {
  const [progress, setProgress] = useState(0)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (item) setProgress(item.progress)
  }, [item])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!item) return
    setBusy(true)
    try {
      await api.patch(`/workitems/${item.id}/progress`, { progress_percentage: progress })
      onUpdated()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={item !== null} title={`Cập nhật tiến độ: ${item?.name ?? ''}`} onClose={onClose}>
      <form onSubmit={onSubmit}>
        <Field label={`Tiến độ: ${progress}%`}>
          <input type="range" min={0} max={100} value={progress} onChange={(e) => setProgress(Number(e.target.value))} className="w-full" />
        </Field>
        <p className="text-xs text-slate-500">Đạt 100% sẽ tự đánh dấu hạng mục hoàn thành.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Hủy
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? 'Đang lưu...' : 'Lưu'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
