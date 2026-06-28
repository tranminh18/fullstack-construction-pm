import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { Token } from './types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const ACCESS_KEY = 'cpm_access_token'
const REFRESH_KEY = 'cpm_refresh_token'

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(tokens: Token) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token)
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.access
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Tự refresh access token một lần khi gặp 401, rồi thử lại request gốc.
let refreshing: Promise<string | null> | null = null

async function doRefresh(): Promise<string | null> {
  const refresh = tokenStore.refresh
  if (!refresh) return null
  try {
    const resp = await axios.post<Token>(`${BASE_URL}/refresh`, { refresh_token: refresh })
    tokenStore.set(resp.data)
    return resp.data.access_token
  } catch {
    tokenStore.clear()
    return null
  }
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }
    const isAuthCall = original?.url?.includes('/token') || original?.url?.includes('/refresh')
    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true
      if (!refreshing) {
        refreshing = doRefresh().finally(() => {
          refreshing = null
        })
      }
      const newToken = await refreshing
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      }
    }
    return Promise.reject(error)
  },
)

// Đăng nhập dùng form-urlencoded theo chuẩn OAuth2 của backend.
export async function loginRequest(email: string, password: string): Promise<Token> {
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)
  const resp = await axios.post<Token>(`${BASE_URL}/token`, body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return resp.data
}
