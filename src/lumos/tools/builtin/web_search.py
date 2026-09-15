"""DuckDuckGo搜索工具。"""
from __future__ import annotations
import asyncio
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="web_search",
    description="Search the web using DuckDuckGo. Returns top results with title, snippet, URL.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
)
class WebSearchTool(Tool):
    async def execute(self, *, query: str, max_results: int = 5) -> str:
        try:
            from duckduckgo_search import DDGS
            def _search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            results = await asyncio.to_thread(_search)
            if not results:
                return "No results found."
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"[{i}] {r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}")
            return "\n\n".join(lines)
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="web_search", cause=e) from e