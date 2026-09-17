<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { McpServerCreate, McpServerOut, McpTransport } from '@/types/domain'

const props = defineProps<{ open: boolean; editing: McpServerOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const transports: McpTransport[] = ['stdio', 'sse', 'streamable_http']

const form = ref<McpServerCreate>({
  name: '',
  transport: 'stdio',
  enabled: true,
  command: '',
  args: [],
  env: {},
  url: '',
  headers: {},
})

const argsText = ref('')
const envText = ref('')
const headersText = ref('')
const loading = ref(false)
const error = ref('')

watch(
  () => [props.open, props.editing?.id],
  () => {
    if (!props.open) return
    error.value = ''
    if (props.editing) {
      form.value = {
        name: props.editing.name,
        transport: props.editing.transport,
        enabled: props.editing.enabled,
        command: props.editing.config.command ?? '',
        args: props.editing.config.args ?? [],
        env: props.editing.config.env ?? {},
        url: props.editing.config.url ?? '',
        headers: props.editing.config.headers ?? {},
      }
      argsText.value = (props.editing.config.args ?? []).join('\n')
      envText.value = Object.entries(props.editing.config.env ?? {}).map(([k, v]) => `${k}=${v}`).join('\n')
      headersText.value = Object.entries(props.editing.config.headers ?? {}).map(([k, v]) => `${k}: ${v}`).join('\n')
    } else {
      form.value = { name: '', transport: 'stdio', enabled: true, command: '', args: [], env: {}, url: '', headers: {} }
      argsText.value = ''
      envText.value = ''
      headersText.value = ''
    }
  },
  { immediate: true },
)

function parseLines(s: string): string[] {
  return s.split('\n').map((x) => x.trim()).filter(Boolean)
}
function parseKv(s: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const line of parseLines(s)) {
    const i = line.indexOf('=')
    const k = (i === -1 ? line.indexOf(':') : i)
    if (k <= 0) continue
    const key = line.slice(0, k).trim()
    const val = line.slice(k + 1).trim()
    if (key) out[key] = val
  }
  return out
}

async function submit() {
  error.value = ''
  if (!form.value.name.trim()) {
    error.value = '名称必填'
    return
  }
  if (form.value.transport === 'stdio' && !form.value.command?.trim()) {
    error.value = 'stdio 传输需要 command'
    return
  }
  if ((form.value.transport === 'sse' || form.value.transport === 'streamable_http') && !form.value.url?.trim()) {
    error.value = `${form.value.transport} 传输需要 url`
    return
  }
  loading.value = true
  try {
    const payload: McpServerCreate = {
      name: form.value.name.trim(),
      transport: form.value.transport,
      enabled: form.value.enabled,
      command: form.value.command || undefined,
      args: parseLines(argsText.value),
      env: parseKv(envText.value),
      url: form.value.url || undefined,
      headers: parseKv(headersText.value),
    }
    const { api } = await import('@/api/client')
    if (props.editing) {
      await api.patch(`/api/mcp/servers/${props.editing.id}`, payload)
    } else {
      await api.post('/api/mcp/servers', payload)
    }
    emit('saved')
    emit('update:open', false)
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || '保存失败'
    error.value = msg
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog :open="props.open" @update:open="(v) => emit('update:open', v)">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-[560px]">
      <DialogHeader>
        <DialogTitle>{{ props.editing ? '编辑 MCP 服务器' : '新建 MCP 服务器' }}</DialogTitle>
        <DialogDescription>配置后点击"测试连接"验证。</DialogDescription>
      </DialogHeader>

      <div class="grid gap-3 py-2">
        <div class="grid grid-cols-2 gap-3">
          <div class="grid gap-1.5">
            <Label>名称</Label>
            <Input v-model="form.name" placeholder="my-mcp" />
          </div>
          <div class="grid gap-1.5">
            <Label>传输</Label>
            <select v-model="form.transport" class="flex h-9 rounded-md border border-input bg-background px-3 text-sm">
              <option v-for="t in transports" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
        </div>

        <div class="grid gap-1.5">
          <Label class="flex items-center gap-2">
            <input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded border-input" />
            启用
          </Label>
        </div>

        <template v-if="form.transport === 'stdio'">
          <div class="grid gap-1.5">
            <Label>命令</Label>
            <Input v-model="form.command" placeholder="python" />
          </div>
          <div class="grid gap-1.5">
            <Label>参数（每行一个）</Label>
            <Textarea v-model="argsText" :rows="3" placeholder="-m&#10;my_mcp_server" />
          </div>
        </template>

        <template v-else>
          <div class="grid gap-1.5">
            <Label>URL</Label>
            <Input v-model="form.url" placeholder="http://localhost:3000/mcp" />
          </div>
        </template>

        <div class="grid gap-1.5">
          <Label>环境变量（每行 KEY=VALUE，仅 stdio）</Label>
          <Textarea v-model="envText" :rows="2" placeholder="API_KEY=xxx" />
        </div>
        <div class="grid gap-1.5">
          <Label>Headers（每行 KEY: VALUE，仅 HTTP）</Label>
          <Textarea v-model="headersText" :rows="2" placeholder="Authorization: Bearer xxx" />
        </div>

        <div v-if="error" class="text-sm text-destructive">{{ error }}</div>
      </div>

      <DialogFooter>
        <Button variant="ghost" @click="emit('update:open', false)">取消</Button>
        <Button :disabled="loading" @click="submit">{{ loading ? '保存中…' : '保存' }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>