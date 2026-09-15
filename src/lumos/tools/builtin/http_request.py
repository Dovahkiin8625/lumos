"""通用HTTP请求工具。"""
from __future__ import annotations
import httpx
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="http_request",
    description="Make an HTTP request. Supports GET/POST/PUT/DELETE. Body must be JSON.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
            "headers": {"type": "object", "additionalProperties": {"type": "string"}},
            "json_body": {"type": "object"},
            "timeout": {"type": "integer", "default": 30, "maximum": 120},
        },
        "required": ["url", "method"],
    },
)
class HttpRequestTool(Tool):
    async def execute(
        self, *, url: str, method: str,
        headers: dict | None = None,
        json_body: dict | None = None,
        timeout: int = 30,
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method=method, url=url,
                    headers=headers or {},
                    json=json_body,
                )
            body_preview = resp.text[:5000]
            return f"Status: {resp.status_code}\n\n{body_preview}"
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="http_request", cause=e) from e