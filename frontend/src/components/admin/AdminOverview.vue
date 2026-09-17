<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw, Activity, Database, Cpu, Plug } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { api } from '@/api/client'
import { useSessionsStore } from '@/stores/sessions'
import { useMcpsStore } from '@/stores/mcps'

interface Health {
  status: string
  version: string
  providers: Record<string, string>
  mcp_servers: Record<string, string>
  db: string
}

const sessions = useSessionsStore()
const mcps = useMcpsStore()

const health = ref<Health | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<Health>('/api/health')
    health.value = data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([sessions.loadList(), mcps.load()])
  await load()
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">总览</h2>
      <Button variant="ghost" size="sm" :disabled="loading" @click="load">
        <RefreshCw class="mr-1.5 h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
        刷新
      </Button>
    </div>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-2">
          <CardTitle class="text-xs font-medium text-muted-foreground">会话数</CardTitle>
          <Activity class="h-3.5 w-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-semibold text-foreground">{{ sessions.list.length }}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-2">
          <CardTitle class="text-xs font-medium text-muted-foreground">MCP 服务器</CardTitle>
          <Plug class="h-3.5 w-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-semibold text-foreground">{{ mcps.list.length }}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-2">
          <CardTitle class="text-xs font-medium text-muted-foreground">数据库</CardTitle>
          <Database class="h-3.5 w-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-semibold" :class="health?.db === 'ok' ? 'text-foreground' : 'text-destructive'">
            {{ health?.db ?? '—' }}
          </div>
        </CardContent>
      </Card>
    </div>

    <Card>
      <CardHeader>
        <CardTitle class="text-sm font-medium">系统健康</CardTitle>
      </CardHeader>
      <CardContent class="space-y-2 text-sm">
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">总体状态</span>
          <span class="font-mono" :class="health?.status === 'ok' ? 'text-foreground' : 'text-destructive'">
            {{ health?.status ?? '—' }}
          </span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">版本</span>
          <span class="font-mono text-foreground">{{ health?.version ?? '—' }}</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">Providers</span>
          <span class="font-mono text-foreground">
            <template v-for="(v, k) in health?.providers ?? {}" :key="k">
              {{ k }}={{ v }}
            </template>
          </span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">Provider 状态</span>
          <Cpu class="h-3.5 w-3.5 text-muted-foreground" />
        </div>
        <div v-if="health?.mcp_servers && Object.keys(health.mcp_servers).length" class="mt-2 space-y-1 border-t border-border pt-2">
          <div
            v-for="(v, k) in health.mcp_servers"
            :key="k"
            class="flex items-center justify-between text-xs"
          >
            <span class="font-mono text-muted-foreground">{{ k }}</span>
            <span :class="v === 'connected' ? 'text-foreground' : 'text-destructive'">{{ v }}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>