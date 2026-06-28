import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Button, Card, ErrorText } from '../components/ui'
import { Field, inputClass } from '../components/Modal'
import { ROLE_LABELS } from '../roles'

const DEMO_ACCOUNTS = [
  'homeowner@example.com',
  'company@example.com',
  'contractor@example.com',
  'sitemanager@example.com',
  'worker@example.com',
]

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('homeowner@example.com')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Email hoặc mật khẩu không đúng.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-slate-900">Quản trị dự án xây dựng</h1>
          <p className="mt-1 text-sm text-slate-500">Nền tảng điều phối thi công đa bên</p>
        </div>
        <Card>
          <form onSubmit={onSubmit}>
            <Field label="Email">
              <input className={inputClass} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Field>
            <Field label="Mật khẩu">
              <input className={inputClass} type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </Field>
            {error && <ErrorText>{error}</ErrorText>}
            <Button type="submit" disabled={busy} className="mt-2 w-full">
              {busy ? 'Đang đăng nhập...' : 'Đăng nhập'}
            </Button>
          </form>
        </Card>
        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-600">
          <p className="mb-2 font-medium text-slate-700">Tài khoản demo (mật khẩu: password123)</p>
          <div className="space-y-1">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc}
                type="button"
                className="block w-full rounded px-2 py-1 text-left hover:bg-slate-50"
                onClick={() => setEmail(acc)}
              >
                {acc}
              </button>
            ))}
          </div>
          <p className="mt-2 text-slate-400">
            Mỗi tài khoản tương ứng một vai trò: {Object.values(ROLE_LABELS).join(', ')}.
          </p>
        </div>
      </div>
    </div>
  )
}
