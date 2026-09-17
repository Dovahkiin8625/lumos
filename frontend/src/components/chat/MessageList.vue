<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import MessageItem from '@/components/chat/MessageItem.vue'
import WelcomePanel from '@/components/chat/WelcomePanel.vue'

const sessions = useSessionsStore()
const emit = defineEmits<{ usePrompt: [string] }>()

const scrollerRef = ref<HTMLDivElement | null>(null)

const items = computed(() => {
  const list: Array<{ kind: 'message'; message: typeof sessions.messages[number]; streaming?: boolean; pending?: boolean } | { kind: 'placeholder' }> = []
  for (const m of sessions.messages) {
    list.push({ kind: 'message', message: m, pending: m.id.startsWith('pending-') })
  }
  if (sessions.streaming) {
    list.push({
      kind: 'message',
      message: {
        id: '__streaming__',
        role: 'assistant',
        content: sessions.streaming.content,
        tool_calls: sessions.streaming.toolCalls.length ? sessions.streaming.toolCalls : undefined,
        created_at: new Date().toISOString(),
      },
      streaming: true,
    })
  }
  return list
})

async function scrollToBottom() {
  await nextTick()
  const el = scrollerRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch(
  () => [sessions.messages.length, sessions.streaming?.content.length, sessions.streaming?.toolCalls.length],
  () => scrollToBottom(),
  { deep: true },
)
</script>

<template>
  <div ref="scrollerRef" class="flex-1 overflow-y-auto">
    <div v-if="items.length === 0" class="flex h-full items-center justify-center">
      <WelcomePanel @use-prompt="(p) => emit('usePrompt', p)" />
    </div>
    <div v-else class="mx-auto max-w-3xl py-4">
      <template v-for="(it, i) in items" :key="i">
        <MessageItem
          v-if="it.kind === 'message'"
          :message="it.message"
          :streaming="it.streaming"
          :pending="it.pending"
        />
      </template>
    </div>
  </div>
</template>