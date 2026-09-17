<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Sun, Moon, Settings, LogOut, Wrench } from 'lucide-vue-next'
import { useDark } from '@vueuse/core'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()
const isDark = useDark()

const props = defineProps<{ isAdmin: boolean }>()

const initial = computed(() => (auth.user?.email ?? '?')[0].toUpperCase())

async function logout() {
  await auth.logout()
  router.replace('/login')
}

function toggleTheme() {
  isDark.value = !isDark.value
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <button
        class="h-8 w-8 rounded-full border border-border bg-card text-sm font-semibold text-muted-foreground hover:border-accent hover:text-accent transition-colors"
        :title="auth.user?.email"
      >
        {{ initial }}
      </button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="start" :side-offset="8" class="w-48">
      <DropdownMenuItem @select="toggleTheme">
        <component :is="isDark ? Sun : Moon" class="mr-2 h-3.5 w-3.5" />
        {{ isDark ? '浅色主题' : '深色主题' }}
      </DropdownMenuItem>
      <DropdownMenuSeparator v-if="!props.isAdmin" />
      <DropdownMenuItem v-if="!props.isAdmin" @select="router.push('/admin')">
        <Settings class="mr-2 h-3.5 w-3.5" />
        后台管理
      </DropdownMenuItem>
      <DropdownMenuItem v-else @select="router.push('/chat')">
        <Wrench class="mr-2 h-3.5 w-3.5" />
        回到对话
      </DropdownMenuItem>
      <DropdownMenuItem @select="ui.openSettings()">
        <Settings class="mr-2 h-3.5 w-3.5" />
        技能 &amp; MCP
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @select="logout" class="text-destructive">
        <LogOut class="mr-2 h-3.5 w-3.5" />
        登出
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>