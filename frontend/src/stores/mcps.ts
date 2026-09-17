import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import type { McpServerCreate, McpServerOut } from '@/types/domain'

export const useMcpsStore = defineStore('mcps', () => {
  const list = ref<McpServerOut[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const { data } = await api.get<McpServerOut[]>('/api/mcp/servers')
      list.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: McpServerCreate) {
    const { data } = await api.post<McpServerOut>('/api/mcp/servers', payload)
    list.value = [...list.value, data]
    return data
  }

  async function update(id: number, payload: McpServerCreate) {
    const { data } = await api.patch<McpServerOut>(`/api/mcp/servers/${id}`, payload)
    list.value = list.value.map((m) => (m.id === id ? data : m))
    return data
  }

  async function remove(id: number) {
    await api.delete(`/api/mcp/servers/${id}`)
    list.value = list.value.filter((m) => m.id !== id)
  }

  async function test(id: number): Promise<{ ok: boolean; error?: string; tools_count?: number }> {
    const { data } = await api.post(`/api/mcp/servers/${id}/test`)
    return data
  }

  return { list, loading, load, create, update, remove, test }
})