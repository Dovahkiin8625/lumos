<script setup lang="ts">
import { computed, onMounted, ref, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu, ArrowLeft, Pencil, Check, X } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import Logo from '@/components/common/Logo.vue'
import AvatarMenu from '@/components/common/AvatarMenu.vue'
import SessionSidebar from '@/components/chat/SessionSidebar.vue'
import SettingsDrawer from '@/components/settings/SettingsDrawer.vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionsStore } from '@/stores/sessions'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const sessions = useSessionsStore()
const ui = useUiStore()

const isAdmin = computed(() => route.path.startsWith('/admin'))
const editingTitle = ref(false)
const titleDraft = ref('')

const title = computed(() => {
  if (!sessions.current) return '新对话'
  return sessions.current.title?.trim() || '新对话'
})

function startEdit() {
  if (isAdmin.value || !sessions.current) return
  titleDraft.value = title.value === '新对话' ? '' : title.value
  editingTitle.value = true
}

async function commitEdit() {
  const t = titleDraft.value.trim()
  editingTitle.value = false
  if (!sessions.current || !t || t === title.value) return
  try {
    await api.patch(`/api/sessions/${sessions.current.id}`, { title: t })
    sessions.current.title = t
    toast.success('已重命名')
  } catch {
    toast.error('重命名失败')
  }
}

function cancelEdit() { editingTitle.value = false }

function backToChat() { router.push('/chat') }

function onKey(e: KeyboardEvent) {
  const mod = e.metaKey || e.ctrlKey
  if (mod && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    ui.toggleSidebar()
  }
  if (e.key === 'Escape' && ui.sidebarOpen) {
    ui.closeSidebar()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="flex h-screen flex-col bg-background">
    <header class="flex h-12 flex-shrink-0 items-center gap-2 border-b border-border bg-background px-3">
      <button
        v-if="!isAdmin"
        class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        aria-label="打开会话列表"
        @click="ui.toggleSidebar()"
      >
        <Menu class="h-4 w-4" :stroke-width="1.75" />
      </button>
      <button
        v-else
        class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        aria-label="返回对话"
        @click="backToChat"
      >
        <ArrowLeft class="h-4 w-4" :stroke-width="1.75" />
      </button>

      <a
        class="inline-flex cursor-pointer items-center rounded-md px-1.5 py-1 hover:bg-muted transition-colors"
        @click="isAdmin ? backToChat() : router.push('/chat')"
      >
        <Logo :size="20" />
      </a>

      <div class="flex min-w-0 flex-1 items-center gap-1">
        <template v-if="editingTitle">
          <input
            v-model="titleDraft"
            autofocus
            class="rounded-md border border-accent bg-muted px-2.5 py-1 text-sm font-medium text-foreground outline-none ring-2 ring-ring"
            @keydown.enter="commitEdit"
            @keydown.esc="cancelEdit"
            @blur="commitEdit"
          />
          <button class="inline-flex h-6 w-6 items-center justify-center rounded-md hover:bg-muted" @click="commitEdit">
            <Check class="h-3 w-3" :stroke-width="2" />
          </button>
          <button class="inline-flex h-6 w-6 items-center justify-center rounded-md hover:bg-muted" @click="cancelEdit">
            <X class="h-3 w-3" :stroke-width="2" />
          </button>
        </template>
        <button
          v-else
          class="group inline-flex max-w-[320px] items-center gap-1.5 truncate rounded-md px-2.5 py-1 text-sm font-medium text-foreground hover:bg-muted transition-colors disabled:cursor-default disabled:hover:bg-transparent"
          :class="{ 'text-muted-foreground font-normal': !sessions.current }"
          :disabled="isAdmin"
          @click="startEdit"
        >
          {{ isAdmin ? '后台管理' : title }}
          <Pencil v-if="!isAdmin && sessions.current" class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" :stroke-width="1.75" />
        </button>
      </div>
    </header>

    <main class="flex min-h-0 flex-1 flex-col overflow-hidden">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <div v-if="auth.user" class="fixed bottom-4 left-4 z-50">
      <AvatarMenu :is-admin="isAdmin" />
    </div>

    <SessionSidebar />
    <SettingsDrawer />
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 150ms ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>