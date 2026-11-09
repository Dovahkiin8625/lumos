<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { BookOpen, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import AdminKnowledgeBaseDialog from '@/components/admin/AdminKnowledgeBaseDialog.vue'
import { ref } from 'vue'
import { useKnowledgeBasesStore } from '@/stores/knowledge_bases'
import type { KnowledgeBaseOut } from '@/types/domain'

const router = useRouter()
const kbs = useKnowledgeBasesStore()

const dialogOpen = ref(false)
const editing = ref<KnowledgeBaseOut | null>(null)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}
function openEdit(kb: KnowledgeBaseOut) {
  editing.value = kb
  dialogOpen.value = true
}

function openDetail(kb: KnowledgeBaseOut) {
  router.push({ name: 'admin-knowledge-base-detail', params: { id: kb.id } })
}

async function onSaved() {
  toast.success('已保存')
  await kbs.load()
}

async function remove(kb: KnowledgeBaseOut) {
  if (!confirm(`确定删除知识库 "${kb.name}"？所有文档与向量数据都将被清除。`)) return
  try {
    await kbs.remove(kb.id)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

onMounted(() => kbs.load())
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">知识库</h2>
      <Button size="sm" @click="openCreate">
        <Plus class="mr-1.5 h-3.5 w-3.5" />
        新建知识库
      </Button>
    </div>

    <div
      v-if="kbs.list.length === 0"
      class="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground"
    >
      <BookOpen class="mx-auto mb-2 h-8 w-8 opacity-50" :stroke-width="1.5" />
      暂无知识库。点击"新建知识库"开始。
    </div>

    <div v-else class="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
      <Card v-for="kb in kbs.list" :key="kb.id" class="cursor-pointer transition-colors hover:bg-accent/5" @click="openDetail(kb)">
        <CardContent class="p-4">
          <div class="flex items-start gap-3">
            <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent">
              <BookOpen class="h-4.5 w-4.5" :stroke-width="1.75" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="truncate font-medium text-foreground">{{ kb.name }}</span>
                <span
                  v-if="kb.enabled"
                  class="rounded bg-accent/10 px-1.5 py-0.5 text-xs text-accent"
                >启用</span>
                <span v-else class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">停用</span>
              </div>
              <p
                v-if="kb.description"
                class="mt-1 line-clamp-2 text-xs text-muted-foreground"
              >{{ kb.description }}</p>
              <div class="mt-2 flex items-center gap-3 font-mono text-xs text-muted-foreground">
                <span>{{ kb.document_count }} 文档</span>
                <span>·</span>
                <span>{{ kb.indexed_chunk_count }} chunks</span>
                <span>·</span>
                <span class="truncate">{{ kb.embedding_model }}</span>
              </div>
            </div>
          </div>
          <div class="mt-3 flex justify-end gap-1" @click.stop>
            <Button variant="ghost" size="icon" @click.stop="openEdit(kb)">
              <Pencil class="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" @click.stop="remove(kb)">
              <Trash2 class="h-3.5 w-3.5 text-destructive" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <AdminKnowledgeBaseDialog
      v-model:open="dialogOpen"
      :editing="editing"
      @saved="onSaved"
    />
  </div>
</template>
