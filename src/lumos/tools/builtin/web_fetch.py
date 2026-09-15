"""URL抓取转Markdown工具。"""
from __future__ import annotations
import httpx
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="web_fetch",
    description="Fetch a URL and extract its main content as Markdown.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer", "default": 20000, "maximum": 100000},
        },
        "required": ["url"],
    },
)
class WebFetchTool(Tool):
    async def execute(self, *, url: str, max_chars: int = 20000) -> str:
        try:
            import trafilatura
            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True,
                headers={"User-Agent": "Lumos/0.1 (+https://lumos.local)"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
            text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n...[truncated, total {len(text)} chars]"
            return f"Source: {url}\n\n{text}" if text else f"No content extracted from {url}"
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="web_fetch", cause=e) from e