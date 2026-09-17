<script setup lang="ts">
import { onMounted, ref } from 'vue'
import MessageList from '@/components/chat/MessageList.vue'
import Composer from '@/components/chat/Composer.vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionsStore } from '@/stores/sessions'
import { useSkillsStore } from '@/stores/skills'
import { useMcpsStore } from '@/stores/mcps'

const auth = useAuthStore()
const sessions = useSessionsStore()
const skills = useSkillsStore()
const mcps = useMcpsStore()

const composerRef = ref<InstanceType<typeof Composer> | null>(null)

function onPrompt(p: string) {
  composerRef.value?.prefill(p)
}

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  await Promise.all([sessions.loadList(), skills.load(), mcps.load()])
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <MessageList class="flex-1" @use-prompt="onPrompt" />
    <Composer ref="composerRef" />
  </div>
</template>