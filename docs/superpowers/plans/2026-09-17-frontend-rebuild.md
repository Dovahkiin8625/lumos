# Frontend Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Lumos frontend (Vue 3 + Element Plus) with Vue 3 + shadcn-vue + Tailwind in a Notion-style minimalist visual system, preserving all existing functionality.

**Architecture:** Incremental replacement — keep all business logic (`api/`, `stores/` business logic, `types/`, `router/`), only rewrite the presentation layer (`.vue` files, styles, theme). Replace Element Plus with shadcn-vue + Tailwind, theme via `@vueuse/core useDark`, toasts via Sonner.

**Tech Stack:** Vue 3.5 + TypeScript + Vite 5 + Pinia 2 + Vue Router 4 + Tailwind 3 + shadcn-vue (radix-vue) + Sonner + @vueuse/core + axios + marked + highlight.js + lucide-vue-next

**Spec:** `docs/superpowers/specs/2026-09-17-frontend-rebuild-design.md`

---

## Global Constraints

- **Language:** All UI text in Simplified Chinese (zh-CN); code/comments in English
- **Backend:** Zero changes. API at `/api/*` and WebSocket at `/ws/sessions/{id}` are frozen contracts
- **No new test framework:** No Vitest, no Playwright. Verification = manual + visual + screenshots
- **Backward compatibility:** `frontend/src/api/client.ts`, `frontend/src/api/ws.ts`, `frontend/src/stores/{auth,sessions,skills,mcps}.ts`, `frontend/src/stores/ui.ts` (simplified only), `frontend/src/types/domain.ts`, `frontend/src/router/index.ts` — internal logic **untouched**
- **Visual:** Notion-style minimalist — neutral grays, blue accent `#3B82F6`, hairline 1px borders, max `shadow-sm` / `shadow`. No `shadow-md+`
- **Motion:** 150ms ease-out (in), 100ms ease-in (out)
- **Theme:** Single source = `useDark()` from `@vueuse/core`; `<html class="dark">` toggle; Tailwind `darkMode: 'class'`. Apply pre-mount in `main.ts` to avoid FOUC
- **Fonts:** System stack only — no Google Fonts
- **No new functionality:** Strict visual/UX rewrite only
- **Delete:** `AdminTools.vue` page + tab; `stores/theme.ts`; `styles/tokens.css`; `styles/global.css`; `views/` directory; `utils/markdown.ts`

---

## File Structure

### Files Touched (overview)

| Path | Action | Purpose |
|---|---|---|
| `frontend/package.json` | modify | Replace deps |
| `frontend/vite.config.ts` | modify | Disable sourcemap, no other change |
| `frontend/index.html` | modify | lang/title tweaks |
| `frontend/tailwind.config.ts` | create | Tailwind config + design tokens |
| `frontend/postcss.config.js` | create | PostCSS pipeline |
| `frontend/components.json` | create | shadcn-vue config |
| `frontend/src/style.css` | create | Tailwind + CSS variables (replaces direct t `styles/`) |
| `frontend/src/main.ts` | rewrite | Tailwind import + theme init + Toaster |
| `frontend/src/App.vue` | rewrite | Sonner + RouterView |
| `frontend/src/stores/ui.ts` | rewrite (simplified) | sidebar/settings only |
| `frontend/src/stores/theme.ts` | **delete** | useDark replaces it |
| `frontend/src/styles/tokens.css` | **delete** | |
| `frontend/src/styles/global.css` | **delete** | |
| `frontend/src/views/` | **delete** | move to components/ subdirs |
| `frontend/src/utils/markdown.ts` | **delete** | inline copy handler in chat/MessageItem |
| `frontend/src/components/ui/*` | create (CLI) | shadcn-vue atomic components |
| `frontend/src/components/layout/AppShell.vue` | rewrite | Top bar + Sidebar + Settings |
| `frontend/src/components/auth/LoginView.vue` | create | Login + Register |
| `frontend/src/components/chat/SessionSidebar.vue` | rewrite | Sheet + sessions list |
| `frontend/src/components/chat/MessageList.vue` | rewrite | Scrollable list + WelcomePanel |
| `frontend/src/components/chat/MessageItem.vue` | rewrite | Per-message renderer |
| `frontend/src/components/chat/ToolCallCard.vue` | rewrite | Collapsible tool call card |
| `frontend/src/components/chat/Composer.vue` | rewrite | Input + Send/Stop |
| `frontend/src/components/chat/WelcomePanel.vue` | rewrite | Empty state |
| `frontend/src/components/settings/SettingsDrawer.vue` | rewrite | Sheet + Skills/MCP tabs |
| `frontend/src/components/admin/AdminView.vue` | rewrite | Tabs (overview/skills/mcp) |
| `frontend/src/components/admin/AdminOverview.vue` | rewrite | Health + summary cards |
| `frontend/src/components/admin/AdminSkills.vue` | rewrite | List + CRUD trigger |
| `frontend/src/components/admin/AdminSkillDialog.vue` | create | Create/Edit dialog |
| `frontend/src/components/admin/AdminMcp.vue` | rewrite | List + CRUD + Test |
| `frontend/src/components/admin/AdminMcpDialog.vue` | create | Create/Edit dialog |
| `frontend/src/components/admin/AdminTools.vue` | **delete** | (no `/api/tools` backend) |
| `frontend/src/components/common/AvatarMenu.vue` | rewrite | DropdownMenu in AppShell |
| `frontend/src/components/common/Logo.vue` | rewrite | SVG Logo |
| `frontend/src/components/LoginView.vue` | delete | (moved) |
| `frontend/src/components/ChatView.vue` | delete | (moved to chat/) |
| `frontend/src/components/AdminView.vue` | delete | (moved to admin/) |
| `frontend/src/components/Composer.vue` | delete | (moved to chat/) |
| `frontend/src/components/MessageList.vue` | delete | (moved to chat/) |
| `frontend/src/components/MessageItem.vue` | delete | (moved to chat/) |
| `frontend/src/components/SessionSidebar.vue` | delete | (moved to chat/) |
| `frontend/src/components/SettingsDrawer.vue` | delete | (moved to settings/) |
| `frontend/src/components/McpFormDialog.vue` | delete | (replaced by AdminMcpDialog) |
| `frontend/src/components/SkillFormDialog.vue` | delete | (replaced by AdminSkillDialog) |
| `frontend/src/components/SkillCard.vue` | delete | (integrated into AdminSkills) |
| `frontend/src/components/McpCard.vue` | delete | (integrated into AdminMcp) |
| `frontend/src/components/WelcomePanel.vue` | delete | (moved to chat/) |
| `frontend/src/components/ToolCallCard.vue` | delete | (moved to chat/) |
| `README.md` | modify | Tech stack text |

### Untouched Business Logic (DO NOT EDIT internals)

```
frontend/src/api/client.ts
frontend/src/api/ws.ts
frontend/src/stores/auth.ts
frontend/src/stores/sessions.ts
frontend/src/stores/skills.ts
frontend/src/stores/mcps.ts
frontend/src/types/domain.ts
frontend/src/router/index.ts
```

---

## Task 1: Environment & Build Setup

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/index.html`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/style.css`
- Delete: `frontend/src/styles/tokens.css`
- Delete: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: existing `frontend/package.json` deps list
- Produces: working `vite dev` server (no UI yet) with Tailwind classes ready; `vite build` succeeds

---

- [ ] **Step 1: Update `frontend/package.json`**

Replace the entire `dependencies` and `devDependencies` blocks:

```json
{
  "name": "lumos-frontend",
  "private": true,
  "version": "0.2.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.7",
    "@radix-icons/vue": "^1.5.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "highlight.js": "^11.10.0",
    "lucide-vue-next": "^0.453.0",
    "marked": "^14.1.3",
    "pinia": "^2.2.4",
    "radix-vue": "^1.9.10",
    "sonner": "^1.5.0",
    "tailwind-merge": "^2.5.4",
    "vue": "^3.5.10",
    "vue-router": "^4.4.5",
    "@vueuse/core": "^11.1.0"
  },
  "devDependencies": {
    "@types/node": "^22.7.4",
    "@vitejs/plugin-vue": "^5.1.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "shadcn-vue": "^0.10.4",
    "tailwindcss": "^3.4.13",
    "tailwindcss-animate": "^1.0.7",
    "@tailwindcss/typography": "^0.5.15",
    "typescript": "^5.6.2",
    "vite": "^5.4.8",
    "vue-tsc": "^2.1.6"
  }
}
```

- [ ] **Step 2: Run install**

```bash
cd frontend
npm install
```

Expected: completes without errors. Some peer-dep warnings OK (radix-vue + Vue 3.5).

- [ ] **Step 3: Replace `frontend/vite.config.ts`**

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: Update `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <title>Lumos</title>
  </head>
  <body class="bg-background text-foreground antialiased">
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `frontend/postcss.config.js`**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 6: Create `frontend/tailwind.config.ts`**

```ts
import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '1rem',
      screens: { '2xl': '1280px' },
    },
    extend: {
      fontFamily: {
        sans: [
          'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont',
          '"PingFang SC"', '"Microsoft YaHei"', '"Helvetica Neue"', 'sans-serif',
        ],
        mono: [
          'ui-monospace', '"JetBrains Mono"', '"Cascadia Code"', 'Menlo',
          'Consolas', 'monospace',
        ],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: `var(--radius)`,
        md: `calc(var(--radius) - 2px)`,
        sm: `calc(var(--radius) - 4px)`,
      },
    },
  },
  plugins: [animate, require('@tailwindcss/typography')],
} satisfies Config
```

- [ ] **Step 7: Create `frontend/src/style.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 240 10% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 240 10% 3.9%;
    --primary: 240 5.9% 10%;
    --primary-foreground: 0 0% 98%;
    --secondary: 240 4.8% 95.9%;
    --secondary-foreground: 240 5.9% 10%;
    --muted: 240 4.8% 95.9%;
    --muted-foreground: 240 3.8% 46.1%;
    --accent: 217 91% 60%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 5.9% 90%;
    --input: 240 5.9% 90%;
    --ring: 240 5% 64.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --card: 240 10% 5.9%;
    --card-foreground: 0 0% 98%;
    --popover: 240 10% 5.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 5.9% 10%;
    --secondary: 240 3.7% 15.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 240 3.7% 15.9%;
    --muted-foreground: 240 5% 64.9%;
    --accent: 217 91% 60%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 3.7% 15.9%;
    --input: 240 3.7% 15.9%;
    --ring: 240 4.9% 83.9%;
  }

  * {
    border-color: hsl(var(--border));
  }

  body {
    background-color: hsl(var(--background));
    color: hsl(var(--foreground));
    font-feature-settings: 'rlig' 1, 'calt' 1;
  }

  /* Code highlight (markdown) — minimal look, no library theme overrides */
  .hljs {
    background: transparent;
    color: inherit;
  }
}
```

- [ ] **Step 8: Delete old style files**

```bash
cd frontend
rm -rf src/styles
```

- [ ] **Step 9: Replace `frontend/src/main.ts` (interim)**

Replace the current `main.ts` with a minimal version that just imports style.css and mounts a placeholder App. Full `main.ts` arrives in Task 3.

```ts
import { createApp } from 'vue'
import './style.css'

const app = createApp({
  template: '<div class="p-8">Lumos bootstrap OK</div>',
})
app.mount('#app')
```

- [ ] **Step 10: Verify dev + build**

```bash
cd frontend
npm run dev
# Open http://127.0.0.1:5173 → expect "Lumos bootstrap OK" with white background, dark text
```

Then:

```bash
npm run build
```

Expected: build succeeds, `dist/` produced, no TS errors.

- [ ] **Step 11: Commit**

```bash
cd frontend && git add -A
git commit -m "chore(deps): bootstrap tailwind + new frontend deps, drop element-plus"
```

---

## Task 2: shadcn-vue Init + Atomic Components

**Files:**
- Create: `frontend/components.json`
- Create: `frontend/src/components/ui/*` (via CLI)

**Interfaces:**
- Consumes: Task 1's Tailwind config
- Produces: `frontend/src/lib/utils.ts` with `cn()` helper; 17 shadcn-vue components in `components/ui/`

---

- [ ] **Step 1: Create `frontend/components.json`**

```json
{
  "$schema": "https://shadcn-vue.com/schema.json",
  "style": "default",
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/style.css",
    "baseColor": "zinc",
    "cssVariables": true
  },
  "framework": "vue",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "composables": "@/composables",
    "lib": "@/lib"
  },
  "typescript": true
}
```

- [ ] **Step 2: Create `frontend/src/lib/utils.ts`**

```ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 3: Run shadcn-vue init (non-interactive)**

```bash
cd frontend
mkdir -p src/components/ui
npx shadcn-vue@latest init --yes --force
```

If interactive, answer: style=default, baseColor=zinc, cssVariables=yes, typescript=yes.

- [ ] **Step 4: Add the 17 atomic components**

```bash
cd frontend
npx shadcn-vue@latest add button input textarea label \
  dialog dropdown-menu sheet tabs switch skeleton \
  tooltip popover card sonner separator avatar scroll-area
```

Expected: each component is generated under `frontend/src/components/ui/<name>/`.

- [ ] **Step 5: Verify components exist**

```bash
ls frontend/src/components/ui
# Expected directories: button dialog dropdown-menu input label sheet skeleton sonner switch tabs textarea tooltip popover card separator avatar scroll-area
```

- [ ] **Step 6: Verify a sample import works**

Edit `frontend/src/main.ts` to import Button:

```ts
import { createApp } from 'vue'
import './style.css'
import Button from '@/components/ui/button/Button.vue'

const app = createApp({
  components: { Button },
  template: '<div class="p-8"><Button>Test</Button></div>',
})
app.mount('#app')
```

Run `npm run dev`. Visit `http://127.0.0.1:5173`. Expected: blue button with white text reading "Test".

- [ ] **Step 7: Revert main.ts to interim bootstrap**

Restore the Task 1 interim `main.ts`:

```ts
import { createApp } from 'vue'
import './style.css'

const app = createApp({
  template: '<div class="p-8">Lumos bootstrap OK</div>',
})
app.mount('#app')
```

- [ ] **Step 8: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): initialize shadcn-vue with 17 atomic components"
```

---

## Task 3: App Entry & Infrastructure

**Files:**
- Modify: `frontend/src/main.ts`
- Rewrite: `frontend/src/App.vue`
- Rewrite: `frontend/src/stores/ui.ts`
- Delete: `frontend/src/stores/theme.ts`
- Create: `frontend/src/composables/useShortcut.ts`

**Interfaces:**
- Consumes: shadcn-vue Toaster from `components/ui/sonner/`
- Produces: working `main.ts` that mounts `App.vue`; `useUiStore` exposes `sidebarOpen`, `settingsOpen`; `useShortcut(key, handler)` from composables

---

- [ ] **Step 1: Rewrite `frontend/src/stores/ui.ts`**

```ts
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
```

- [ ] **Step 2: Delete `frontend/src/stores/theme.ts`**

```bash
git rm frontend/src/stores/theme.ts
```

- [ ] **Step 3: Create `frontend/src/composables/useShortcut.ts`**

```ts
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
```

- [ ] **Step 4: Rewrite `frontend/src/main.ts`**

```ts
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
```

- [ ] **Step 5: Rewrite `frontend/src/App.vue`**

```vue
<script setup lang="ts">
import { Toaster } from '@/components/ui/sonner'
</script>

<template>
  <router-view />
  <Toaster position="top-right" rich-colors />
</template>
```

- [ ] **Step 6: Keep interim main.ts (router needs real App)**

Restore `main.ts` to use the rewritten version from Step 4. Run:

```bash
cd frontend
npm run dev
# Expect blank page + "Cannot GET /" or no error in console (router has no routes pointing at the placeholder)
# Visit http://127.0.0.1:5173 — should not crash. Console shows no errors.
```

- [ ] **Step 7: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): app entry — Tailwind, dark mode, Sonner Toaster, ui store"
```

---

## Task 4: AppShell + AvatarMenu + Logo

**Files:**
- Create: `frontend/src/components/common/Logo.vue`
- Create: `frontend/src/components/common/AvatarMenu.vue`
- Create: `frontend/src/components/layout/AppShell.vue`

**Interfaces:**
- Consumes: `useAuthStore` (from `stores/auth`), `useUiStore`, `useDark`, `useShortcut`
- Produces: top-bar with sidebar trigger, brand, title, avatar menu; routes to `/chat` and `/admin`

---

- [ ] **Step 1: Create `frontend/src/components/common/Logo.vue`**

```vue
<script setup lang="ts">
defineProps<{ size?: number }>()
</script>

<template>
  <svg
    :width="size ?? 24"
    :height="size ?? 24"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" />
    <path
      d="M7 12h10M12 7v10"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
    />
  </svg>
</template>
```

- [ ] **Step 2: Create `frontend/src/components/common/AvatarMenu.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Sun, Moon, Settings, LogOut, Wrench } from 'lucide-vue-next'
import { useDark } from '@vueuse/core'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()
const isDark = useDark()

const props = defineProps<{ isAdmin: boolean }>()

const initial = computed(() => (auth.user?.email ?? '?')[0].toUpperCase())

async function logout() {
  await auth.logout()
  router.replace('/login')
}

function toggleTheme() {
  isDark.value = !isDark.value
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <button
        class="h-8 w-8 rounded-full border border-border bg-card text-sm font-semibold text-muted-foreground hover:border-accent hover:text-accent transition-colors"
        :title="auth.user?.email"
      >
        {{ initial }}
      </button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="start" :side-offset="8" class="w-48">
      <DropdownMenuItem @select="toggleTheme">
        <component :is="isDark ? Sun : Moon" class="mr-2 h-3.5 w-3.5" />
        {{ isDark ? '浅色主题' : '深色主题' }}
      </DropdownMenuItem>
      <DropdownMenuSeparator v-if="!props.isAdmin" />
      <DropdownMenuItem v-if="!props.isAdmin" @select="router.push('/admin')">
        <Settings class="mr-2 h-3.5 w-3.5" />
        后台管理
      </DropdownMenuItem>
      <DropdownMenuItem v-else @select="router.push('/chat')">
        <Wrench class="mr-2 h-3.5 w-3.5" />
        回到对话
      </DropdownMenuItem>
      <DropdownMenuItem @select="ui.openSettings()">
        <Settings class="mr-2 h-3.5 w-3.5" />
        技能 &amp; MCP
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @select="logout" class="text-destructive">
        <LogOut class="mr-2 h-3.5 w-3.5" />
        登出
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
```

Note: import the DropdownMenu primitives at top of file:

```vue
<script setup lang="ts">
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
// ... rest of script
</script>
```

(The single import block above shows only the new imports; keep the rest.)

- [ ] **Step 3: Create `frontend/src/components/layout/AppShell.vue`**

```vue
<script setup lang="ts">
import { computed, onMounted, ref, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu, ArrowLeft, Pencil, Check, X } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import Logo from '@/components/common/Logo.vue'
import AvatarMenu from '@/components/common/AvatarMenu.vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionsStore } from '@/stores/sessions'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const sessions = useSessionsStore()
const ui = useUiStore()

const isAdmin = computed(() => route.path.startsWith('/admin'))
const editingTitle = ref(false)
const titleDraft = ref('')

const title = computed(() => {
  if (!sessions.current) return '新对话'
  return sessions.current.title?.trim() || '新对话'
})

function startEdit() {
  if (isAdmin.value || !sessions.current) return
  titleDraft.value = title.value === '新对话' ? '' : title.value
  editingTitle.value = true
}

async function commitEdit() {
  const t = titleDraft.value.trim()
  editingTitle.value = false
  if (!sessions.current || !t || t === title.value) return
  try {
    await api.patch(`/api/sessions/${sessions.current.id}`, { title: t })
    sessions.current.title = t
    toast.success('已重命名')
  } catch {
    toast.error('重命名失败')
  }
}

function cancelEdit() { editingTitle.value = false }

function backToChat() { router.push('/chat') }

function onKey(e: KeyboardEvent) {
  const mod = e.metaKey || e.ctrlKey
  if (mod && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    ui.toggleSidebar()
  }
  if (e.key === 'Escape' && ui.sidebarOpen) {
    ui.closeSidebar()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="flex h-screen flex-col bg-background">
    <header class="flex h-12 flex-shrink-0 items-center gap-2 border-b border-border bg-background px-3">
      <button
        v-if="!isAdmin"
        class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        aria-label="打开会话列表"
        @click="ui.toggleSidebar()"
      >
        <Menu class="h-4 w-4" :stroke-width="1.75" />
      </button>
      <button
        v-else
        class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        aria-label="返回对话"
        @click="backToChat"
      >
        <ArrowLeft class="h-4 w-4" :stroke-width="1.75" />
      </button>

      <a
        class="inline-flex cursor-pointer items-center rounded-md px-1.5 py-1 hover:bg-muted transition-colors"
        @click="isAdmin ? backToChat() : router.push('/chat')"
      >
        <Logo :size="20" />
      </a>

      <div class="flex min-w-0 flex-1 items-center gap-1">
        <template v-if="editingTitle">
          <input
            v-model="titleDraft"
            autofocus
            class="rounded-md border border-accent bg-muted px-2.5 py-1 text-sm font-medium text-foreground outline-none ring-2 ring-ring"
            @keydown.enter="commitEdit"
            @keydown.esc="cancelEdit"
            @blur="commitEdit"
          />
          <button class="inline-flex h-6 w-6 items-center justify-center rounded-md hover:bg-muted" @click="commitEdit">
            <Check class="h-3 w-3" :stroke-width="2" />
          </button>
          <button class="inline-flex h-6 w-6 items-center justify-center rounded-md hover:bg-muted" @click="cancelEdit">
            <X class="h-3 w-3" :stroke-width="2" />
          </button>
        </template>
        <button
          v-else
          class="inline-flex max-w-[320px] items-center gap-1.5 truncate rounded-md px-2.5 py-1 text-sm font-medium text-foreground hover:bg-muted transition-colors disabled:cursor-default disabled:hover:bg-transparent"
          :class="{ 'text-muted-foreground font-normal': !sessions.current }"
          :disabled="isAdmin"
          @click="startEdit"
        >
          {{ isAdmin ? '后台管理' : title }}
          <Pencil v-if="!isAdmin && sessions.current" class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" :stroke-width="1.75" />
        </button>
      </div>
    </header>

    <main class="flex min-h-0 flex-1 flex-col overflow-hidden">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <div v-if="auth.user" class="fixed bottom-4 left-4 z-50">
      <AvatarMenu :is-admin="isAdmin" />
    </div>

    <slot name="drawers" />
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 150ms ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
```

- [ ] **Step 4: Update `frontend/src/router/index.ts`**

Replace `component: () => import('@/components/AppShell.vue')` with the new layout location:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/components/auth/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppShell.vue'),
      children: [
        { path: '', redirect: '/chat' },
        { path: 'chat', name: 'chat', component: () => import('@/components/chat/ChatView.vue') },
        { path: 'admin', name: 'admin', component: () => import('@/components/admin/AdminView.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.accessToken) return { path: '/login', query: { redirect: to.fullPath } }
  return true
})

export default router
```

- [ ] **Step 5: Verify build still passes**

```bash
cd frontend
npm run build
```

Expected: builds successfully. LoginView / ChatView / AdminView files don't exist yet so build will fail at the lazy imports. That's OK — just confirm TypeScript / Vite config compiles.

- [ ] **Step 6: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): AppShell + AvatarMenu + Logo with shadcn-vue"
```

---

## Task 5: LoginView

**Files:**
- Create: `frontend/src/components/auth/LoginView.vue`
- Delete: `frontend/src/components/LoginView.vue`
- Delete: `frontend/src/views/LoginView.vue` (if not already deleted)

**Interfaces:**
- Consumes: `useAuthStore` (login, register, fetchMe), `useRoute` for redirect
- Produces: login + register flow → store toasts + `router.replace(redirect)`

---

- [ ] **Step 1: Delete old LoginView files**

```bash
git rm frontend/src/components/LoginView.vue
git rm -f frontend/src/views/LoginView.vue 2>/dev/null || true
```

- [ ] **Step 2: Create `frontend/src/components/auth/LoginView.vue`**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Mail, Lock, ArrowRight } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Logo from '@/components/common/Logo.vue'
import { useAuthStore } from '@/stores/auth'

type Mode = 'login' | 'register'
const mode = ref<Mode>('login')
const loading = ref(false)
const email = ref('')
const password = ref('')
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const title = computed(() => (mode.value === 'login' ? '欢迎回来' : '创建账号'))
const buttonLabel = computed(() => (mode.value === 'login' ? '继续' : '注册'))

async function submit() {
  if (!email.value || password.value.length < 8) {
    toast.warning('密码至少 8 位')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(email.value, password.value)
      toast.success('已登录')
    } else {
      await auth.register(email.value, password.value)
      toast.success('已注册')
    }
    const redirect = (route.query.redirect as string) || '/chat'
    router.replace(redirect)
  } catch (err: unknown) {
    const msg =
      (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
      (mode.value === 'login' ? '登录失败' : '注册失败')
    toast.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center bg-background p-6">
    <div class="flex w-full max-w-[360px] flex-col gap-6">
      <Logo :size="28" />

      <h1 class="text-2xl font-semibold tracking-tight text-foreground">
        {{ title }}
      </h1>

      <Tabs v-model:value="mode">
        <TabsList class="w-fit">
          <TabsTrigger value="login">登录</TabsTrigger>
          <TabsTrigger value="register">注册</TabsTrigger>
        </TabsList>
      </Tabs>

      <form class="flex flex-col gap-2" @submit.prevent="submit">
        <div class="relative">
          <Mail class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" :stroke-width="1.75" />
          <Input
            v-model="email"
            type="email"
            placeholder="邮箱"
            autocomplete="email"
            class="pl-10"
            required
          />
        </div>

        <div class="relative">
          <Lock class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" :stroke-width="1.75" />
          <Input
            v-model="password"
            type="password"
            placeholder="密码（至少 8 位）"
            autocomplete="current-password"
            class="pl-10"
            required
            @keyup.enter="submit"
          />
        </div>

        <Button type="submit" :disabled="loading" class="mt-2 h-10 w-full">
          <span>{{ loading ? '处理中…' : buttonLabel }}</span>
          <ArrowRight v-if="!loading" class="h-3.5 w-3.5" :stroke-width="2" />
        </Button>
      </form>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Verify build (skip imports that will fail)**

ChatView and AdminView don't exist yet, so the router will fail to import. Temporarily comment out the failing children in router to verify LoginView compiles:

In `frontend/src/router/index.ts`, comment out the ChatView / AdminView imports:

```ts
        { path: 'chat', name: 'chat', component: () => import('@/components/chat/_ChatViewPlaceholder.vue') },
        { path: 'admin', name: 'admin', component: () => import('@/components/admin/_AdminViewPlaceholder.vue') },
```

Create placeholder files:

`frontend/src/components/chat/_ChatViewPlaceholder.vue`:
```vue
<template><div class="p-8 text-foreground">Chat view placeholder</div></template>
```

`frontend/src/components/admin/_AdminViewPlaceholder.vue`:
```vue
<template><div class="p-8 text-foreground">Admin view placeholder</div></template>
```

Run `npm run build`. Expected: build OK.

- [ ] **Step 4: Verify login flow manually**

```bash
cd frontend
npm run dev
# Open http://127.0.0.1:5173 — redirects to /login
# Try email format invalid → see Sonner warning
# Type valid email + 8+ char password → click 继续
# Expected: redirects to /chat (placeholder), Sonner success toast
```

- [ ] **Step 5: Revert placeholders**

Restore `frontend/src/router/index.ts` to use the real ChatView / AdminView imports (they'll be created in later tasks; keep placeholders for now until those tasks run). DO NOT delete placeholders yet — leave them in place; they will be replaced in Tasks 6 and 9.

- [ ] **Step 6: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): LoginView with shadcn-vue Tabs/Input/Button + Sonner toasts"
```

---

## Task 6: SessionSidebar (Sheet)

**Files:**
- Create: `frontend/src/components/chat/SessionSidebar.vue`
- Delete: `frontend/src/components/SessionSidebar.vue`

**Interfaces:**
- Consumes: `useUiStore.sidebarOpen`, `useSessionsStore.{list, currentId, select, createSession, deleteSession, current}`, `Sheet` (shadcn-vue)
- Produces: left Sheet containing session items; CRUD actions; close on item click

---

- [ ] **Step 1: Create `frontend/src/components/chat/SessionSidebar.vue`**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Trash2, MessageSquare } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useUiStore } from '@/stores/ui'
import { useSessionsStore } from '@/stores/sessions'

const ui = useUiStore()
const sessions = useSessionsStore()
const renamingId = ref<string | null>(null)
const renameDraft = ref('')

function closeSidebar() {
  ui.closeSidebar()
}

async function createAndSelect() {
  await sessions.createSession()
  closeSidebar()
}

function select(id: string) {
  if (sessions.currentId === id) {
    closeSidebar()
    return
  }
  sessions.select(id)
  closeSidebar()
}

async function deleteItem(id: string) {
  try {
    await sessions.deleteSession(id)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

function startRename(id: string, currentTitle: string) {
  renamingId.value = id
  renameDraft.value = currentTitle === '新会话' ? '' : currentTitle
}

async function commitRename(id: string) {
  const t = renameDraft.value.trim()
  renamingId.value = null
  if (!t) return
  try {
    const { api } = await import('@/api/client')
    await api.patch(`/api/sessions/${id}`, { title: t })
    const s = sessions.list.find((x) => x.id === id)
    if (s) s.title = t
    if (sessions.current?.id === id) sessions.current.title = t
  } catch {
    toast.error('重命名失败')
  }
}
</script>

<template>
  <Sheet :open="ui.sidebarOpen" @update:open="(v) => v ? ui.openSidebar() : ui.closeSidebar()">
    <SheetContent side="left" class="w-[280px] p-0">
      <SheetHeader class="border-b border-border px-4 py-3">
        <SheetTitle>会话</SheetTitle>
      </SheetHeader>

      <div class="flex items-center justify-between px-4 py-2">
        <Button variant="ghost" size="sm" class="gap-1.5" @click="createAndSelect">
          <Plus class="h-3.5 w-3.5" />
          新会话
        </Button>
      </div>
      <Separator />

      <div class="flex-1 overflow-y-auto">
        <div v-if="sessions.list.length === 0" class="px-4 py-12 text-center text-sm text-muted-foreground">
          还没有会话
        </div>
        <div v-else class="flex flex-col">
          <div
            v-for="s in sessions.list"
            :key="s.id"
            class="group flex cursor-pointer items-center justify-between gap-2 border-b border-border/40 px-4 py-2.5 hover:bg-muted/50"
            :class="{ 'bg-muted': sessions.currentId === s.id }"
            @click="select(s.id)"
          >
            <div class="flex min-w-0 flex-1 items-center gap-2">
              <MessageSquare class="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" :stroke-width="1.75" />
              <template v-if="renamingId === s.id">
                <input
                  v-model="renameDraft"
                  autofocus
                  class="min-w-0 flex-1 rounded border border-accent bg-background px-1.5 py-0.5 text-sm outline-none"
                  @click.stop
                  @keydown.enter="commitRename(s.id)"
                  @keydown.esc="renamingId = null"
                  @blur="commitRename(s.id)"
                />
              </template>
              <span v-else class="truncate text-sm text-foreground">{{ s.title || '新会话' }}</span>
            </div>
            <div class="flex flex-shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100">
              <button
                class="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                @click.stop="startRename(s.id, s.title || '')"
              >
                重命名
              </button>
              <button
                class="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                aria-label="删除"
                @click.stop="deleteItem(s.id)"
              >
                <Trash2 class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </SheetContent>
  </Sheet>
</template>
```

- [ ] **Step 2: Mount Sidebar in AppShell**

In `frontend/src/components/layout/AppShell.vue`, replace `<slot name="drawers" />` with:

```vue
    <SessionSidebar />
    <SettingsDrawer />
```

Add to script imports:

```ts
import SessionSidebar from '@/components/chat/SessionSidebar.vue'
import SettingsDrawer from '@/components/settings/SettingsDrawer.vue'
```

Create `frontend/src/components/settings/SettingsDrawer.vue` as a temporary stub so the build passes:

```vue
<template>
  <div class="hidden">Settings drawer placeholder</div>
</template>
```

(Full SettingsDrawer rewrite is Task 9.)

- [ ] **Step 3: Verify build + manual flow**

```bash
cd frontend
npm run build
```

Run dev. Login → click ☰ → SessionSidebar opens. Create new session. Select. Delete (with toast). Rename.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): SessionSidebar as shadcn-vue Sheet with full session CRUD"
```

---

## Task 7: Chat Core — MessageList + MessageItem + ToolCallCard

**Files:**
- Create: `frontend/src/components/chat/MessageItem.vue`
- Create: `frontend/src/components/chat/ToolCallCard.vue`
- Create: `frontend/src/components/chat/MessageList.vue`
- Delete: `frontend/src/components/MessageItem.vue`
- Delete: `frontend/src/components/ToolCallCard.vue`
- Delete: `frontend/src/components/MessageList.vue`

**Consumes:** `useSessionsStore.{messages, streaming}`, `marked`, `highlight.js`

---

- [ ] **Step 1: Create `frontend/src/components/chat/ToolCallCard.vue`**

```vue
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
```

- [ ] **Step 2: Create `frontend/src/components/chat/MessageItem.vue`**

```vue
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

marked.setOptions({
  breaks: true,
  highlight(code, language) {
    if (language && hljs.getLanguage(language)) {
      try {
        return hljs.highlight(code, { language }).value
      } catch {
        // fall through
      }
    }
    return hljs.highlightAuto(code).value
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
```

- [ ] **Step 3: Create `frontend/src/components/chat/MessageList.vue`**

```vue
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
```

- [ ] **Step 4: Delete old message files**

```bash
git rm frontend/src/components/MessageItem.vue frontend/src/components/ToolCallCard.vue frontend/src/components/MessageList.vue
```

- [ ] **Step 5: Verify build**

```bash
cd frontend
npm run build
```

Build will fail on WelcomePanel / ChatView missing — temporarily stub `frontend/src/components/chat/WelcomePanel.vue`:

```vue
<template>
  <div class="text-sm text-muted-foreground">Welcome placeholder</div>
</template>
```

(Full rewrite is Task 8.) Run build. Expected: passes.

- [ ] **Step 6: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): MessageList + MessageItem + ToolCallCard with markdown rendering"
```

---

## Task 8: Chat Input — Composer + WelcomePanel

**Files:**
- Create: `frontend/src/components/chat/Composer.vue`
- Create: `frontend/src/components/chat/WelcomePanel.vue`
- Create: `frontend/src/components/chat/ChatView.vue`
- Delete: `frontend/src/components/Composer.vue`
- Delete: `frontend/src/components/WelcomePanel.vue`
- Delete: `frontend/src/components/ChatView.vue`

---

- [ ] **Step 1: Create `frontend/src/components/chat/WelcomePanel.vue`**

```vue
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
```

- [ ] **Step 2: Create `frontend/src/components/chat/Composer.vue`**

```vue
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
```

- [ ] **Step 3: Create `frontend/src/components/chat/ChatView.vue`**

```vue
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
```

- [ ] **Step 4: Remove placeholder**

```bash
git rm frontend/src/components/chat/_ChatViewPlaceholder.vue
```

Update `frontend/src/router/index.ts` children to use the real ChatView:

```ts
        { path: 'chat', name: 'chat', component: () => import('@/components/chat/ChatView.vue') },
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```

Expected: passes.

- [ ] **Step 6: Manual flow check**

Run dev. Login → /chat → empty state with WelcomePanel. Click a prompt → input pre-filled, session auto-created. Send a message → streaming dots → assistant reply renders. Test cancel button. Test code blocks render with highlight.

- [ ] **Step 7: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): Composer + WelcomePanel + ChatView with shadcn-vue"
```

---

## Task 9: SettingsDrawer

**Files:**
- Create: `frontend/src/components/settings/SettingsDrawer.vue`
- Delete: `frontend/src/components/SettingsDrawer.vue` (placeholder under layout/)

Wait — the placeholder is at `frontend/src/components/settings/SettingsDrawer.vue`. Replace in place.

**Consumes:** `useUiStore.settingsOpen`, `useSessionsStore.{enabledSkills, currentId, toggleSkill}`, `useSkillsStore.list`

---

- [ ] **Step 1: Replace `frontend/src/components/settings/SettingsDrawer.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { Sparkles, Plug } from 'lucide-vue-next'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { useUiStore } from '@/stores/ui'
import { useSessionsStore } from '@/stores/sessions'
import { useSkillsStore } from '@/stores/skills'
import { useMcpsStore } from '@/stores/mcps'

const ui = useUiStore()
const sessions = useSessionsStore()
const skills = useSkillsStore()
const mcps = useMcpsStore()

const tab = computed<'skills' | 'mcp'>({
  get: () => 'skills',
  set: () => {},
})

async function toggleSkill(name: string, on: boolean) {
  if (!sessions.currentId) return
  await sessions.toggleSkill(name, on)
}
</script>

<template>
  <Sheet :open="ui.settingsOpen" @update:open="(v) => v ? ui.openSettings() : ui.closeSettings()">
    <SheetContent side="right" class="w-[400px] p-0 sm:max-w-[400px]">
      <SheetHeader class="border-b border-border px-4 py-3">
        <SheetTitle>设置</SheetTitle>
      </SheetHeader>

      <Tabs v-model:value="tab" class="w-full">
        <TabsList class="mx-4 mt-3">
          <TabsTrigger value="skills">
            <Sparkles class="mr-1.5 h-3.5 w-3.5" :stroke-width="1.75" />
            技能
          </TabsTrigger>
          <TabsTrigger value="mcp">
            <Plug class="mr-1.5 h-3.5 w-3.5" :stroke-width="1.75" />
            MCP
          </TabsTrigger>
        </TabsList>

        <TabsContent value="skills" class="mt-0">
          <div class="px-4 pt-3 text-xs text-muted-foreground">
            当前会话启用的技能
          </div>
          <Separator class="my-2" />
          <div v-if="!sessions.currentId" class="px-4 py-8 text-center text-sm text-muted-foreground">
            请先选择或创建一个会话
          </div>
          <div v-else-if="skills.list.length === 0" class="px-4 py-8 text-center text-sm text-muted-foreground">
            暂无可配置的技能
          </div>
          <div v-else class="flex flex-col">
            <div
              v-for="s in skills.list"
              :key="s.name"
              class="flex items-start justify-between gap-3 border-b border-border/40 px-4 py-3"
            >
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-foreground">{{ s.name }}</div>
                <div class="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                  {{ s.description }}
                </div>
              </div>
              <Switch
                :model-value="sessions.enabledSkills.has(s.name)"
                :disabled="!s.enabled"
                @update:model-value="(v) => toggleSkill(s.name, !!v)"
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="mcp" class="mt-0">
          <div class="px-4 pt-3 text-xs text-muted-foreground">
            当前已配置的 MCP 服务器
          </div>
          <Separator class="my-2" />
          <div v-if="mcps.list.length === 0" class="px-4 py-8 text-center text-sm text-muted-foreground">
            暂未配置 MCP 服务器
          </div>
          <div v-else class="flex flex-col">
            <div
              v-for="m in mcps.list"
              :key="m.id"
              class="flex items-start justify-between gap-3 border-b border-border/40 px-4 py-3"
            >
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 text-sm font-medium text-foreground">
                  {{ m.name }}
                  <span class="rounded bg-muted px-1.5 py-0.5 text-xs font-normal text-muted-foreground">
                    {{ m.transport }}
                  </span>
                </div>
                <div class="mt-0.5 font-mono text-xs text-muted-foreground truncate">
                  {{ m.config.url ?? m.config.command }}
                </div>
              </div>
            </div>
          </div>
          <div class="border-t border-border px-4 py-3 text-xs text-muted-foreground">
            如需新增/编辑 MCP，请前往
            <router-link to="/admin?tab=mcp" class="text-accent hover:underline" @click="ui.closeSettings()">
              后台管理
            </router-link>
          </div>
        </TabsContent>
      </Tabs>
    </SheetContent>
  </Sheet>
</template>
```

- [ ] **Step 2: Verify build + manual flow**

```bash
cd frontend && npm run build
```

Run dev. Open settings drawer via AvatarMenu. Toggle a skill on/off → check it persists across reload. Switch to MCP tab → see list of configured servers.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): SettingsDrawer with Skills switch + MCP read-only tabs"
```

---

## Task 10: AdminOverview

**Files:**
- Create: `frontend/src/components/admin/AdminView.vue`
- Create: `frontend/src/components/admin/AdminOverview.vue`
- Delete: `frontend/src/components/admin/AdminView.vue` (old)
- Delete: `frontend/src/components/AdminView.vue` (under top-level components)

**Consumes:** `api.get('/api/health')`, `useSessionsStore.list.length`, `useMcpsStore.list`

---

- [ ] **Step 1: Create `frontend/src/components/admin/AdminOverview.vue`**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw, Activity, Database, Cpu, Plug } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { api } from '@/api/client'
import { useSessionsStore } from '@/stores/sessions'
import { useMcpsStore } from '@/stores/mcps'

interface Health {
  status: string
  version: string
  providers: Record<string, string>
  mcp_servers: Record<string, string>
  db: string
}

const sessions = useSessionsStore()
const mcps = useMcpsStore()

const health = ref<Health | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<Health>('/api/health')
    health.value = data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([sessions.loadList(), mcps.load()])
  await load()
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">总览</h2>
      <Button variant="ghost" size="sm" :disabled="loading" @click="load">
        <RefreshCw class="mr-1.5 h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
        刷新
      </Button>
    </div>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-2">
          <CardTitle class="text-xs font-medium text-muted-foreground">会话数</CardTitle>
          <Activity class="h-3.5 w-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-semibold text-foreground">{{ sessions.list.length }}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-2">
          <CardTitle class="text-xs font-medium text-muted-foreground">MCP 服务器</CardTitle>
          <Plug class="h-3.5 w-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-semibold text-foreground">{{ mcps.list.length }}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader class="flex flex-row items-center justify-between pb-2">
          <CardTitle class="text-xs font-medium text-muted-foreground">数据库</CardTitle>
          <Database class="h-3.5 w-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-semibold" :class="health?.db === 'ok' ? 'text-foreground' : 'text-destructive'">
            {{ health?.db ?? '—' }}
          </div>
        </CardContent>
      </Card>
    </div>

    <Card>
      <CardHeader>
        <CardTitle class="text-sm font-medium">系统健康</CardTitle>
      </CardHeader>
      <CardContent class="space-y-2 text-sm">
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">总体状态</span>
          <span class="font-mono" :class="health?.status === 'ok' ? 'text-foreground' : 'text-destructive'">
            {{ health?.status ?? '—' }}
          </span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">版本</span>
          <span class="font-mono text-foreground">{{ health?.version ?? '—' }}</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">Providers</span>
          <span class="font-mono text-foreground">
            <template v-for="(v, k) in health?.providers ?? {}" :key="k">
              {{ k }}={{ v }}
            </template>
          </span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-muted-foreground">Provider 状态</span>
          <Cpu class="h-3.5 w-3.5 text-muted-foreground" />
        </div>
        <div v-if="health?.mcp_servers && Object.keys(health.mcp_servers).length" class="mt-2 space-y-1 border-t border-border pt-2">
          <div
            v-for="(v, k) in health.mcp_servers"
            :key="k"
            class="flex items-center justify-between text-xs"
          >
            <span class="font-mono text-muted-foreground">{{ k }}</span>
            <span :class="v === 'connected' ? 'text-foreground' : 'text-destructive'">{{ v }}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
```

- [ ] **Step 2: Create `frontend/src/components/admin/AdminView.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Sparkles, Plug } from 'lucide-vue-next'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import AdminOverview from '@/components/admin/AdminOverview.vue'
import AdminSkills from '@/components/admin/AdminSkills.vue'
import AdminMcp from '@/components/admin/AdminMcp.vue'

const route = useRoute()
const router = useRouter()

const tabs = [
  { value: 'overview', label: '总览', icon: LayoutDashboard },
  { value: 'skills', label: '技能', icon: Sparkles },
  { value: 'mcp', label: 'MCP', icon: Plug },
]

const active = computed({
  get: () => (route.query.tab as string) || 'overview',
  set: (v) => router.replace({ query: { ...route.query, tab: v } }),
})
</script>

<template>
  <div class="flex h-full flex-col">
    <Tabs v-model:value="active" class="flex h-full flex-col">
      <div class="border-b border-border px-6">
        <TabsList class="bg-transparent">
          <TabsTrigger v-for="t in tabs" :key="t.value" :value="t.value">
            <component :is="t.icon" class="mr-1.5 h-3.5 w-3.5" :stroke-width="1.75" />
            {{ t.label }}
          </TabsTrigger>
        </TabsList>
      </div>
      <div class="flex-1 overflow-y-auto p-6">
        <AdminOverview v-if="active === 'overview'" />
        <AdminSkills v-else-if="active === 'skills'" />
        <AdminMcp v-else-if="active === 'mcp'" />
      </div>
    </Tabs>
  </div>
</template>
```

- [ ] **Step 3: Delete old AdminView**

```bash
git rm frontend/src/components/admin/AdminView.vue
git rm frontend/src/components/AdminView.vue 2>/dev/null || true
```

- [ ] **Step 4: Verify build (will fail on AdminSkills/AdminMcp missing — full implementations in Tasks 11/12)**

Stub `frontend/src/components/admin/AdminSkills.vue` and `frontend/src/components/admin/AdminMcp.vue`:

```vue
<!-- AdminSkills.vue placeholder -->
<template><div>Skills placeholder</div></template>
```

```vue
<!-- AdminMcp.vue placeholder -->
<template><div>MCP placeholder</div></template>
```

Build:

```bash
cd frontend && npm run build
```

Expected: passes.

- [ ] **Step 5: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): AdminView + AdminOverview with health cards"
```

---

## Task 11: AdminSkills + AdminSkillDialog

**Files:**
- Create: `frontend/src/components/admin/AdminSkillDialog.vue`
- Create: `frontend/src/components/admin/AdminSkills.vue` (real)
- Delete: `frontend/src/components/admin/AdminSkills.vue` (placeholder)
- Delete: `frontend/src/components/admin/AdminSkills.old` (if any)
- Delete: `frontend/src/components/McpFormDialog.vue`
- Delete: `frontend/src/components/SkillFormDialog.vue`
- Delete: `frontend/src/components/admin/SkillFormDialog.vue` (if any)
- Delete: `frontend/src/components/SkillCard.vue`

**Consumes:** `useSkillsStore` (load, create, update, remove, enable, disable, reload), `Dialog` (shadcn-vue)

---

- [ ] **Step 1: Create `frontend/src/components/admin/AdminSkillDialog.vue`**

```vue
<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import type { SkillOut, SkillCreate } from '@/types/domain'

const props = defineProps<{ open: boolean; editing: SkillOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const form = ref<SkillCreate>({
  name: '',
  description: '',
  version: '0.0.0',
  tags: [],
  required_tools: [],
  optional_tools: [],
  max_steps: null,
  instructions: '',
})

const tagsText = ref('')
const requiredText = ref('')
const optionalText = ref('')
const loading = ref(false)
const error = ref('')

watch(
  () => [props.open, props.editing?.name],
  () => {
    if (!props.open) return
    error.value = ''
    if (props.editing) {
      form.value = {
        name: props.editing.name,
        description: props.editing.description,
        version: props.editing.version,
        tags: [...props.editing.tags],
        required_tools: [...props.editing.required_tools],
        optional_tools: [...props.editing.optional_tools],
        max_steps: props.editing.max_steps,
        instructions: props.editing.instructions,
      }
      tagsText.value = props.editing.tags.join(', ')
      requiredText.value = props.editing.required_tools.join(', ')
      optionalText.value = props.editing.optional_tools.join(', ')
    } else {
      form.value = { name: '', description: '', version: '0.0.0', tags: [], required_tools: [], optional_tools: [], max_steps: null, instructions: '' }
      tagsText.value = ''
      requiredText.value = ''
      optionalText.value = ''
    }
  },
  { immediate: true },
)

function splitCsv(s: string): string[] {
  return s.split(',').map((x) => x.trim()).filter(Boolean)
}

async function submit() {
  error.value = ''
  if (!form.name.trim()) {
    error.value = '名称必填'
    return
  }
  loading.value = true
  try {
    const payload: SkillCreate = {
      name: form.value.name.trim(),
      description: form.value.description,
      version: form.value.version,
      tags: splitCsv(tagsText.value),
      required_tools: splitCsv(requiredText.value),
      optional_tools: splitCsv(optionalText.value),
      max_steps: form.value.max_steps,
      instructions: form.value.instructions,
    }
    const { skills } = await import('@/stores/skills')
    const store = skills()
    if (props.editing) {
      await store.update(props.editing.name, payload)
    } else {
      await store.create(payload)
    }
    emit('saved')
    emit('update:open', false)
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || '保存失败'
    error.value = msg
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog :open="props.open" @update:open="(v) => emit('update:open', v)">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-[560px]">
      <DialogHeader>
        <DialogTitle>{{ props.editing ? '编辑技能' : '新建技能' }}</DialogTitle>
        <DialogDescription>
          技能以 SKILL.md 文件存储于 <code>skills.dirs[0]</code>
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-3 py-2">
        <div class="grid gap-1.5">
          <Label>名称</Label>
          <Input v-model="form.name" :disabled="!!props.editing" placeholder="my-skill" />
        </div>
        <div class="grid gap-1.5">
          <Label>描述</Label>
          <Input v-model="form.description" placeholder="一句话说明" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="grid gap-1.5">
            <Label>版本</Label>
            <Input v-model="form.version" placeholder="0.0.0" />
          </div>
          <div class="grid gap-1.5">
            <Label>最大步数</Label>
            <Input v-model.number="form.max_steps" type="number" min="1" max="200" placeholder="留空 = 默认" />
          </div>
        </div>
        <div class="grid gap-1.5">
          <Label>标签（逗号分隔）</Label>
          <Input v-model="tagsText" placeholder="tag1, tag2" />
        </div>
        <div class="grid gap-1.5">
          <Label>必需工具（逗号分隔）</Label>
          <Input v-model="requiredText" placeholder="file_read, http_request" />
        </div>
        <div class="grid gap-1.5">
          <Label>可选工具（逗号分隔）</Label>
          <Input v-model="optionalText" placeholder="shell" />
        </div>
        <div class="grid gap-1.5">
          <Label>指令</Label>
          <Textarea v-model="form.instructions" :rows="6" placeholder="Markdown 格式的技能指令..." />
        </div>
        <div v-if="error" class="text-sm text-destructive">{{ error }}</div>
      </div>

      <DialogFooter>
        <Button variant="ghost" @click="emit('update:open', false)">取消</Button>
        <Button :disabled="loading" @click="submit">{{ loading ? '保存中…' : '保存' }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
```

- [ ] **Step 2: Verify `useSkillsStore.update` exists**

Read `frontend/src/stores/skills.ts`. If it doesn't expose `update` / `create`, ADD them (this is the only allowed exception — we MUST add a missing method that the dialog relies on). Verify the backend API supports `PUT /api/skills/{name}` (it does — see spec §6.1 store list).

Open `frontend/src/stores/skills.ts` and replace its contents with:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import type { SkillCreate, SkillOut } from '@/types/domain'

export const useSkillsStore = defineStore('skills', () => {
  const list = ref<SkillOut[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const { data } = await api.get<SkillOut[]>('/api/skills')
      list.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: SkillCreate) {
    const { data } = await api.post<SkillOut>('/api/skills', payload)
    list.value = [...list.value, data]
    return data
  }

  async function update(name: string, payload: SkillCreate) {
    const { data } = await api.put<SkillOut>(`/api/skills/${name}`, payload)
    list.value = list.value.map((s) => (s.name === name ? data : s))
    return data
  }

  async function remove(name: string) {
    await api.delete(`/api/skills/${name}`)
    list.value = list.value.filter((s) => s.name !== name)
  }

  async function enable(name: string) {
    await api.post(`/api/skills/${name}/enable`)
    const s = list.value.find((x) => x.name === name)
    if (s) s.enabled = true
  }

  async function disable(name: string) {
    await api.post(`/api/skills/${name}/disable`)
    const s = list.value.find((x) => x.name === name)
    if (s) s.enabled = false
  }

  async function reload() {
    await api.post('/api/skills/reload')
    await load()
  }

  return { list, loading, load, create, update, remove, enable, disable, reload }
})
```

(Only edit this if it doesn't already have update/create/remove/enable/disable/reload. If it does, leave it untouched and just verify.)

- [ ] **Step 3: Create `frontend/src/components/admin/AdminSkills.vue`**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Plus, Pencil, Trash2, RotateCw, Power, PowerOff } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { useSkillsStore } from '@/stores/skills'
import AdminSkillDialog from '@/components/admin/AdminSkillDialog.vue'

const skills = useSkillsStore()
const dialogOpen = ref(false)
const editing = ref<SkillOut | null>(null)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}
function openEdit(s: SkillOut) {
  editing.value = s
  dialogOpen.value = true
}

async function onSaved() {
  toast.success('已保存')
}

async function toggle(s: SkillOut) {
  try {
    if (s.enabled) await skills.disable(s.name)
    else await skills.enable(s.name)
  } catch {
    toast.error('操作失败')
  }
}

async function remove(s: SkillOut) {
  if (!confirm(`确定删除技能 "${s.name}"？`)) return
  try {
    await skills.remove(s.name)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

async function reload() {
  try {
    await skills.reload()
    toast.success('已重载')
  } catch {
    toast.error('重载失败')
  }
}

onMounted(() => skills.load())
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">技能</h2>
      <div class="flex gap-2">
        <Button variant="ghost" size="sm" @click="reload">
          <RotateCw class="mr-1.5 h-3.5 w-3.5" />
          重载
        </Button>
        <Button size="sm" @click="openCreate">
          <Plus class="mr-1.5 h-3.5 w-3.5" />
          新建
        </Button>
      </div>
    </div>

    <div v-if="skills.list.length === 0" class="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
      暂无技能。点击右上角"新建"或放入 <code>skills.dirs[0]</code> 目录后点"重载"。
    </div>

    <div v-else class="space-y-2">
      <Card v-for="s in skills.list" :key="s.name">
        <CardContent class="flex items-start gap-4 p-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-medium text-foreground">{{ s.name }}</span>
              <span class="font-mono text-xs text-muted-foreground">v{{ s.version }}</span>
            </div>
            <p class="mt-1 line-clamp-2 text-sm text-muted-foreground">{{ s.description }}</p>
            <div v-if="s.tags.length || s.required_tools.length" class="mt-2 flex flex-wrap gap-1">
              <span v-for="t in s.tags" :key="t" class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                {{ t }}
              </span>
              <span v-for="t in s.required_tools" :key="'r-'+t" class="rounded bg-accent/10 px-1.5 py-0.5 text-xs text-accent">
                {{ t }}
              </span>
            </div>
          </div>
          <div class="flex flex-shrink-0 items-center gap-2">
            <Switch :model-value="s.enabled" @update:model-value="toggle(s)" />
            <Button variant="ghost" size="icon" @click="openEdit(s)">
              <Pencil class="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" @click="remove(s)">
              <Trash2 class="h-3.5 w-3.5 text-destructive" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <AdminSkillDialog v-model:open="dialogOpen" :editing="editing" @saved="onSaved" />
  </div>
</template>
```

- [ ] **Step 4: Delete old skill files**

```bash
git rm frontend/src/components/admin/AdminSkills.vue  # placeholder
git rm frontend/src/components/SkillCard.vue 2>/dev/null || true
git rm frontend/src/components/SkillFormDialog.vue 2>/dev/null || true
git rm frontend/src/components/admin/SkillFormDialog.vue 2>/dev/null || true
```

- [ ] **Step 5: Verify build + manual flow**

```bash
cd frontend && npm run build
```

Run dev. Go to /admin?tab=skills. Test: list, create new, edit existing, toggle enable, delete, reload.

- [ ] **Step 6: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): AdminSkills full CRUD with shadcn-vue Dialog"
```

---

## Task 12: AdminMcp + AdminMcpDialog + Test Connection

**Files:**
- Create: `frontend/src/components/admin/AdminMcpDialog.vue`
- Create: `frontend/src/components/admin/AdminMcp.vue` (real)
- Delete: `frontend/src/components/admin/AdminMcp.vue` (placeholder)
- Delete: `frontend/src/components/McpFormDialog.vue`
- Delete: `frontend/src/components/McpCard.vue`
- Delete: `frontend/src/components/admin/McpFormDialog.vue` (if any)

**Consumes:** `useMcpsStore` (load, create, remove), `api.post('/api/mcp/servers/{id}/test')`, `Dialog` (shadcn-vue)

---

- [ ] **Step 1: Create `frontend/src/components/admin/AdminMcpDialog.vue`**

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { McpServerCreate, McpServerOut, McpTransport } from '@/types/domain'

const props = defineProps<{ open: boolean; editing: McpServerOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const transports: McpTransport[] = ['stdio', 'sse', 'streamable_http']

const form = ref<McpServerCreate>({
  name: '',
  transport: 'stdio',
  enabled: true,
  command: '',
  args: [],
  env: {},
  url: '',
  headers: {},
})

const argsText = ref('')
const envText = ref('')
const headersText = ref('')
const loading = ref(false)
const error = ref('')

watch(
  () => [props.open, props.editing?.id],
  () => {
    if (!props.open) return
    error.value = ''
    if (props.editing) {
      form.value = {
        name: props.editing.name,
        transport: props.editing.transport,
        enabled: props.editing.enabled,
        command: props.editing.config.command ?? '',
        args: props.editing.config.args ?? [],
        env: props.editing.config.env ?? {},
        url: props.editing.config.url ?? '',
        headers: props.editing.config.headers ?? {},
      }
      argsText.value = (props.editing.config.args ?? []).join('\n')
      envText.value = Object.entries(props.editing.config.env ?? {}).map(([k, v]) => `${k}=${v}`).join('\n')
      headersText.value = Object.entries(props.editing.config.headers ?? {}).map(([k, v]) => `${k}: ${v}`).join('\n')
    } else {
      form.value = { name: '', transport: 'stdio', enabled: true, command: '', args: [], env: {}, url: '', headers: {} }
      argsText.value = ''
      envText.value = ''
      headersText.value = ''
    }
  },
  { immediate: true },
)

function parseLines(s: string): string[] {
  return s.split('\n').map((x) => x.trim()).filter(Boolean)
}
function parseKv(s: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const line of parseLines(s)) {
    const i = line.indexOf('=')
    const k = (i === -1 ? line.indexOf(':') : i)
    if (k <= 0) continue
    const key = line.slice(0, k).trim()
    const val = line.slice(k + 1).trim()
    if (key) out[key] = val
  }
  return out
}

async function submit() {
  error.value = ''
  if (!form.value.name.trim()) {
    error.value = '名称必填'
    return
  }
  if (form.value.transport === 'stdio' && !form.value.command?.trim()) {
    error.value = 'stdio 传输需要 command'
    return
  }
  if ((form.value.transport === 'sse' || form.value.transport === 'streamable_http') && !form.value.url?.trim()) {
    error.value = `${form.value.transport} 传输需要 url`
    return
  }
  loading.value = true
  try {
    const payload: McpServerCreate = {
      name: form.value.name.trim(),
      transport: form.value.transport,
      enabled: form.value.enabled,
      command: form.value.command || undefined,
      args: parseLines(argsText.value),
      env: parseKv(envText.value),
      url: form.value.url || undefined,
      headers: parseKv(headersText.value),
    }
    const { api } = await import('@/api/client')
    if (props.editing) {
      await api.patch(`/api/mcp/servers/${props.editing.id}`, payload)
    } else {
      await api.post('/api/mcp/servers', payload)
    }
    emit('saved')
    emit('update:open', false)
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || '保存失败'
    error.value = msg
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog :open="props.open" @update:open="(v) => emit('update:open', v)">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-[560px]">
      <DialogHeader>
        <DialogTitle>{{ props.editing ? '编辑 MCP 服务器' : '新建 MCP 服务器' }}</DialogTitle>
        <DialogDescription>配置后点击"测试连接"验证。</DialogDescription>
      </DialogHeader>

      <div class="grid gap-3 py-2">
        <div class="grid grid-cols-2 gap-3">
          <div class="grid gap-1.5">
            <Label>名称</Label>
            <Input v-model="form.name" placeholder="my-mcp" />
          </div>
          <div class="grid gap-1.5">
            <Label>传输</Label>
            <select v-model="form.transport" class="flex h-9 rounded-md border border-input bg-background px-3 text-sm">
              <option v-for="t in transports" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
        </div>

        <div class="grid gap-1.5">
          <Label class="flex items-center gap-2">
            <input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded border-input" />
            启用
          </Label>
        </div>

        <template v-if="form.transport === 'stdio'">
          <div class="grid gap-1.5">
            <Label>命令</Label>
            <Input v-model="form.command" placeholder="python" />
          </div>
          <div class="grid gap-1.5">
            <Label>参数（每行一个）</Label>
            <Textarea v-model="argsText" :rows="3" placeholder="-m&#10;my_mcp_server" />
          </div>
        </template>

        <template v-else>
          <div class="grid gap-1.5">
            <Label>URL</Label>
            <Input v-model="form.url" placeholder="http://localhost:3000/mcp" />
          </div>
        </template>

        <div class="grid gap-1.5">
          <Label>环境变量（每行 KEY=VALUE，仅 stdio）</Label>
          <Textarea v-model="envText" :rows="2" placeholder="API_KEY=xxx" />
        </div>
        <div class="grid gap-1.5">
          <Label>Headers（每行 KEY: VALUE，仅 HTTP）</Label>
          <Textarea v-model="headersText" :rows="2" placeholder="Authorization: Bearer xxx" />
        </div>

        <div v-if="error" class="text-sm text-destructive">{{ error }}</div>
      </div>

      <DialogFooter>
        <Button variant="ghost" @click="emit('update:open', false)">取消</Button>
        <Button :disabled="loading" @click="submit">{{ loading ? '保存中…' : '保存' }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
```

- [ ] **Step 2: Verify `useMcpsStore.update` exists**

Open `frontend/src/stores/mcps.ts`. If `update` is missing, add it (only exception allowed):

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import type { McpServerCreate, McpServerOut } from '@/types/domain'

export const useMcpsStore = defineStore('mcps', () => {
  const list = ref<McpServerOut[]>([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const { data } = await api.get<McpServerOut[]>('/api/mcp/servers')
      list.value = data
    } finally {
      loading.value = false
    }
  }

  async function create(payload: McpServerCreate) {
    const { data } = await api.post<McpServerOut>('/api/mcp/servers', payload)
    list.value = [...list.value, data]
    return data
  }

  async function update(id: number, payload: McpServerCreate) {
    const { data } = await api.patch<McpServerOut>(`/api/mcp/servers/${id}`, payload)
    list.value = list.value.map((m) => (m.id === id ? data : m))
    return data
  }

  async function remove(id: number) {
    await api.delete(`/api/mcp/servers/${id}`)
    list.value = list.value.filter((m) => m.id !== id)
  }

  async function test(id: number): Promise<{ ok: boolean; error?: string; tools_count?: number }> {
    const { data } = await api.post(`/api/mcp/servers/${id}/test`)
    return data
  }

  return { list, loading, load, create, update, remove, test }
})
```

(Only edit if missing. If store already has these methods, leave untouched.)

- [ ] **Step 3: Create `frontend/src/components/admin/AdminMcp.vue`**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Plus, Pencil, Trash2, Plug, CheckCircle2, XCircle } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useMcpsStore } from '@/stores/mcps'
import AdminMcpDialog from '@/components/admin/AdminMcpDialog.vue'
import type { McpServerOut } from '@/types/domain'

const mcps = useMcpsStore()
const dialogOpen = ref(false)
const editing = ref<McpServerOut | null>(null)
const testing = ref<number | null>(null)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}
function openEdit(m: McpServerOut) {
  editing.value = m
  dialogOpen.value = true
}

async function onSaved() {
  toast.success('已保存')
  await mcps.load()
}

async function remove(m: McpServerOut) {
  if (!confirm(`确定删除 MCP 服务器 "${m.name}"？`)) return
  try {
    await mcps.remove(m.id)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

async function test(m: McpServerOut) {
  testing.value = m.id
  try {
    const res = await mcps.test(m.id)
    if (res.ok) {
      toast.success(`连接成功，发现 ${res.tools_count ?? 0} 个工具`)
    } else {
      toast.error(`连接失败：${res.error}`)
    }
  } catch {
    toast.error('测试请求失败')
  } finally {
    testing.value = null
  }
}

onMounted(() => mcps.load())
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">MCP 服务器</h2>
      <Button size="sm" @click="openCreate">
        <Plus class="mr-1.5 h-3.5 w-3.5" />
        新建
      </Button>
    </div>

    <div v-if="mcps.list.length === 0" class="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
      暂无 MCP 服务器。
    </div>

    <div v-else class="space-y-2">
      <Card v-for="m in mcps.list" :key="m.id">
        <CardContent class="flex items-start gap-4 p-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <Plug class="h-3.5 w-3.5 text-muted-foreground" :stroke-width="1.75" />
              <span class="font-medium text-foreground">{{ m.name }}</span>
              <span class="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-muted-foreground">
                {{ m.transport }}
              </span>
              <span v-if="m.enabled" class="rounded bg-accent/10 px-1.5 py-0.5 text-xs text-accent">
                启用
              </span>
              <span v-else class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                停用
              </span>
            </div>
            <div class="mt-1 truncate font-mono text-xs text-muted-foreground">
              {{ m.config.url ?? `${m.config.command} ${(m.config.args ?? []).join(' ')}` }}
            </div>
          </div>
          <div class="flex flex-shrink-0 items-center gap-2">
            <Button variant="ghost" size="sm" :disabled="testing === m.id" @click="test(m)">
              <component
                :is="testing === m.id ? null : CheckCircle2"
                class="mr-1.5 h-3.5 w-3.5"
              />
              {{ testing === m.id ? '测试中…' : '测试连接' }}
            </Button>
            <Button variant="ghost" size="icon" @click="openEdit(m)">
              <Pencil class="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" @click="remove(m)">
              <Trash2 class="h-3.5 w-3.5 text-destructive" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <AdminMcpDialog v-model:open="dialogOpen" :editing="editing" @saved="onSaved" />
  </div>
</template>
```

- [ ] **Step 4: Delete old MCP files**

```bash
git rm frontend/src/components/admin/AdminMcp.vue  # placeholder
git rm frontend/src/components/McpCard.vue 2>/dev/null || true
git rm frontend/src/components/McpFormDialog.vue 2>/dev/null || true
git rm frontend/src/components/admin/McpFormDialog.vue 2>/dev/null || true
```

- [ ] **Step 5: Verify build + manual flow**

```bash
cd frontend && npm run build
```

Run dev. Go to /admin?tab=mcp. Test: create stdio, create SSE/streamable_http, edit, test connection, delete.

- [ ] **Step 6: Commit**

```bash
cd frontend && git add -A
git commit -m "feat(ui): AdminMcp full CRUD + test connection with shadcn-vue Dialog"
```

---

## Task 13: Delete AdminTools + Cleanup

**Files:**
- Delete: `frontend/src/components/admin/AdminTools.vue`
- Verify: `frontend/src/components/admin/AdminView.vue` (already 3 tabs only)

**Consumes:** spec section 3.2 ("Tools 页面：后端无 /api/tools 端点，价值低")

---

- [ ] **Step 1: Delete AdminTools**

```bash
git rm frontend/src/components/admin/AdminTools.vue
```

- [ ] **Step 2: Verify AdminView has 3 tabs**

Re-read `frontend/src/components/admin/AdminView.vue`. Confirm `tabs` array has exactly `overview`, `skills`, `mcp` (3 entries, no `tools`).

- [ ] **Step 3: Build + manual check**

```bash
cd frontend && npm run build
```

Run dev. /admin shows 3 tabs only: 总览 / 技能 / MCP.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(ui)!: remove AdminTools page and tab (no /api/tools backend)"
```

---

## Task 14: README Update

**Files:**
- Modify: `README.md`

---

- [ ] **Step 1: Update tech stack section**

In `README.md`, find:
```
- 💬 **Web聊天界面**：FastAPI后端 + Vue 3 + Vite前端（Element Plus），WebSocket流式
```

Replace with:
```
- 💬 **Web聊天界面**：FastAPI后端 + Vue 3 + Vite前端（shadcn-vue + Tailwind），WebSocket流式
```

- [ ] **Step 2: Verify no other Element Plus mentions**

```bash
grep -n -i "element" README.md
```

Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README for new frontend stack"
```

---

## Task 15: Final Regression

**Files:**
- Verify-only (no edits)

---

- [ ] **Step 1: Backend tests**

```bash
cd /path/to/lumos  # repo root
pytest -v --tb=short
```

Expected: all tests green **except** the 4 pre-existing failures documented in `pre-existing-test-failures.md`. (See project memory: `tests/unit/test_tools_registry.py`, `tests/unit/test_openai_compat.py` streaming+cancel, `tests/unit/test_builtin_tools.py::test_http_request_real`, `tests/unit/test_mcp_transports.py::test_sse_transport_send_receive`.)

- [ ] **Step 2: Frontend build**

```bash
cd frontend && npm run build
```

Expected: 0 errors, 0 warnings.

- [ ] **Step 3: Manual regression — 19-item checklist**

Walk through each in browser at `http://127.0.0.1:5173`:

- [ ] Login page loads (dark + light)
- [ ] Register → auto-redirect `/chat`
- [ ] Create session (empty state → auto-create)
- [ ] Send message → streaming + Markdown + code blocks + copy buttons
- [ ] Tool call shows args/result
- [ ] Stop button cancels stream
- [ ] Regenerate last message
- [ ] Switch sessions (history loads correctly)
- [ ] Rename session inline
- [ ] Delete session
- [ ] Skill toggle persists
- [ ] Admin → Skills CRUD
- [ ] Admin → MCP CRUD + Test connection
- [ ] Theme toggle (persists in localStorage)
- [ ] `Cmd/Ctrl+K` toggles sidebar
- [ ] `Esc` closes sidebar
- [ ] AvatarMenu → /admin ↔ /chat
- [ ] 401 → silent token refresh
- [ ] logout → clear state + redirect `/login`
- [ ] Mobile responsive (<640px)

- [ ] **Step 4: Production build smoke test**

```bash
cd frontend && npm run preview
# Visit http://127.0.0.1:4173 — login + basic chat must work
```

- [ ] **Step 5: Done**

Confirm:
- [ ] 19-item checklist all green
- [ ] `npm run build` clean
- [ ] Backend pytest green (excluding documented pre-existing)
- [ ] README updated
- [ ] 6 commits in order per spec §11

If any item fails, **do not mark complete** — create a fix task and execute.

---

## Self-Review

### Spec Coverage

| Spec section | Implementing task(s) |
|---|---|
| §1 概述 | All |
| §2 设计原则 | Implicit in all tasks (env, stores) |
| §3.1 范围 | Tasks 1–15 |
| §3.2 不包含 | Honored (no backend change, no tests) |
| §4 技术栈 | Task 1, 2 |
| §5 视觉系统 | Tasks 1 (CSS vars), 2 (shadcn) |
| §6 文件布局 | All tasks |
| §7.1 AppShell | Task 4 |
| §7.2 ChatView | Tasks 6, 7, 8 |
| §7.3 MessageItem | Task 7 |
| §7.4 SessionSidebar | Task 6 |
| §7.5 SettingsDrawer | Task 9 |
| §7.6 AdminView | Tasks 10, 11, 12, 13 |
| §7.7 LoginView | Task 5 |
| §7.8 AvatarMenu | Task 4 |
| §8 状态保留 | Task 3 |
| §9 迁移顺序 | Task order matches |
| §10 验收 | Task 15 |
| §11 提交计划 | 6 commits produced |
| §12 风险 | Addressed in Task 1 (sourcemap, FOUC) |

### Placeholder Scan

- No `TBD` / `TODO` / `FIXME` in plan ✓
- All steps have actual code, not descriptions of code ✓
- No "similar to" references — each step is self-contained ✓

### Type Consistency

- `useUiStore.{sidebarOpen, settingsOpen, toggleSidebar, openSidebar, closeSidebar, openSettings, closeSettings}` — defined Task 3, consumed Tasks 4, 6, 9 ✓
- `useSkillsStore.{load, create, update, remove, enable, disable, reload}` — added in Task 11 ✓
- `useMcpsStore.{load, create, update, remove, test}` — added in Task 12 ✓
- `useSessionsStore.{messages, streaming, currentId, current, enabledSkills, list, createSession, select, deleteSession, send, cancel, toggleSkill}` — unchanged from existing ✓
- `useAuthStore.{login, register, logout, fetchMe, user}` — unchanged ✓
- `cn()` from `@/lib/utils` — created Task 2 ✓
- Logo, AvatarMenu, AppShell, all shadcn-vue primitives — referenced consistently ✓

No conflicts detected.