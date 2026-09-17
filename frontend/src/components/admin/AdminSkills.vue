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

    <div v-else class="space-y-2">
      <Card v-for="s in skills.list" :key="s.name">
        <CardContent class="flex items-start gap-4 p-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-medium text-foreground">{{ s.name }}</span>
              <span class="font-mono text-xs text-muted-foreground">v{{ s.version }}</span>
            </div>
            <p class="mt-1 line-clamp-2 text-sm text-muted-foreground">{{ s.description }}</p>
            <div v-if="s.tags.length || s.required_tools.length" class="mt-2 flex flex-wrap gap-1">
              <span v-for="t in s.tags" :key="t" class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                {{ t }}
              </span>
              <span v-for="t in s.required_tools" :key="'r-'+t" class="rounded bg-accent/10 px-1.5 py-0.5 text-xs text-accent">
                {{ t }}
              </span>
            </div>
          </div>
          <div class="flex flex-shrink-0 items-center gap-2">
            <Switch :model-value="s.enabled" @update:model-value="toggle(s)" />
            <Button variant="ghost" size="icon" @click="openEdit(s)">
              <Pencil class="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" @click="remove(s)">
              <Trash2 class="h-3.5 w-3.5 text-destructive" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <AdminSkillDialog v-model:open="dialogOpen" :editing="editing" @saved="onSaved" />
  </div>
</template>
