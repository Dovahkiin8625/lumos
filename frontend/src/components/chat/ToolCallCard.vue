<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronRight, Copy, Check } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import type { ToolCall } from '@/types/domain'

const props = defineProps<{ call: ToolCall }>()

const open = ref(false)
const copied = ref(false)

const argsText = computed(() => JSON.stringify(props.call.arguments, null, 2))
const resultText = computed(() => props.call.result ?? '')

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    toast.error('复制失败')
  }
}
</script>

<template>
  <div class="my-2 overflow-hidden rounded-md border border-border bg-card">
    <button
      class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted/50"
      @click="open = !open"
    >
      <ChevronRight
        class="h-3.5 w-3.5 text-muted-foreground transition-transform"
        :class="{ 'rotate-90': open }"
      />
      <span class="font-mono text-xs text-foreground">{{ call.name }}</span>
      <span
        v-if="call.is_error"
        class="ml-auto rounded bg-destructive/10 px-1.5 py-0.5 text-xs text-destructive"
      >
        error
      </span>
    </button>
    <div v-if="open" class="border-t border-border bg-muted/30 px-3 py-2">
      <div class="mb-1 text-xs font-medium text-muted-foreground">Arguments</div>
      <div class="relative">
        <pre class="overflow-x-auto rounded bg-background p-2 text-xs font-mono text-foreground"><code>{{ argsText }}</code></pre>
        <Button
          variant="ghost"
          size="icon"
          class="absolute right-1 top-1 h-6 w-6"
          @click="copy(argsText)"
        >
          <Check v-if="copied" class="h-3 w-3" />
          <Copy v-else class="h-3 w-3" />
        </Button>
      </div>
      <div v-if="resultText" class="mt-3">
        <div class="mb-1 text-xs font-medium text-muted-foreground">Result</div>
        <div class="relative">
          <pre class="overflow-x-auto rounded bg-background p-2 text-xs font-mono text-foreground"><code>{{ resultText }}</code></pre>
          <Button
            variant="ghost"
            size="icon"
            class="absolute right-1 top-1 h-6 w-6"
            @click="copy(resultText)"
          >
            <Copy class="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>