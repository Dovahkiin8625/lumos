import { onBeforeUnmount, onMounted } from 'vue'

export function useShortcut(
  binding: { key: string; mod?: boolean; shift?: boolean; alt?: boolean },
  handler: (e: KeyboardEvent) => void,
) {
  function onKey(e: KeyboardEvent) {
    const matchesKey = e.key.toLowerCase() === binding.key.toLowerCase()
    const mod = binding.mod ? (e.metaKey || e.ctrlKey) : (!e.metaKey && !e.ctrlKey)
    const shift = binding.shift ? e.shiftKey : !e.shiftKey
    const alt = binding.alt ? e.altKey : !e.altKey
    if (matchesKey && mod && shift && alt) {
      e.preventDefault()
      handler(e)
    }
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
}