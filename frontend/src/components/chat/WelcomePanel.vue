<script setup lang="ts">
import { Sparkles, Code2, BookOpen, Wrench } from 'lucide-vue-next'

defineEmits<{ usePrompt: [string] }>()

const prompts = [
  { icon: Sparkles, label: '你能做什么？', prompt: '你能做什么？' },
  { icon: Code2, label: '写一段 Python Hello World', prompt: '写一段 Python Hello World' },
  { icon: BookOpen, label: '总结一个主题', prompt: '请总结一下 RAG 的核心思想' },
  { icon: Wrench, label: '调用工具示例', prompt: '现在有哪些工具可以用？' },
]
</script>

<template>
  <div class="flex flex-col items-center gap-6 px-6 py-12">
    <div class="flex flex-col items-center gap-2 text-center">
      <h2 class="text-2xl font-semibold tracking-tight text-foreground">开始一段新对话</h2>
      <p class="text-sm text-muted-foreground">选择一个起点，或直接在下方输入</p>
    </div>
    <div class="grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
      <button
        v-for="p in prompts"
        :key="p.label"
        class="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-left text-sm transition-colors hover:border-accent hover:bg-accent/5"
        @click="$emit('usePrompt', p.prompt)"
      >
        <component :is="p.icon" class="h-4 w-4 flex-shrink-0 text-accent" :stroke-width="1.75" />
        <span class="truncate text-foreground">{{ p.label }}</span>
      </button>
    </div>
  </div>
</template>