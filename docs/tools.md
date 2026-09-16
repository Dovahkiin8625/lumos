# 扩展工具

工具通过装饰器或类注册到`ToolRegistry`。

## 装饰器方式（推荐）

```python
# src/lumos/tools/builtin/my_tool.py
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool

@register_tool(
    name="my_tool",
    description="做某事",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string"},
        },
        "required": ["input"],
    },
)
class MyTool(Tool):
    async def execute(self, *, input: str) -> str:
        return f"处理: {input}"
```

文件放到`src/lumos/tools/builtin/`下，会被自动发现。

## 类方式

```python
from lumos.tools.base import Tool, ToolMeta

class MyTool(Tool):
    meta = ToolMeta(
        name="my_tool",
        description="做某事",
        parameters={...},
    )
    async def execute(self, **kwargs):
        ...
```

## 危险操作

标记`requires_confirmation=True`，前端会弹窗确认。