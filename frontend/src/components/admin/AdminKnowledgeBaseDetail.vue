<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, FileText, Loader2, RefreshCw, Trash2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import AdminKnowledgeBaseDocumentUpload from '@/components/admin/AdminKnowledgeBaseDocumentUpload.vue'
import AdminKnowledgeBaseSearch from '@/components/admin/AdminKnowledgeBaseSearch.vue'
import { useKnowledgeBasesStore } from '@/stores/knowledge_bases'
import { getDocumentStatus } from '@/api/knowledge_bases'
import type { KnowledgeDocumentOut, KnowledgeDocumentStatus } from '@/types/domain'

const route = useRoute()
const router = useRouter()
const kbs = useKnowledgeBasesStore()

const kbId = computed(() => route.params.id as string)
const pollingTimers = new Map<string, ReturnType<typeof setInterval>>()

const statusColors: Record<KnowledgeDocumentStatus, string> = {
  pending: 'bg-muted text-muted-foreground',
  parsing: 'bg-blue-500/10 text-blue-600',
  chunking: 'bg-blue-500/10 text-blue-600',
  embedding: 'bg-blue-500/10 text-blue-600',
  ready: 'bg-accent/10 text-accent',
  failed: 'bg-destructive/10 text-destructive',
  deleting: 'bg-muted text-muted-foreground',
}

const statusLabel: Record<KnowledgeDocumentStatus, string> = {
  pending: '等待中',
  parsing: '解析中',
  chunking: '分片中',
  embedding: '嵌入中',
  ready: '就绪',
  failed: '失败',
  deleting: '删除中',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function refreshDetail() {
  await kbs.loadDetail(kbId.value)
  startPollingForPending()
}

function startPollingForPending() {
  // 清理旧的
  for (const t of pollingTimers.values()) clearInterval(t)
  pollingTimers.clear()
  // 找出非终态文档
  for (const doc of kbs.documents) {
    if (doc.status === 'ready' || doc.status === 'failed') continue
    pollOne(doc.id)
  }
}

function pollOne(docId: string) {
  const t = setInterval(async () => {
    try {
      const s = await getDocumentStatus(kbId.value, docId)
      const idx = kbs.documents.findIndex((d) => d.id === docId)
      if (idx >= 0) {
        kbs.documents[idx] = {
          ...kbs.documents[idx],
          status: s.status,
          chunk_count: s.chunk_count,
          error: s.error,
          indexed_at: s.indexed_at,
        }
      }
      if (s.status === 'ready' || s.status === 'failed') {
        const timer = pollingTimers.get(docId)
        if (timer) clearInterval(timer)
        pollingTimers.delete(docId)
      }
    } catch {
      // ignore
    }
  }, 1500)
  pollingTimers.set(docId, t)
}

onMounted(refreshDetail)
onUnmounted(() => {
  for (const t of pollingTimers.values()) clearInterval(t)
  pollingTimers.clear()
})

async function removeDocument(doc: KnowledgeDocumentOut) {
  if (!confirm(`确定删除文档 "${doc.filename}"？相关向量数据将被清除。`)) return
  try {
    await kbs.removeDocument(kbId.value, doc.id)
  } catch {
    // store toast not used; silent
  }
}

function back() {
  kbs.resetCurrent()
  router.push({ name: 'admin', query: { tab: 'knowledge_base' } })
}
</script>

<template>
  <div class="flex h-full flex-col gap-4">
    <div class="flex items-center gap-3">
      <Button variant="ghost" size="icon" @click="back">
        <ArrowLeft class="h-4 w-4" />
      </Button>
      <div v-if="kbs.current" class="min-w-0 flex-1">
        <h2 class="truncate text-lg font-semibold text-foreground">{{ kbs.current.name }}</h2>
        <p v-if="kbs.current.description" class="truncate text-xs text-muted-foreground">
          {{ kbs.current.description }}
        </p>
      </div>
      <Button variant="ghost" size="sm" @click="refreshDetail">
        <RefreshCw class="mr-1.5 h-3.5 w-3.5" />
        刷新
      </Button>
    </div>

    <div v-if="!kbs.current" class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
      <Loader2 class="mr-2 h-4 w-4 animate-spin" />
      加载中…
    </div>

    <div v-else class="grid flex-1 gap-4 overflow-hidden lg:grid-cols-2">
      <!-- 左栏：文档管理 -->
      <div class="flex flex-col gap-4 overflow-y-auto pr-1">
        <Card>
          <CardContent class="p-4">
            <h3 class="mb-3 text-sm font-medium text-foreground">上传文档</h3>
            <AdminKnowledgeBaseDocumentUpload
              :kb-id="kbId"
              @uploaded="refreshDetail"
            />
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-4">
            <div class="mb-3 flex items-center justify-between">
              <h3 class="text-sm font-medium text-foreground">
                文档（{{ kbs.documents.length }}）
              </h3>
            </div>
            <div v-if="kbs.documents.length === 0" class="rounded border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
              暂无文档
            </div>
            <ul v-else class="space-y-2">
              <li
                v-for="doc in kbs.documents"
                :key="doc.id"
                class="flex items-start gap-2 rounded-md border border-border p-2 text-sm"
              >
                <FileText class="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" :stroke-width="1.75" />
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <span class="truncate font-mono text-xs">{{ doc.filename }}</span>
                    <span
                      class="flex-shrink-0 rounded px-1.5 py-0.5 text-xs"
                      :class="statusColors[doc.status]"
                    >{{ statusLabel[doc.status] }}</span>
                  </div>
                  <div class="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{{ formatBytes(doc.file_size) }}</span>
                    <span v-if="doc.page_count !== null">· {{ doc.page_count }} 页</span>
                    <span v-if="doc.chunk_count > 0">· {{ doc.chunk_count }} chunks</span>
                  </div>
                  <div v-if="doc.error" class="mt-1 text-xs text-destructive">
                    {{ doc.error }}
                  </div>
                </div>
                <Button
                  v-if="doc.status === 'ready' || doc.status === 'failed'"
                  variant="ghost"
                  size="icon"
                  class="h-6 w-6"
                  @click="removeDocument(doc)"
                >
                  <Trash2 class="h-3.5 w-3.5 text-destructive" />
                </Button>
                <Loader2 v-else class="mt-1 h-3.5 w-3.5 animate-spin text-muted-foreground" />
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <!-- 右栏：检索 -->
      <div class="flex flex-col overflow-hidden">
        <Card class="flex h-full flex-col">
          <CardContent class="flex h-full flex-col p-4">
            <h3 class="mb-3 text-sm font-medium text-foreground">检索</h3>
            <AdminKnowledgeBaseSearch :kb-id="kbId" />
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
