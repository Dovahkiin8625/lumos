import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useDark } from '@vueuse/core'
import router from './router'
import './style.css'
import App from './App.vue'

// Apply theme pre-mount to avoid FOUC
const isDark = useDark()
document.documentElement.classList.toggle('dark', isDark.value)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')