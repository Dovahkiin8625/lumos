import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import type { UserOut } from '@/types/domain'

const ACCESS_KEY = 'lumos.access_token'
const REFRESH_KEY = 'lumos.refresh_token'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(ACCESS_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const user = ref<UserOut | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  }

  function clear() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }

  async function login(email: string, password: string) {
    const { data } = await api.post<{
      access_token: string
      refresh_token: string
    }>('/api/auth/login', { email, password })
    setTokens(data.access_token, data.refresh_token)
    await fetchMe()
  }

  async function register(email: string, password: string) {
    const { data } = await api.post<{
      access_token: string
      refresh_token: string
    }>('/api/auth/register', { email, password })
    setTokens(data.access_token, data.refresh_token)
    await fetchMe()
  }

  async function logout() {
    try {
      await api.post('/api/auth/logout')
    } catch {
      // 即使后端失败也要清空本地状态
    }
    clear()
  }

  async function fetchMe() {
    if (!accessToken.value) return
    try {
      const { data } = await api.get<UserOut>('/api/auth/me')
      user.value = data
    } catch {
      clear()
    }
  }

  // 自动恢复登录状态
  if (accessToken.value && !user.value) {
    void fetchMe()
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    setTokens,
    clear,
    login,
    register,
    logout,
    fetchMe,
  }
})