<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'
import 'highlight.js/styles/github-dark.css'
import { UserCircle2, Sparkles } from 'lucide-vue-next'
import ToolCallCard from '@/components/chat/ToolCallCard.vue'
import type { MessageOut, ToolCall } from '@/types/domain'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('json', json)

// Marked v14 removed the built-in `highlight` option from setOptions.
// Use the official renderer override so hljs actually runs against code blocks.
marked.use({
  breaks: true,
  renderer: {
    code(token: { text: string; lang?: string } | string): string {
      const code = typeof token === 'string' ? token : token.text
      const lang = typeof token === 'string' ? undefined : token.lang
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
      const highlighted =
        lang && hljs.getLanguage(lang)
          ? hljs.highlight(code, { language: lang }).value
          : hljs.highlightAuto(code).value
      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
    },
  },
})

const props = defineProps<{
  message: MessageOut
  streaming?: boolean
  pending?: boolean
}>()

const emit = defineEmits<{ usePrompt: [string] }>()

const html = computed(() => {
  if (props.message.role !== 'assistant') return ''
  try {
    return marked.parse(props.message.content) as string
  } catch {
    return ''
  }
})

const toolCalls = computed<ToolCall[]>(() => props.message.tool_calls ?? [])
</script>

<template>
  <div class="flex w-full gap-3 px-4 py-3">
    <div
      class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-border bg-card"
    >
      <UserCircle2 v-if="message.role === 'user'" class="h-4 w-4 text-muted-foreground" />
      <Sparkles v-else class="h-4 w-4 text-accent" />
    </div>

    <div class="min-w-0 flex-1">
      <div class="mb-1 text-xs font-medium text-muted-foreground">
        {{ message.role === 'user' ? '你' : '助手' }}
      </div>

      <div
        v-if="message.role === 'user'"
        class="inline-block max-w-[80%] rounded-2xl bg-muted px-3 py-2 text-sm text-foreground"
      >
        {{ message.content }}
      </div>

      <div v-else>
        <div
          v-if="html"
          class="prose prose-sm max-w-none dark:prose-invert prose-pre:my-2 prose-code:before:hidden prose-code:after:hidden"
          v-html="html"
        />
        <span v-if="streaming" class="ml-0.5 inline-block h-4 w-1 animate-pulse bg-foreground" />

        <ToolCallCard v-for="call in toolCalls" :key="call.id" :call="call" class="my-2" />
      </div>

      <div v-if="pending" class="mt-1 text-xs text-muted-foreground">…</div>
    </div>
  </div>
</template>