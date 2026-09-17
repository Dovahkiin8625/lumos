import axios, { AxiosError, type AxiosRequestConfig } from 'axios'

const ACCESS_KEY = 'lumos.access_token'
const REFRESH_KEY = 'lumos.refresh_token'

export const api = axios.create({
  baseURL: '/',
  timeout: 30_000,
})

let refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (refreshing) return refreshing
  const refresh = localStorage.getItem(REFRESH_KEY)
  if (!refresh) return null
  refreshing = (async () => {
    try {
      const { data } = await axios.post<{
        access_token: string
        refresh_token: string
      }>('/api/auth/refresh', { refresh_token: refresh })
      localStorage.setItem(ACCESS_KEY, data.access_token)
      localStorage.setItem(REFRESH_KEY, data.refresh_token)
      return data.access_token
    } catch {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
      return null
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status !== 401 || original._retry || original.url?.includes('/api/auth/')) {
      return Promise.reject(error)
    }
    original._retry = true
    const token = await refreshAccessToken()
    if (!token) {
      // 刷新失败：跳转到登录页
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
      return Promise.reject(error)
    }
    original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${token}` }
    return api.request(original)
  },
)