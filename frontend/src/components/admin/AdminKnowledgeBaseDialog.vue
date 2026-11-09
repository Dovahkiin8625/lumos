<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { KnowledgeBaseCreate, KnowledgeBaseOut } from '@/types/domain'
import { api } from '@/api/client'

const props = defineProps<{ open: boolean; editing: KnowledgeBaseOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const form = ref<KnowledgeBaseCreate>({
  name: '',
  description: '',
  embedding_model: 'bge-m3',
  rerank_model: 'bge-reranker-v2-m3',
  chunk_size: 500,
  chunk_overlap: 75,
  enabled: true,
})

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
        description: props.editing.description,
        embedding_model: props.editing.embedding_model,
        rerank_model: props.editing.rerank_model,
        chunk_size: props.editing.chunk_size,
        chunk_overlap: props.editing.chunk_overlap,
        enabled: props.editing.enabled,
      }
    } else {
      form.value = {
        name: '',
        description: '',
        embedding_model: 'bge-m3',
        rerank_model: 'bge-reranker-v2-m3',
        chunk_size: 500,
        chunk_overlap: 75,
        enabled: true,
      }
    }
  },
  { immediate: true },
)

async function submit() {
  error.value = ''
  if (!form.value.name.trim()) {
    error.value = '名称必填'
    return
  }
  const cs = form.value.chunk_size ?? 500
  const co = form.value.chunk_overlap ?? 75
  if (co >= cs) {
    error.value = 'chunk_overlap 必须小于 chunk_size'
    return
  }
  loading.value = true
  try {
    if (props.editing) {
      await api.patch(`/api/knowledge_bases/${props.editing.id}`, {
        description: form.value.description,
        chunk_size: cs,
        chunk_overlap: co,
        enabled: form.value.enabled,
      })
    } else {
      await api.post('/api/knowledge_bases', form.value)
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
        <DialogTitle>{{ props.editing ? '编辑知识库' : '新建知识库' }}</DialogTitle>
        <DialogDescription>
          文档解析与向量化通过 vector-service 完成（Docling + BGE-M3）。
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-3 py-2">
        <div class="grid gap-1.5">
          <Label>名称</Label>
          <Input v-model="form.name" :disabled="!!props.editing" placeholder="my-kb" />
          <p class="text-xs text-muted-foreground">1-64 字符，字母/数字/下划线/连字符/空格</p>
        </div>

        <div class="grid gap-1.5">
          <Label>描述</Label>
          <Textarea v-model="form.description" :rows="2" placeholder="选填" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="grid gap-1.5">
            <Label>嵌入模型</Label>
            <Input v-model="form.embedding_model" :disabled="!!props.editing" />
          </div>
          <div class="grid gap-1.5">
            <Label>重排模型</Label>
            <Input v-model="form.rerank_model" :disabled="!!props.editing" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="grid gap-1.5">
            <Label>chunk_size（tokens）</Label>
            <Input
              v-model.number="form.chunk_size"
              type="number"
              :min="64"
              :max="4096"
              :disabled="!!props.editing"
            />
          </div>
          <div class="grid gap-1.5">
            <Label>chunk_overlap（tokens）</Label>
            <Input
              v-model.number="form.chunk_overlap"
              type="number"
              :min="0"
              :max="512"
              :disabled="!!props.editing"
            />
          </div>
        </div>

        <div class="grid gap-1.5">
          <Label class="flex items-center gap-2">
            <input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded border-input" />
            启用
          </Label>
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
