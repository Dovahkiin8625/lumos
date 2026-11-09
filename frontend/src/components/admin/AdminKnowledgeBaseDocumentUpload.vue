<script setup lang="ts">
import { ref } from 'vue'
import { Upload, X } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { useKnowledgeBasesStore } from '@/stores/knowledge_bases'
import type { KnowledgeDocumentOut } from '@/types/domain'

const props = defineProps<{ kbId: string }>()
const emit = defineEmits<{ uploaded: [KnowledgeDocumentOut] }>()

const kbs = useKnowledgeBasesStore()
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const queue = ref<{ file: File; status: 'pending' | 'uploading' | 'done' | 'failed'; error?: string }[]>([])

const ACCEPT = '.pdf,.docx,.pptx,.md,.markdown,.txt,.html,.htm'

function openPicker() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  enqueueFiles(Array.from(input.files))
  input.value = ''
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return
  enqueueFiles(Array.from(files))
}

function enqueueFiles(files: File[]) {
  for (const f of files) {
    if (f.size > 200 * 1024 * 1024) {
      queue.value.push({ file: f, status: 'failed', error: '文件超过 200MB' })
      continue
    }
    queue.value.push({ file: f, status: 'pending' })
  }
  void runQueue()
}

async function runQueue() {
  for (const item of queue.value) {
    if (item.status !== 'pending') continue
    item.status = 'uploading'
    try {
      const doc = await kbs.uploadDocument(props.kbId, item.file)
      item.status = 'done'
      emit('uploaded', doc)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || '上传失败'
      item.status = 'failed'
      item.error = msg
    }
  }
}

function clearDone() {
  queue.value = queue.value.filter((i) => i.status === 'uploading' || i.status === 'pending')
}

function removeItem(idx: number) {
  queue.value.splice(idx, 1)
}
</script>

<template>
  <div class="space-y-3">
    <div
      class="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border p-6 text-center text-sm transition-colors"
      :class="{ 'border-accent bg-accent/5': dragOver }"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop="onDrop"
    >
      <Upload class="h-6 w-6 text-muted-foreground" :stroke-width="1.5" />
      <div class="text-muted-foreground">
        拖放文件到此处，或
        <button class="text-accent underline-offset-2 hover:underline" @click="openPicker">选择文件</button>
      </div>
      <div class="text-xs text-muted-foreground">PDF · DOCX · PPTX · Markdown · HTML · TXT（≤ 50 MB）</div>
      <input
        ref="fileInput"
        type="file"
        multiple
        :accept="ACCEPT"
        class="hidden"
        @change="onFileChange"
      />
    </div>

    <div v-if="queue.length > 0" class="space-y-1">
      <div class="flex items-center justify-between text-xs text-muted-foreground">
        <span>{{ queue.length }} 个文件</span>
        <Button v-if="queue.some((i) => i.status === 'done' || i.status === 'failed')" variant="ghost" size="sm" @click="clearDone">
          清除已完成
        </Button>
      </div>
      <ul class="space-y-1 text-xs">
        <li
          v-for="(item, idx) in queue"
          :key="idx"
          class="flex items-center justify-between gap-2 rounded border border-border px-2 py-1.5"
        >
          <div class="min-w-0 flex-1 truncate">
            <div class="truncate font-mono">{{ item.file.name }}</div>
            <div class="text-muted-foreground">
              <template v-if="item.status === 'pending'">等待中</template>
              <template v-else-if="item.status === 'uploading'">上传中…</template>
              <template v-else-if="item.status === 'done'" class="text-accent">已上传 · 索引中…</template>
              <template v-else class="text-destructive">失败：{{ item.error }}</template>
            </div>
          </div>
          <Button variant="ghost" size="icon" class="h-6 w-6" @click="removeItem(idx)">
            <X class="h-3.5 w-3.5" />
          </Button>
        </li>
      </ul>
    </div>
  </div>
</template>
