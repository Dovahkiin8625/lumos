# Skills系统

每个Skill是一个目录，含`SKILL.md`（YAML frontmatter + Markdown正文）。

## 创建Skill

### 通过管理界面（推荐）

登录后进入 **管理 → Skills**，点击右上角「+ 新建技能」。表单字段与下方元数据表一一对应，
`指令` 字段支持 Markdown，左侧编辑、右侧实时预览。保存后立即生效（无需重启）。

新建/编辑/删除操作会写到 `config.yaml` 中 `skills.dirs` 的**第一个**目录。

### 手动创建

```bash
mkdir -p skills/my-skill
cat > skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: 简短的skill描述（LLM根据这个决定何时启用）
required_tools: [web_search]
optional_tools: []
---

# 我的Skill

详细指令注入到系统提示词。

## 工作流

步骤1...
步骤2...
EOF
```

## 元数据字段

| 字段 | 类型 | 说明 |
|---|---|---|
| name | str | Skill名称（必填，目录名；`^[a-z0-9][a-z0-9_-]{0,63}$`） |
| description | str | 描述（必填，LLM据此选择） |
| version | str | 版本号 |
| tags | list[str] | 标签 |
| required_tools | list[str] | 必需工具，缺失则禁用 |
| optional_tools | list[str] | 可选工具 |
| max_steps | int | Agent最大步数覆盖 |
| instructions | str | Markdown 正文，注入系统提示词 |

## 管理 API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/skills` | 列出全部技能 |
| POST | `/api/skills` | 新建技能（body 见 `SkillCreate`） |
| GET | `/api/skills/{name}` | 单个技能详情 |
| PUT | `/api/skills/{name}` | 更新技能（仅修改传入字段） |
| DELETE | `/api/skills/{name}` | 删除技能目录 |
| POST | `/api/skills/{name}/enable` | 启用 |
| POST | `/api/skills/{name}/disable` | 禁用 |
| POST | `/api/skills/reload` | 重新扫描所有配置目录 |

## 携带工具

Skill目录可包含`tools/`子目录，专属工具的Python代码。