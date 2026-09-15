"""Tool抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field


@dataclass
class ToolMeta:
    """工具元数据（装饰器注入）。"""
    name: str
    description: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False


class Tool(ABC):
    """所有工具的抽象基类。子类必须设置meta并实现execute。"""

    meta: ToolMeta

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """执行工具，返回文本结果。抛ToolExecutionError表示执行失败。"""
        ...
