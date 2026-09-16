# Skills系统

每个Skill是一个目录，含`SKILL.md`（YAML frontmatter + Markdown正文）。

## 创建Skill

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
| name | str | Skill名称（必填） |
| description | str | 描述（必填，LLM据此选择） |
| version | str | 版本号 |
| tags | list[str] | 标签 |
| required_tools | list[str] | 必需工具，缺失则禁用 |
| optional_tools | list[str] | 可选工具 |
| max_steps | int | Agent最大步数覆盖 |

## 携带工具

Skill目录可包含`tools/`子目录，专属工具的Python代码。