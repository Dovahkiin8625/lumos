<script setup lang="ts">
import { ref } from 'vue'
import { Loader2, Search, FileText, Copy, Check } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useKnowledgeBasesStore } from '@/stores/knowledge_bases'
import type { RetrievalHit } from '@/types/domain'

const props = defineProps<{ kbId: string }>()

const kbs = useKnowledgeBasesStore()

const query = ref('')
const topK = ref(8)
const useRerank = ref(true)
const searching = ref(false)
const error = ref('')
const hits = ref<RetrievalHit[]>([])
const tookMs = ref(0)
const rerankUsed = ref(false)

const copiedIdx = ref<number | null>(null)

async function doSearch() {
  error.value = ''
  if (!query.value.trim()) return
  searching.value = true
  try {
    const res = await kbs.search(props.kbId, {
      query: query.value.trim(),
      top_k: topK.value,
      use_rerank: useRerank.value,
    })
    hits.value = res.hits
    tookMs.value = res.took_ms
    rerankUsed.value = res.rerank_used
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || '检索失败'
    error.value = msg
    hits.value = []
  } finally {
    searching.value = false
  }
}

async function copyText(text: string, idx: number) {
  try {
    await navigator.clipboard.writeText(text)
    copiedIdx.value = idx
    setTimeout(() => {
      if (copiedIdx.value === idx) copiedIdx.value = null
    }, 1500)
  } catch {
    // ignore
  }
}

function highlight(text: string, q: string): string {
  if (!q.trim()) return escape(text)
  const tokens = q.trim().split(/\s+/).filter((t) => t.length >= 2)
  if (tokens.length === 0) return escape(text)
  const re = new RegExp(`(${tokens.map(escapeReg).join('|')})`, 'gi')
  return escape(text).replace(re, '<mark>$1</mark>')
}

function escape(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function escapeReg(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function pct(score: number): string {
  return (score * 100).toFixed(1) + '%'
}
</script>

<template>
  <div class="flex h-full flex-col gap-3">
    <form class="space-y-3" @submit.prevent="doSearch">
      <div class="flex gap-2">
        <Input
          v-model="query"
          placeholder="输入查询，例如：如何配置 BGE-M3 的检索前缀？"
          :disabled="searching"
          class="flex-1"
        />
        <Button type="submit" :disabled="searching || !query.trim()">
          <Loader2 v-if="searching" class="mr-1.5 h-3.5 w-3.5 animate-spin" />
          <Search v-else class="mr-1.5 h-3.5 w-3.5" />
          检索
        </Button>
      </div>
      <div class="flex items-center gap-4 text-xs text-muted-foreground">
        <div class="flex items-center gap-1.5">
          <Label class="text-xs">top_k</Label>
          <select v-model.number="topK" class="h-7 rounded border border-input bg-background px-2 text-xs">
            <option :value="5">5</option>
            <option :value="8">8</option>
            <option :value="15">15</option>
            <option :value="30">30</option>
          </select>
        </div>
        <Label class="flex items-center gap-1.5">
          <input v-model="useRerank" type="checkbox" class="h-3.5 w-3.5 rounded border-input" />
          启用重排
        </Label>
      </div>
    </form>

    <div v-if="error" class="rounded border border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive">
      {{ error }}
    </div>

    <div class="flex-1 overflow-y-auto">
      <div v-if="hits.length === 0 && !searching && !error" class="rounded border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
        输入查询后点击"检索"以查看结果。
      </div>

      <div v-else-if="hits.length === 0 && !searching" class="rounded border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
        无匹配结果。请尝试更换查询或上传更多文档。
      </div>

      <div v-else class="space-y-2">
        <div class="flex items-center justify-between text-xs text-muted-foreground">
          <span>{{ hits.length }} 条结果</span>
          <span>{{ tookMs }}ms · {{ rerankUsed ? '已重排' : '未重排' }}</span>
        </div>
        <div
          v-for="(h, idx) in hits"
          :key="idx"
          class="space-y-1.5 rounded-md border border-border bg-card p-3 text-sm"
        >
          <div class="flex items-start gap-2">
            <FileText class="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" :stroke-width="1.75" />
            <div class="min-w-0 flex-1">
              <div
                class="text-xs text-muted-foreground"
                v-html="highlight(h.text, query).slice(0, 500) + (h.text.length > 500 ? '…' : '')"
              />
              <div class="mt-1.5 flex items-center justify-between gap-2 text-xs">
                <span class="truncate font-mono text-muted-foreground">{{ h.citation }}</span>
                <span class="flex items-center gap-2">
                  <span class="rounded bg-accent/10 px-1.5 py-0.5 font-mono text-accent">{{ pct(h.score) }}</span>
                  <button
                    class="rounded p-1 text-muted-foreground hover:bg-muted"
                    :title="'复制片段'"
                    @click="copyText(h.text, idx)"
                  >
                    <Check v-if="copiedIdx === idx" class="h-3.5 w-3.5 text-accent" />
                    <Copy v-else class="h-3.5 w-3.5" />
                  </button>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
