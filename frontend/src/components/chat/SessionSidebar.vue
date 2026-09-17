<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Trash2, MessageSquare } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useUiStore } from '@/stores/ui'
import { useSessionsStore } from '@/stores/sessions'

const ui = useUiStore()
const sessions = useSessionsStore()
const renamingId = ref<string | null>(null)
const renameDraft = ref('')

function closeSidebar() {
  ui.closeSidebar()
}

async function createAndSelect() {
  await sessions.createSession()
  closeSidebar()
}

function select(id: string) {
  if (sessions.currentId === id) {
    closeSidebar()
    return
  }
  sessions.select(id)
  closeSidebar()
}

async function deleteItem(id: string) {
  try {
    await sessions.deleteSession(id)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

function startRename(id: string, currentTitle: string) {
  renamingId.value = id
  renameDraft.value = currentTitle === '新会话' ? '' : currentTitle
}

async function commitRename(id: string) {
  const t = renameDraft.value.trim()
  renamingId.value = null
  if (!t) return
  try {
    const { api } = await import('@/api/client')
    await api.patch(`/api/sessions/${id}`, { title: t })
    const s = sessions.list.find((x) => x.id === id)
    if (s) s.title = t
    if (sessions.current?.id === id) sessions.current.title = t
  } catch {
    toast.error('重命名失败')
  }
}
</script>

<template>
  <Sheet :open="ui.sidebarOpen" @update:open="(v) => v ? ui.openSidebar() : ui.closeSidebar()">
    <SheetContent side="left" class="w-[280px] p-0">
      <SheetHeader class="border-b border-border px-4 py-3">
        <SheetTitle>会话</SheetTitle>
      </SheetHeader>

      <div class="flex items-center justify-between px-4 py-2">
        <Button variant="ghost" size="sm" class="gap-1.5" @click="createAndSelect">
          <Plus class="h-3.5 w-3.5" />
          新会话
        </Button>
      </div>
      <Separator />

      <div class="flex-1 overflow-y-auto">
        <div v-if="sessions.list.length === 0" class="px-4 py-12 text-center text-sm text-muted-foreground">
          还没有会话
        </div>
        <div v-else class="flex flex-col">
          <div
            v-for="s in sessions.list"
            :key="s.id"
            class="group flex cursor-pointer items-center justify-between gap-2 border-b border-border/40 px-4 py-2.5 hover:bg-muted/50"
            :class="{ 'bg-muted': sessions.currentId === s.id }"
            @click="select(s.id)"
          >
            <div class="flex min-w-0 flex-1 items-center gap-2">
              <MessageSquare class="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" :stroke-width="1.75" />
              <template v-if="renamingId === s.id">
                <input
                  v-model="renameDraft"
                  autofocus
                  class="min-w-0 flex-1 rounded border border-accent bg-background px-1.5 py-0.5 text-sm outline-none"
                  @click.stop
                  @keydown.enter="commitRename(s.id)"
                  @keydown.esc="renamingId = null"
                  @blur="commitRename(s.id)"
                />
              </template>
              <span v-else class="truncate text-sm text-foreground">{{ s.title || '新会话' }}</span>
            </div>
            <div class="flex flex-shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100">
              <button
                class="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                @click.stop="startRename(s.id, s.title || '')"
              >
                重命名
              </button>
              <button
                class="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                aria-label="删除"
                @click.stop="deleteItem(s.id)"
              >
                <Trash2 class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </SheetContent>
  </Sheet>
</template>