<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Sparkles, Plug } from 'lucide-vue-next'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import AdminOverview from '@/components/admin/AdminOverview.vue'
import AdminSkills from '@/components/admin/AdminSkills.vue'
import AdminMcp from '@/components/admin/AdminMcp.vue'

const route = useRoute()
const router = useRouter()

const tabs = [
  { value: 'overview', label: '总览', icon: LayoutDashboard },
  { value: 'skills', label: '技能', icon: Sparkles },
  { value: 'mcp', label: 'MCP', icon: Plug },
]

const active = computed({
  get: () => (route.query.tab as string) || 'overview',
  set: (v) => router.replace({ query: { ...route.query, tab: v } }),
})
</script>

<template>
  <div class="flex h-full flex-col">
    <Tabs v-model:value="active" class="flex h-full flex-col">
      <div class="border-b border-border px-6">
        <TabsList class="bg-transparent">
          <TabsTrigger v-for="t in tabs" :key="t.value" :value="t.value">
            <component :is="t.icon" class="mr-1.5 h-3.5 w-3.5" :stroke-width="1.75" />
            {{ t.label }}
          </TabsTrigger>
        </TabsList>
      </div>
      <div class="flex-1 overflow-y-auto p-6">
        <AdminOverview v-if="active === 'overview'" />
        <AdminSkills v-else-if="active === 'skills'" />
        <AdminMcp v-else-if="active === 'mcp'" />
      </div>
    </Tabs>
  </div>
</template>