<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Mail, Lock, ArrowRight } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Logo from '@/components/common/Logo.vue'
import { useAuthStore } from '@/stores/auth'

type Mode = 'login' | 'register'
const mode = ref<Mode>('login')
const loading = ref(false)
const email = ref('')
const password = ref('')
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const title = computed(() => (mode.value === 'login' ? '欢迎回来' : '创建账号'))
const buttonLabel = computed(() => (mode.value === 'login' ? '继续' : '注册'))

async function submit() {
  if (!email.value || password.value.length < 8) {
    toast.warning('密码至少 8 位')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(email.value, password.value)
      toast.success('已登录')
    } else {
      await auth.register(email.value, password.value)
      toast.success('已注册')
    }
    const redirect = (route.query.redirect as string) || '/chat'
    router.replace(redirect)
  } catch (err: unknown) {
    const msg =
      (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
      (mode.value === 'login' ? '登录失败' : '注册失败')
    toast.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center bg-background p-6">
    <div class="flex w-full max-w-[360px] flex-col gap-6">
      <Logo :size="28" />

      <h1 class="text-2xl font-semibold tracking-tight text-foreground">
        {{ title }}
      </h1>

      <Tabs v-model:value="mode">
        <TabsList class="w-fit">
          <TabsTrigger value="login">登录</TabsTrigger>
          <TabsTrigger value="register">注册</TabsTrigger>
        </TabsList>
      </Tabs>

      <form class="flex flex-col gap-2" @submit.prevent="submit">
        <div class="relative">
          <Mail class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" :stroke-width="1.75" />
          <Input
            v-model="email"
            type="email"
            placeholder="邮箱"
            autocomplete="email"
            class="pl-10"
            required
          />
        </div>

        <div class="relative">
          <Lock class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" :stroke-width="1.75" />
          <Input
            v-model="password"
            type="password"
            placeholder="密码（至少 8 位）"
            autocomplete="current-password"
            class="pl-10"
            required
            @keyup.enter="submit"
          />
        </div>

        <Button type="submit" :disabled="loading" class="mt-2 h-10 w-full">
          <span>{{ loading ? '处理中…' : buttonLabel }}</span>
          <ArrowRight v-if="!loading" class="h-3.5 w-3.5" :stroke-width="2" />
        </Button>
      </form>
    </div>
  </div>
</template>
