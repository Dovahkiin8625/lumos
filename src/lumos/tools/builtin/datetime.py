"""当前时间工具。"""
from __future__ import annotations
from datetime import datetime, timezone
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool


@register_tool(
    name="datetime_now",
    description="Get the current date and time in a specified timezone.",
    parameters={
        "type": "object",
        "properties": {
            "tz": {
                "type": "string",
                "description": "IANA timezone name, e.g. Asia/Shanghai. Default UTC.",
                "default": "UTC",
            },
        },
        "required": [],
    },
)
class DateTimeTool(Tool):
    async def execute(self, *, tz: str = "UTC") -> str:
        try:
            zone = timezone.utc if tz == "UTC" else __import__("zoneinfo").ZoneInfo(tz)
        except Exception:
            zone = timezone.utc
            tz = "UTC"
        now = datetime.now(zone)
        return now.strftime(f"%Y-%m-%d %H:%M:%S %Z ({tz})")