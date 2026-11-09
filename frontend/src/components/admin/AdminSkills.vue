<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Plus, Pencil, Trash2, RotateCw } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { useSkillsStore } from '@/stores/skills'
import type { SkillOut } from '@/types/domain'
import AdminSkillDialog from '@/components/admin/AdminSkillDialog.vue'

const skills = useSkillsStore()
const dialogOpen = ref(false)
const editing = ref<SkillOut | null>(null)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}
function openEdit(s: SkillOut) {
  editing.value = s
  dialogOpen.value = true
}

async function onSaved() {
  toast.success('已保存')
}

async function toggle(s: SkillOut) {
  try {
    if (s.enabled) await skills.disable(s.name)
    else await skills.enable(s.name)
  } catch {
    toast.error('操作失败')
  }
}

async function remove(s: SkillOut) {
  if (!confirm(`确定删除技能 "${s.name}"？`)) return
  try {
    await skills.remove(s.name)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

async function reload() {
  try {
    await skills.reload()
    toast.success('已重载')
  } catch {
    toast.error('重载失败')
  }
}

function fileName(path: string): string {
  if (!path) return ''
  const parts = path.split(/[\\/]/).filter(Boolean)
  return parts[parts.length - 1] ?? path
}

// Single source for the bottom meta-line so all chips sit on one row.
function chipMeta(s: SkillOut) {
  const tags = s.tags.map((t) => ({ key: 'tag-' + t, label: t, kind: 'tag' as const }))
  const req = s.required_tools.map((t) => ({ key: 'r-' + t, label: t, kind: 'req' as const }))
  const opt = s.optional_tools.map((t) => ({ key: 'o-' + t, label: t, kind: 'opt' as const }))
  return [...tags, ...req, ...opt]
}

onMounted(() => skills.load())
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">技能</h2>
      <div class="flex gap-2">
        <Button variant="ghost" size="sm" @click="reload">
          <RotateCw class="mr-1.5 h-3.5 w-3.5" />
          重载
        </Button>
        <Button size="sm" @click="openCreate">
          <Plus class="mr-1.5 h-3.5 w-3.5" />
          新建
        </Button>
      </div>
    </div>

    <div v-if="skills.list.length === 0" class="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
      暂无技能。点击右上角"新建"或放入 <code>skills.dirs[0]</code> 目录后点"重载"。
    </div>

    <div
      v-else
      class="grid gap-2.5 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3"
    >
      <Card v-for="s in skills.list" :key="s.name" class="flex flex-col py-0">
        <CardContent class="flex flex-1 flex-col gap-1.5 p-3">
          <!-- 顶部：名称 + 开关 + 操作 -->
          <div class="flex items-center justify-between gap-2">
            <div class="flex min-w-0 flex-1 items-baseline gap-1.5">
              <span class="truncate text-sm font-medium text-foreground">{{ s.name }}</span>
              <span class="font-mono text-[10px] text-muted-foreground">v{{ s.version }}</span>
              <span
                v-if="s.dir_path"
                class="truncate font-mono text-[10px] text-muted-foreground/70"
                :title="s.dir_path"
              >
                · {{ fileName(s.dir_path) }}
              </span>
            </div>
            <div class="flex flex-shrink-0 items-center gap-0.5">
              <Switch
                :model-value="s.enabled"
                size="sm"
                @update:model-value="toggle(s)"
              />
              <Button variant="ghost" size="icon" class="h-6 w-6" @click="openEdit(s)" title="编辑">
                <Pencil class="h-3 w-3" />
              </Button>
              <Button variant="ghost" size="icon" class="h-6 w-6" @click="remove(s)" title="删除">
                <Trash2 class="h-3 w-3 text-destructive" />
              </Button>
            </div>
          </div>

          <!-- 描述 -->
          <p class="line-clamp-1 text-xs text-foreground/80" :title="s.description">
            {{ s.description || '—' }}
          </p>

          <!-- 元信息行：标签 + 工具 -->
          <div v-if="chipMeta(s).length" class="flex flex-wrap gap-1">
            <span
              v-for="m in chipMeta(s)"
              :key="m.key"
              :class="[
                'rounded px-1.5 py-0.5 text-[10px] font-mono',
                m.kind === 'req'
                  ? 'bg-accent/10 text-accent'
                  : m.kind === 'opt'
                    ? 'bg-muted text-muted-foreground'
                    : 'bg-muted text-muted-foreground',
              ]"
            >
              {{ m.label }}
            </span>
          </div>

          <!-- 底部：最大步数 -->
          <div class="mt-auto flex items-center justify-between text-[10px] text-muted-foreground">
            <span class="uppercase tracking-wider">最大步数</span>
            <span class="font-mono text-foreground/80">{{ s.max_steps ?? '默认' }}</span>
          </div>
        </CardContent>
      </Card>
    </div>

    <AdminSkillDialog v-model:open="dialogOpen" :editing="editing" @saved="onSaved" />
  </div>
</template>