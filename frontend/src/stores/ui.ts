import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarOpen = ref(false)
  const settingsOpen = ref(false)

  function toggleSidebar() { sidebarOpen.value = !sidebarOpen.value }
  function openSidebar() { sidebarOpen.value = true }
  function closeSidebar() { sidebarOpen.value = false }
  function openSettings() { settingsOpen.value = true }
  function closeSettings() { settingsOpen.value = false }

  return {
    sidebarOpen,
    settingsOpen,
    toggleSidebar,
    openSidebar,
    closeSidebar,
    openSettings,
    closeSettings,
  }
})