<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { Send, Square } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useSessionsStore } from '@/stores/sessions'

const sessions = useSessionsStore()

const text = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)

const canSend = computed(() => !!sessions.currentId && !!text.value.trim())
const placeholder = computed(() =>
  !sessions.currentId ? '开始新对话…' : '输入消息…',
)

function send() {
  const v = text.value.trim()
  if (!v || !sessions.currentId) return
  sessions.send(v)
  text.value = ''
  nextTick(() => inputRef.value?.focus())
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

defineExpose({
  async prefill(value: string) {
    if (!sessions.currentId) {
      await sessions.createSession()
    }
    text.value = value
    await nextTick()
    inputRef.value?.focus()
  },
})
</script>

<template>
  <div class="bg-background px-4 pb-6 pt-4">
    <div class="mx-auto flex max-w-3xl items-end gap-2 rounded-lg border border-border bg-card px-3 py-2 transition-colors focus-within:border-accent focus-within:ring-2 focus-within:ring-ring">
      <Textarea
        ref="inputRef"
        v-model="text"
        :placeholder="placeholder"
        :disabled="!sessions.currentId"
        :rows="1"
        class="min-h-[24px] flex-1 resize-none border-0 bg-transparent p-0 focus-visible:ring-0 focus-visible:ring-offset-0"
        @keydown="onKeydown"
      />
      <Button
        v-if="sessions.streaming"
        size="icon"
        variant="destructive"
        class="h-8 w-8 rounded-full"
        title="取消"
        @click="sessions.cancel()"
      >
        <Square class="h-3 w-3" fill="currentColor" />
      </Button>
      <Button
        v-else
        size="icon"
        :disabled="!canSend"
        class="h-8 w-8 rounded-full"
        title="发送"
        @click="send"
      >
        <Send class="h-4 w-4" :stroke-width="2" />
      </Button>
    </div>
  </div>
</template>