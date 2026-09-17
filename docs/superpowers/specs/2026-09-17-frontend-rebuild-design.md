# Lumos 前端重建 — 设计文档

**日期**: 2026-09-17
**状态**: 设计中，等待用户审阅
**范围**: 完全重写 `frontend/src/` 表现层，业务逻辑层保留

---

## 1. 概述

丢弃现有前端页面（基于 Vue 3 + Element Plus）并基于 Vue 3 + shadcn-vue + Tailwind 重建视觉与交互层，保留全部业务功能（登录、会话、流式对话、Skills、MCP、Admin）。

- **目标**：用更现代的视觉风格（Notion 风 / 现代极简）替换 Element Plus 工业风界面
- **交付形态**：同一 `frontend/` 目录，同一 `dist/` 构建产物，同一 FastAPI 静态服务
- **业务边界**：后端 API、Pinia store 内部逻辑、WS 协议、类型定义 **均不改动**
- **明确删除**：`AdminTools` 页面与对应 tab（后端无 `/api/tools` 端点，价值低）

---

## 2. 设计原则

1. **业务逻辑零回归** — `api/`、`stores/`、`types/` 内部实现一字不动；重写仅限于表现层（`.vue` + 样式）
2. **生态延续** — 保留 Vue 3 + Pinia + Vue Router；仅替换组件库与样式方案
3. **样式收敛** — 用 Tailwind utility 类 + CSS 变量替代散落的 `:root` token 与 scoped 样式
4. **暗色优先** — 默认暗色主题；通过 `<html class="dark">` 切换，避免 FOUC
5. **可测试** — 不引入新测试框架，依赖手工验收清单 + 后端 pytest

---

## 3. 范围与边界

### 3.1 本次重写包含

- `frontend/src/components/` 下所有 `.vue` 文件（重写）
- `frontend/src/views/` 视图文件（移到 `components/` 下相应子目录）
- `frontend/src/styles/` 整体替换为 Tailwind
- 依赖调整：`package.json` 移除 element-plus + @lucide/vue，新增 Tailwind + shadcn-vue + vue-sonner + @vueuse/core 等
- `frontend/index.html` 调整 lang/title
- `frontend/vite.config.ts` 关 sourcemap（生产构建体积）
- README.md 更新技术栈描述

### 3.2 本次重写不包含

- 后端 Python 代码（0 改动）
- `frontend/src/api/` 业务代码（0 改动）
- `frontend/src/stores/` 业务逻辑（仅 `stores/theme.ts` 删除，`stores/ui.ts` 实现简化）
- `frontend/src/types/` 类型（0 改动）
- `frontend/src/router/index.ts`（0 改动）
- 前端测试栈引入（Vitest/Playwright）
- 后端 `/api/tools` 端点新增
- 任何功能新增（导出、搜索、Token 仪表盘等）

---

## 4. 技术栈

| 类别 | 之前 | 之后 |
|---|---|---|
| 框架 | Vue 3.5 + TS + Vite | 不变 |
| 状态 | Pinia | 不变 |
| 路由 | Vue Router 4 | 不变 |
| HTTP | axios | 不变 |
| WS | 自研 `WsClient` | 不变 |
| **组件库** | Element Plus 2.18 | **shadcn-vue (radix-vue + Tailwind)** |
| **样式** | 自写 `tokens.css` + scoped CSS | **Tailwind v3 + CSS 变量** |
| **图标** | @lucide/vue | **lucide-vue-next**（shadcn-vue 默认） |
| Markdown | marked + highlight.js | 不变 |
| 主题 | `useThemeStore` + `lumos-light`/`lumos-dark` 类 | **`useDark()` from @vueuse/core + Tailwind `dark:`** |
| Toast | `ElMessage` / `ElMessageBox` | **Sonner (`vue-sonner`)** |
| 新增工具库 | — | `@vueuse/core`（`useDark` / `useMediaQuery` / `useLocalStorage`） |
| 辅助 | — | `class-variance-authority`、`clsx`、`tailwind-merge`、`tailwindcss-animate`、`@tailwindcss/typography` |

### 4.1 删除依赖

- `element-plus` — 由 shadcn-vue Dialog/Dropdown/Tabs/Switch 等替代
- `@lucide/vue` — 由 `lucide-vue-next` 替代（shadcn-vue 默认）
- `marked-highlight`（如果单独安装） — shadcn-vue 代码块用 highlight.js

### 4.2 新增依赖

```
tailwindcss
@tailwindcss/postcss
@tailwindcss/typography
tailwindcss-animate
class-variance-authority
clsx
tailwind-merge
radix-vue
lucide-vue-next
@vueuse/core
vue-sonner
shadcn-vue (CLI devDep)
```

---

## 5. 视觉系统

### 5.1 色彩（CSS 变量驱动 Tailwind）

- 浅色：白底 + 近黑前景 + 蓝色品牌 `#3B82F6`
- 暗色：近黑底 `#0A0A0F` + 浅灰前景 + 蓝色品牌（同上）
- 圆角：`--radius: 0.5rem`（`rounded-md` / `rounded-lg`）
- 边框：1px hairline（`#E5E5E5` 浅 / `#262626` 暗）
- 阴影：仅 `shadow-sm` / `shadow`，无 `shadow-md` 以上的"重投影"

### 5.2 字体

- 字体栈：`ui-sans-serif, system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", ...`
- 等宽：`ui-monospace, "JetBrains Mono", "Cascadia Code", Menlo, ...`
- **不引入 Google Fonts**，保持离线可用

### 5.3 间距与动效

- 间距：Tailwind 默认 4px 步进
- 动效：所有交互 150ms ease-out（hover/focus），100ms ease-in（退场）
- 不引入额外动画库

### 5.4 暗色切换

- `useDark()` from `@vueuse/core` 单一来源
- `<html>` 上加 `class="dark"`，Tailwind `darkMode: 'class'`
- main.ts 挂载前应用主题，零 FOUC

---

## 6. 文件布局

### 6.1 保留（业务逻辑层）

```
frontend/src/
  api/client.ts                  ← axios + 401 刷新（不改）
  api/ws.ts                      ← WsClient（含重连，不改）
  stores/auth.ts                 ← JWT 用户状态（不改）
  stores/sessions.ts             ← 会话 + WS 事件聚合（不改）
  stores/skills.ts               ← 技能缓存（不改）
  stores/mcps.ts                 ← MCP 缓存（不改）
  stores/ui.ts                   ← 简化为 sidebar/settings 状态
  types/domain.ts                ← 与后端 Pydantic 对齐（不改）
  router/index.ts                ← 路由表（不改）
```

### 6.2 重写（表现层）

```
frontend/src/
  components/
    ui/                          ← shadcn-vue CLI 生成（17 个原子组件）
      button.vue / input.vue / textarea.vue / dialog/
      dropdown-menu/ / sheet/ / tabs/ / switch/ / skeleton/
      tooltip.vue / popover/ / label.vue / card.vue / sonner/
      scroll-area/ / separator/ / avatar.vue
    layout/
      AppShell.vue               ← 顶部条 + AvatarMenu + Sidebar + Settings
    chat/
      ChatView.vue               ← 容器
      Composer.vue               ← 输入区
      MessageList.vue            ← 滚动列表 + 空态
      MessageItem.vue            ← 单条消息渲染
      ToolCallCard.vue           ← 折叠/展开 + 复制
      WelcomePanel.vue           ← 空态欢迎
      SessionSidebar.vue         ← Sheet 形式
    settings/
      SettingsDrawer.vue         ← Sheet 形式
    admin/
      AdminView.vue              ← Tabs 容器
      AdminOverview.vue          ← 仪表盘
      AdminSkills.vue            ← 列表
      AdminSkillDialog.vue       ← 创建/编辑对话框
      AdminMcp.vue               ← 列表
      AdminMcpDialog.vue         ← 创建/编辑对话框
      AdminMcpTestButton.vue     ← 测试连接
    auth/
      LoginView.vue              ← 登录/注册
    common/
      AvatarMenu.vue             ← 头像下拉
      Logo.vue                   ← SVG Logo
  composables/                   ← 可选：useShortcut 等
  App.vue                        ← Toaster + RouterView
  main.ts                        ← Tailwind + Toaster + 主题初始化
  style.css                      ← Tailwind base + CSS 变量
```

### 6.3 删除

```
frontend/src/styles/tokens.css          ← 由 tailwind.config + style.css 替代
frontend/src/styles/global.css         ← 同上
frontend/src/views/                     ← 整个目录（迁到 components/）
frontend/src/components/admin/AdminTools.vue  ← 后端无 /api/tools
frontend/src/stores/theme.ts            ← 改用 useDark()
frontend/src/utils/markdown.ts          ← 移到 components/chat/ 局部
```

---

## 7. 组件详细设计

### 7.1 AppShell（重写）

```
┌─ header (40px) ────────────────────────────────────────────────┐
│ [☰] Lumos   [Title - inline editable]              (avatar) │
├─ main (flex-1, overflow-hidden) ─────────────────────────────┤
│ <router-view/>                                                │
└───────────────────────────────────────────────────────────────┘
```

- `<Sheet>` 触发：sidebar（左侧）/ settings（右侧）
- 快捷键：`Cmd/Ctrl+K` 切 sidebar；`Esc` 关 sidebar
- AvatarMenu（DropdownMenu）：主题 / 后台管理 / 技能&MCP / 登出

### 7.2 ChatView

```
<main flex flex-col h-full>
  <MessageList class="flex-1 overflow-y-auto" />
  <Composer class="px-4 pb-6" />
</main>
```

- `MessageList`：
  - 空态：`<WelcomePanel onPrompt=...>`
  - 滚动列表：`<MessageItem>` for 持久化消息 + 末尾流式消息
  - 自动滚到底（新内容 / 流式 delta）
- `Composer`：
  - `<Textarea>` + `<SendButton>` / `<StopButton>`（流式中切换）
  - `Enter` 发送、`Shift+Enter` 换行

### 7.3 MessageItem

- 用户：右对齐气泡 `bg-muted rounded-2xl`
- 助手：左对齐，无气泡；`prose prose-sm dark:prose-invert max-w-none` 包裹
- 代码块：highlight.js 主题 + 复制按钮（utils/markdown 逻辑迁移）
- 工具调用：`<ToolCallCard>` 折叠 args / result / is_error
- 流式中：caret 闪烁（CSS animation 1s infinite）

### 7.4 SessionSidebar（Sheet）

- 列表按 `updated_at` desc
- "+ 新会话" 顶部 ghost button
- 每条：左标题（inline rename）、右删除按钮（hover 显现）
- 空态：居中"还没有会话"

### 7.5 SettingsDrawer（Sheet）

- Tabs：Skills（默认）/ MCP（只读预览）
- Skills：Switch 列表，切换调用 `useSessionsStore.toggleSkill()`

### 7.6 AdminView

- Tabs root：`overview | skills | mcp`
- `AdminOverview`（重写）：健康检查结果 + Provider 状态 + 会话计数
- `AdminSkills` + `AdminSkillDialog`：CRUD + enable/disable + reload
- `AdminMcp` + `AdminMcpDialog`：CRUD + 测试连接

### 7.7 LoginView

- 单卡片 360px，`bg-card` + `border` + `rounded-lg`
- Tabs：登录 / 注册
- 表单：Email + Password（Input + Label）
- 主按钮：Submit（loading 时禁用 + spinner）
- 错误反馈：Sonner toast

### 7.8 AvatarMenu（DropdownMenu）

- 头像按钮（左下角浮动，Button size="icon" variant="ghost"）
- Items：主题切换 / 后台管理（仅 /chat） / 技能&MCP / 登出

---

## 8. 状态保留

### 8.1 Pinia store 调整

| Store | 改动 |
|---|---|
| `auth.ts` | 0 改动 |
| `sessions.ts` | 0 改动 |
| `skills.ts` | 0 改动 |
| `mcps.ts` | 0 改动 |
| `ui.ts` | 简化实现（保留字段） |
| `theme.ts` | **删除**，改用 `useDark()` |

### 8.2 `useUiStore` 简化后

```ts
export const useUiStore = defineStore('ui', () => {
  const sidebarOpen = ref(false)
  const settingsOpen = ref(false)
  return {
    sidebarOpen, settingsOpen,
    toggleSidebar: () => sidebarOpen.value = !sidebarOpen.value,
    openSidebar: () => sidebarOpen.value = true,
    closeSidebar: () => sidebarOpen.value = false,
    openSettings: () => settingsOpen.value = true,
    closeSettings: () => settingsOpen.value = false,
  }
})
```

---

## 9. 迁移顺序

1. **环境层** — 改 `package.json`；建 `tailwind.config.ts` / `postcss.config.js` / `style.css`
2. **shadcn-vue 初始化** — `npx shadcn-vue@latest init`；注册 15 个原子组件
3. **样式清理** — 删 `tokens.css` / `global.css` / `views/` / `stores/theme.ts` / `utils/markdown.ts` / `AdminTools.vue`
4. **AppShell 重写** — 顶部条 + AvatarMenu
5. **LoginView 重写** — 移到 `components/auth/`
6. **SessionSidebar 重写** — Sheet 形式
7. **MessageList / MessageItem / ToolCallCard / Composer / WelcomePanel 重写**
8. **SettingsDrawer 重写**
9. **Admin 重写** — Overview / Skills CRUD / MCP CRUD（删除 Tools tab）
10. **App.vue / main.ts 重写** — Sonner Toaster + 主题初始化
11. **vite.config.ts** — 关 sourcemap
12. **README.md** — 更新技术栈描述
13. **手测验收清单**

---

## 10. 验收清单

### 10.1 功能回归（手测 + 截图）

- [ ] 登录页加载（暗/亮）
- [ ] 注册 → 自动跳转 `/chat`
- [ ] 创建会话（空态 → 自动创建）
- [ ] 发消息 → 流式返回 + Markdown + 代码块 + 复制按钮
- [ ] 工具调用显示参数/结果
- [ ] Stop 按钮可中断流
- [ ] regenerate 重新生成最后一条
- [ ] 切换会话（消息历史正确加载）
- [ ] 重命名会话（inline）
- [ ] 删除会话
- [ ] Skill 开关（立即持久化）
- [ ] Admin → Skills CRUD
- [ ] Admin → MCP CRUD + Test 连接
- [ ] 主题切换（持久化 localStorage）
- [ ] `Cmd/Ctrl+K` 切换 sidebar
- [ ] `Esc` 关闭 sidebar
- [ ] AvatarMenu 跳转 `/admin` ↔ `/chat`
- [ ] 401 → 静默刷新 token
- [ ] logout → 清状态 + 跳 `/login`
- [ ] 移动端响应式（<640px）

### 10.2 构建/质量

- [ ] `npm run build` 无 TS 错误、无 Vue 警告
- [ ] 切换暗/亮主题无 FOUC
- [ ] 首屏 < 200KB gzip（rough target）
- [ ] 后端 `pytest` 全绿（**排除 pre-existing failures 清单中的 4 个测试**）
- [ ] README 更新到位

### 10.3 DoD（Definition of Done）

1. 上述回归清单全部通过
2. `npm run build` 成功
3. 后端测试全绿（pre-existing 除外）
4. README 更新
5. Git 提交遵循现有 commit 约定

---

## 11. 提交计划

预计 6 个 commit：

1. `chore(deps): replace element-plus with tailwind + shadcn-vue`
2. `feat(ui): rewrite AppShell + LoginView with shadcn-vue`
3. `feat(ui): rewrite chat views (MessageList, MessageItem, Composer, Sidebar)`
4. `feat(ui): rewrite admin views (Overview, Skills CRUD, MCP CRUD)`
5. `feat(ui)!: remove AdminTools page and tab`
6. `docs: update README for new stack`

---

## 12. 风险与权衡

| 风险 | 应对 |
|---|---|
| shadcn-vue CLI 行为差异（vs shadcn/ui React） | 按官方文档初始化，先在空目录试一次 |
| Tailwind v3 vs v4 选择 | 默认 v3（稳定），如需 v4 单独里程碑评估 |
| `marked` 与 highlight.js 与 shadcn-vue 主题冲突 | shadcn-vue 自带代码块样式需手动关闭 |
| 暗色主题 FOUC | main.ts 同步读 localStorage + 立即设 `<html class>` |
| Pinia store 行为微变 | store 内部 0 改动；只重写消费它的 `.vue` 文件 |
| 移动端响应式回归 | 验收清单明确包含 <640px 手测 |
| 首屏体积膨胀 | Tailwind tree-shake + 不引入未用 shadcn 组件 |

---

## 13. 后续（非本次）

- `/api/tools` 端点新增 + AdminTools 复活
- 前端 Vitest 单元测试（store / ws）
- Playwright E2E
- 会话导出 / Token 仪表盘
- RAG 一阶段接入（独立 spec）