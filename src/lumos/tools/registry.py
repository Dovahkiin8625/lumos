"""工具注册中心。"""
from __future__ import annotations
from typing import Any
import importlib
import pkgutil
from lumos.agent.message import ToolSpec
from lumos.tools.base import Tool, ToolMeta


class ToolRegistry:
    """工具注册表，存储Tool实例并生成OpenAI兼容的tools列表。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.meta.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name]

    def get_spec(self, name: str) -> ToolSpec | None:
        tool = self._tools.get(name)
        if tool is None:
            return None
        m = tool.meta
        return ToolSpec(
            name=m.name, description=m.description,
            parameters=m.parameters,
            requires_confirmation=m.requires_confirmation,
            source="builtin",
        )

    def all_specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name=t.meta.name, description=t.meta.description,
                parameters=t.meta.parameters,
                requires_confirmation=t.meta.requires_confirmation,
                source="builtin",
            )
            for t in self._tools.values()
        ]

    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self.all_specs()
        ]

    def discover(self, package: str = "lumos.tools.builtin") -> None:
        """扫描内置工具包，自动注册所有Tool子类。"""
        try:
            pkg = importlib.import_module(package)
        except ImportError:
            return
        for mod_info in pkgutil.iter_modules(pkg.__path__):
            mod = importlib.import_module(f"{package}.{mod_info.name}")
            for name in dir(mod):
                obj = getattr(mod, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, Tool)
                    and obj is not Tool
                    and hasattr(obj, "meta")
                ):
                    self.register(obj())

    def discover_globals(self, tools: list[type[Tool]]) -> None:
        """显式注册一组Tool类（用于测试或非builtin场景）。"""
        for cls in tools:
            if (
                isinstance(cls, type)
                and issubclass(cls, Tool)
                and cls is not Tool
                and hasattr(cls, "meta")
            ):
                self.register(cls())


def register_tool(
    *,
    name: str,
    description: str,
    parameters: dict[str, Any],
    requires_confirmation: bool = False,
):
    """Tool类装饰器：注入meta。"""
    def decorator(cls: type[Tool]) -> type[Tool]:
        cls.meta = ToolMeta(
            name=name, description=description,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
        )
        return cls
    return decorator
