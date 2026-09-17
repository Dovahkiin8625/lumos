<script setup lang="ts">
import { ref } from 'vue'
import { Sparkles, Plug } from 'lucide-vue-next'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useUiStore } from '@/stores/ui'
import { useSessionsStore } from '@/stores/sessions'
import { useSkillsStore } from '@/stores/skills'
import { useMcpsStore } from '@/stores/mcps'

const ui = useUiStore()
const sessions = useSessionsStore()
const skills = useSkillsStore()
const mcps = useMcpsStore()

const tab = ref<'skills' | 'mcp'>('skills')

async function toggleSkill(name: string, on: boolean) {
  if (!sessions.currentId) return
  await sessions.toggleSkill(name, on)
}
</script>

<template>
  <Sheet :open="ui.settingsOpen" @update:open="(v) => v ? ui.openSettings() : ui.closeSettings()">
    <SheetContent side="right" class="w-[400px] p-0 sm:max-w-[400px]">
      <SheetHeader class="border-b border-border px-4 py-3">
        <SheetTitle>设置</SheetTitle>
      </SheetHeader>

      <Tabs v-model:value="tab" class="w-full">
        <TabsList class="mx-4 mt-3">
          <TabsTrigger value="skills">
            <Sparkles class="mr-1.5 h-3.5 w-3.5" :stroke-width="1.75" />
            技能
          </TabsTrigger>
          <TabsTrigger value="mcp">
            <Plug class="mr-1.5 h-3.5 w-3.5" :stroke-width="1.75" />
            MCP
          </TabsTrigger>
        </TabsList>

        <TabsContent value="skills" class="mt-0">
          <div class="px-4 pt-3 text-xs text-muted-foreground">
            当前会话启用的技能
          </div>
          <Separator class="my-2" />
          <div v-if="!sessions.currentId" class="px-4 py-8 text-center text-sm text-muted-foreground">
            请先选择或创建一个会话
          </div>
          <div v-else-if="skills.list.length === 0" class="px-4 py-8 text-center text-sm text-muted-foreground">
            暂无可配置的技能
          </div>
          <div v-else class="flex flex-col">
            <div
              v-for="s in skills.list"
              :key="s.name"
              class="flex items-start justify-between gap-3 border-b border-border/40 px-4 py-3"
            >
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-foreground">{{ s.name }}</div>
                <div class="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                  {{ s.description }}
                </div>
              </div>
              <Switch
                :model-value="sessions.enabledSkills.has(s.name)"
                :disabled="!s.enabled"
                @update:model-value="(v) => toggleSkill(s.name, !!v)"
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="mcp" class="mt-0">
          <div class="px-4 pt-3 text-xs text-muted-foreground">
            当前已配置的 MCP 服务器
          </div>
          <Separator class="my-2" />
          <div v-if="mcps.list.length === 0" class="px-4 py-8 text-center text-sm text-muted-foreground">
            暂未配置 MCP 服务器
          </div>
          <div v-else class="flex flex-col">
            <div
              v-for="m in mcps.list"
              :key="m.id"
              class="flex items-start justify-between gap-3 border-b border-border/40 px-4 py-3"
            >
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 text-sm font-medium text-foreground">
                  {{ m.name }}
                  <span class="rounded bg-muted px-1.5 py-0.5 text-xs font-normal text-muted-foreground">
                    {{ m.transport }}
                  </span>
                </div>
                <div class="mt-0.5 font-mono text-xs text-muted-foreground truncate">
                  {{ m.config.url ?? m.config.command }}
                </div>
              </div>
            </div>
          </div>
          <div class="border-t border-border px-4 py-3 text-xs text-muted-foreground">
            如需新增/编辑 MCP，请前往
            <router-link to="/admin?tab=mcp" class="text-accent hover:underline" @click="ui.closeSettings()">
              后台管理
            </router-link>
          </div>
        </TabsContent>
      </Tabs>
    </SheetContent>
  </Sheet>
</template>