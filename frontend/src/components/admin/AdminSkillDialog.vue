<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import type { SkillOut, SkillCreate } from '@/types/domain'
import { useSkillsStore } from '@/stores/skills'

const props = defineProps<{ open: boolean; editing: SkillOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const form = ref<SkillCreate>({
  name: '',
  description: '',
  version: '0.0.0',
  tags: [],
  required_tools: [],
  optional_tools: [],
  max_steps: null,
  instructions: '',
})

const tagsText = ref('')
const requiredText = ref('')
const optionalText = ref('')
const loading = ref(false)
const error = ref('')

watch(
  () => [props.open, props.editing?.name],
  () => {
    if (!props.open) return
    error.value = ''
    if (props.editing) {
      form.value = {
        name: props.editing.name,
        description: props.editing.description,
        version: props.editing.version,
        tags: [...props.editing.tags],
        required_tools: [...props.editing.required_tools],
        optional_tools: [...props.editing.optional_tools],
        max_steps: props.editing.max_steps,
        instructions: props.editing.instructions,
      }
      tagsText.value = props.editing.tags.join(', ')
      requiredText.value = props.editing.required_tools.join(', ')
      optionalText.value = props.editing.optional_tools.join(', ')
    } else {
      form.value = { name: '', description: '', version: '0.0.0', tags: [], required_tools: [], optional_tools: [], max_steps: null, instructions: '' }
      tagsText.value = ''
      requiredText.value = ''
      optionalText.value = ''
    }
  },
  { immediate: true },
)

function splitCsv(s: string): string[] {
  return s.split(',').map((x) => x.trim()).filter(Boolean)
}

async function submit() {
  error.value = ''
  if (!form.value.name.trim()) {
    error.value = '名称必填'
    return
  }
  loading.value = true
  try {
    const payload: SkillCreate = {
      name: form.value.name.trim(),
      description: form.value.description,
      version: form.value.version,
      tags: splitCsv(tagsText.value),
      required_tools: splitCsv(requiredText.value),
      optional_tools: splitCsv(optionalText.value),
      max_steps: form.value.max_steps,
      instructions: form.value.instructions,
    }
    const store = useSkillsStore()
    if (props.editing) {
      await store.update(props.editing.name, payload)
    } else {
      await store.create(payload)
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
        <DialogTitle>{{ props.editing ? '编辑技能' : '新建技能' }}</DialogTitle>
        <DialogDescription>
          技能以 SKILL.md 文件存储于 <code>skills.dirs[0]</code>
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-3 py-2">
        <div class="grid gap-1.5">
          <Label>名称</Label>
          <Input v-model="form.name" :disabled="!!props.editing" placeholder="my-skill" />
        </div>
        <div class="grid gap-1.5">
          <Label>描述</Label>
          <Input v-model="form.description" placeholder="一句话说明" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="grid gap-1.5">
            <Label>版本</Label>
            <Input v-model="form.version" placeholder="0.0.0" />
          </div>
          <div class="grid gap-1.5">
            <Label>最大步数</Label>
            <Input
              type="number"
              min="1"
              max="200"
              placeholder="留空 = 默认"
              :model-value="form.max_steps ?? ''"
              @update:model-value="(v: string | number) => form.max_steps = (v === '' || v === null) ? null : Number(v)"
            />
          </div>
        </div>
        <div class="grid gap-1.5">
          <Label>标签（逗号分隔）</Label>
          <Input v-model="tagsText" placeholder="tag1, tag2" />
        </div>
        <div class="grid gap-1.5">
          <Label>必需工具（逗号分隔）</Label>
          <Input v-model="requiredText" placeholder="file_read, http_request" />
        </div>
        <div class="grid gap-1.5">
          <Label>可选工具（逗号分隔）</Label>
          <Input v-model="optionalText" placeholder="shell" />
        </div>
        <div class="grid gap-1.5">
          <Label>指令</Label>
          <Textarea v-model="form.instructions" :rows="6" placeholder="Markdown 格式的技能指令..." />
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
