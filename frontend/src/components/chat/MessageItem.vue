<script setup lang="ts">
import { computed } from 'vue'
import 'highlight.js/styles/github-dark.css'
import { UserCircle2, Sparkles } from 'lucide-vue-next'
import ToolCallCard from '@/components/chat/ToolCallCard.vue'
import type { MessageOut, ToolCall } from '@/types/domain'
import { useMarkdown } from '@/composables/useMarkdown'

const props = defineProps<{
  message: MessageOut
  streaming?: boolean
  pending?: boolean
}>()

const emit = defineEmits<{ usePrompt: [string] }>()

const { render } = useMarkdown()

const html = computed(() => {
  if (props.message.role !== 'assistant') return ''
  return render(props.message.content)
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