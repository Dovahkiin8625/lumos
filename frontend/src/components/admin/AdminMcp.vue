<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Plus, Pencil, Trash2, Plug, CheckCircle2 } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useMcpsStore } from '@/stores/mcps'
import AdminMcpDialog from '@/components/admin/AdminMcpDialog.vue'
import type { McpServerOut } from '@/types/domain'

const mcps = useMcpsStore()
const dialogOpen = ref(false)
const editing = ref<McpServerOut | null>(null)
const testing = ref<number | null>(null)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}
function openEdit(m: McpServerOut) {
  editing.value = m
  dialogOpen.value = true
}

async function onSaved() {
  toast.success('已保存')
  await mcps.load()
}

async function remove(m: McpServerOut) {
  if (!confirm(`确定删除 MCP 服务器 "${m.name}"？`)) return
  try {
    await mcps.remove(m.id)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

async function test(m: McpServerOut) {
  testing.value = m.id
  try {
    const res = await mcps.test(m.id)
    if (res.ok) {
      toast.success(`连接成功，发现 ${res.tools_count ?? 0} 个工具`)
    } else {
      toast.error(`连接失败：${res.error}`)
    }
  } catch {
    toast.error('测试请求失败')
  } finally {
    testing.value = null
  }
}

onMounted(() => mcps.load())
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">MCP 服务器</h2>
      <Button size="sm" @click="openCreate">
        <Plus class="mr-1.5 h-3.5 w-3.5" />
        新建
      </Button>
    </div>

    <div v-if="mcps.list.length === 0" class="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
      暂无 MCP 服务器。
    </div>

    <div v-else class="space-y-2">
      <Card v-for="m in mcps.list" :key="m.id">
        <CardContent class="flex items-start gap-4 p-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <Plug class="h-3.5 w-3.5 text-muted-foreground" :stroke-width="1.75" />
              <span class="font-medium text-foreground">{{ m.name }}</span>
              <span class="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-muted-foreground">
                {{ m.transport }}
              </span>
              <span v-if="m.enabled" class="rounded bg-accent/10 px-1.5 py-0.5 text-xs text-accent">
                启用
              </span>
              <span v-else class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                停用
              </span>
            </div>
            <div class="mt-1 truncate font-mono text-xs text-muted-foreground">
              {{ m.config.url ?? `${m.config.command} ${(m.config.args ?? []).join(' ')}` }}
            </div>
          </div>
          <div class="flex flex-shrink-0 items-center gap-2">
            <Button variant="ghost" size="sm" :disabled="testing === m.id" @click="test(m)">
              <component
                :is="testing === m.id ? null : CheckCircle2"
                class="mr-1.5 h-3.5 w-3.5"
              />
              {{ testing === m.id ? '测试中…' : '测试连接' }}
            </Button>
            <Button variant="ghost" size="icon" @click="openEdit(m)">
              <Pencil class="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" @click="remove(m)">
              <Trash2 class="h-3.5 w-3.5 text-destructive" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <AdminMcpDialog v-model:open="dialogOpen" :editing="editing" @saved="onSaved" />
  </div>
</template>