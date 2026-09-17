import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import type { SkillCreate, SkillOut, SkillUpdate } from '@/types/domain'

export const useSkillsStore = defineStore('skills', () => {
  const list = ref<SkillOut[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const { data } = await api.get<SkillOut[]>('/api/skills')
      list.value = data
    } finally {
      loading.value = false
    }
  }

  async function getOne(name: string): Promise<SkillOut> {
    const { data } = await api.get<SkillOut>(`/api/skills/${encodeURIComponent(name)}`)
    return data
  }

  async function create(payload: SkillCreate): Promise<SkillOut> {
    const { data } = await api.post<SkillOut>('/api/skills', payload)
    list.value = [...list.value, data]
    return data
  }

  async function update(name: string, payload: SkillUpdate): Promise<SkillOut> {
    const { data } = await api.put<SkillOut>(
      `/api/skills/${encodeURIComponent(name)}`,
      payload,
    )
    const idx = list.value.findIndex((s) => s.name === name)
    if (idx >= 0) list.value.splice(idx, 1, data)
    return data
  }

  async function remove(name: string) {
    await api.delete(`/api/skills/${encodeURIComponent(name)}`)
    list.value = list.value.filter((s) => s.name !== name)
  }

  async function setEnabled(name: string, enabled: boolean) {
    const path = enabled ? 'enable' : 'disable'
    await api.post(`/api/skills/${encodeURIComponent(name)}/${path}`)
    const target = list.value.find((s) => s.name === name)
    if (target) target.enabled = enabled
  }

  async function enable(name: string) {
    return setEnabled(name, true)
  }

  async function disable(name: string) {
    return setEnabled(name, false)
  }

  async function reload() {
    await api.post('/api/skills/reload')
    await load()
  }

  return { list, loading, load, getOne, create, update, remove, setEnabled, enable, disable, reload }
})
