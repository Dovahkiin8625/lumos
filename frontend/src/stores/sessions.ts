import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { MessageOut, SessionOut, ToolCall, WsServerEvent } from '@/types/domain'
import { WsClient } from '@/api/ws'

export const useSessionsStore = defineStore('sessions', () => {
  const list = ref<SessionOut[]>([])
  const currentId = ref<string | null>(null)
  const current = ref<SessionOut | null>(null)
  const messages = ref<MessageOut[]>([])
  const enabledSkills = ref<Set<string>>(new Set())
  const streaming = ref<{
    content: string
    toolCalls: ToolCall[]
    promptTokens?: number
    completionTokens?: number
  } | null>(null)

  let ws: WsClient | null = null

  async function loadList() {
    const { data } = await api.get<SessionOut[]>('/api/sessions')
    list.value = data
  }

  async function createSession() {
    const { data } = await api.post<SessionOut>('/api/sessions', {})
    list.value.unshift(data)
    await select(data.id)
  }

  async function select(id: string) {
    if (currentId.value === id) return
    disconnect()
    const { data } = await api.get<SessionOut>(`/api/sessions/${id}`)
    current.value = data
    currentId.value = id
    enabledSkills.value = new Set(data.enabled_skills ?? [])
    await loadMessages(id)
    connect(id)
  }

  async function loadMessages(id: string) {
    const { data } = await api.get<MessageOut[]>(`/api/sessions/${id}/messages`)
    messages.value = data
  }

  function connect(id: string) {
    const auth = useAuthStore()
    if (!auth.accessToken) return
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    // 每次重连重新解析 token，避免 token 过期后用旧 token 进入死循环。
    ws = new WsClient(() => {
      const t = useAuthStore().accessToken
      if (!t) return null
      return `${proto}://${location.host}/ws/sessions/${id}?token=${t}`
    })
    ws.onMessage(handleWsEvent)
    ws.onClose(() => {
      if (currentId.value === id) ws = null
    })
    ws.connect()
  }

  function disconnect() {
    ws?.close()
    ws = null
  }

  function handleWsEvent(ev: WsServerEvent) {
    switch (ev.type) {
      case 'text': {
        if (!streaming.value) {
          streaming.value = { content: '', toolCalls: [] }
        }
        streaming.value.content += ev.data.delta
        break
      }
      case 'tool_call_start': {
        if (!streaming.value) streaming.value = { content: '', toolCalls: [] }
        for (const c of ev.data.calls) {
          const existing = streaming.value.toolCalls.find((t) => t.id === c.id)
          if (existing) Object.assign(existing, c)
          else streaming.value.toolCalls.push({ ...c })
        }
        break
      }
      case 'tool_call_result': {
        if (!streaming.value) return
        const t = streaming.value.toolCalls.find((c) => c.id === ev.data.tool_call_id)
        if (t) {
          t.result = ev.data.result
          t.is_error = ev.data.is_error
        }
        break
      }
      case 'usage': {
        if (streaming.value) {
          streaming.value.promptTokens = ev.data.prompt_tokens
          streaming.value.completionTokens = ev.data.completion_tokens
        }
        break
      }
      case 'done': {
        if (streaming.value) {
          messages.value.push({
            id: `stream-${Date.now()}`,
            role: 'assistant',
            content: streaming.value.content,
            tool_calls: streaming.value.toolCalls.length ? streaming.value.toolCalls : undefined,
            prompt_tokens: streaming.value.promptTokens,
            completion_tokens: streaming.value.completionTokens,
            created_at: new Date().toISOString(),
          })
        }
        streaming.value = null
        void loadList() // 刷新侧边栏时间戳
        break
      }
      case 'cancelled': {
        streaming.value = null
        break
      }
      case 'error': {
        streaming.value = null
        // eslint-disable-next-line no-alert
        alert(ev.data.message)
        break
      }
      case 'tool_call_end':
      case 'confirm_required':
        break
    }
  }

  function send(content: string) {
    if (!ws || !currentId.value) return
    if (!content.trim()) return
    messages.value.push({
      id: `pending-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    })
    lastUserMessage.value = content
    ws.send({
      type: 'user_message',
      content,
      enabled_skills: Array.from(enabledSkills.value),
    })
  }

  function cancel() {
    ws?.send({ type: 'cancel' })
  }

  const lastUserMessage = ref<string>('')

  function regenerate() {
    if (!lastUserMessage.value) return
    send(lastUserMessage.value)
  }

  async function toggleSkill(name: string, on: boolean) {
    if (!currentId.value) return
    if (on) enabledSkills.value.add(name)
    else enabledSkills.value.delete(name)
    await api.patch(`/api/sessions/${currentId.value}`, {
      enabled_skills: Array.from(enabledSkills.value),
    })
  }

  async function deleteSession(id: string) {
    await api.delete(`/api/sessions/${id}`)
    if (currentId.value === id) {
      disconnect()
      currentId.value = null
      current.value = null
      messages.value = []
    }
    list.value = list.value.filter((s) => s.id !== id)
  }

  return {
    list,
    currentId,
    current,
    messages,
    enabledSkills,
    streaming,
    lastUserMessage,
    loadList,
    createSession,
    select,
    deleteSession,
    send,
    cancel,
    regenerate,
    toggleSkill,
    disconnect,
  }
})