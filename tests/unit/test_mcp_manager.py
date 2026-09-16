"""测试MCP Manager（用一个假stdio MCP服务器脚本）。"""
from __future__ import annotations
import asyncio
import json
import shutil
import sys
from pathlib import Path
import pytest
from lumos.mcp.config import McpServerConfig
from lumos.mcp.manager import McpManager


def _find_python() -> str | None:
    """优先用当前解释器；回退到PATH查找（跳过Microsoft Store占位）。"""
    candidates = [sys.executable]
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and "WindowsApps" not in found:
            candidates.append(found)
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


PYTHON = _find_python()


FAKE_MCP_SCRIPT = """
import sys, json

def send(msg):
    print(json.dumps(msg), flush=True)

def handle(msg):
    method = msg.get("method")
    if method == "initialize":
        return {"jsonrpc":"2.0","id":msg["id"],"result":{
            "protocolVersion":"2024-11-05",
            "capabilities":{"tools":{"listChanged":False}},
            "serverInfo":{"name":"fake","version":"0.1.0"},
        }}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc":"2.0","id":msg["id"],"result":{
            "tools":[
                {"name":"echo","description":"echo","inputSchema":{
                    "type":"object",
                    "properties":{"text":{"type":"string"}},
                    "required":["text"],
                }},
            ]
        }}
    if method == "tools/call":
        return {"jsonrpc":"2.0","id":msg["id"],"result":{
            "content":[{"type":"text","text":msg["params"]["arguments"]["text"]}]
        }}
    return None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    resp = handle(msg)
    if resp is not None:
        send(resp)
"""


@pytest.fixture
def fake_mcp_path(tmp_path: Path) -> Path:
    p = tmp_path / "fake_mcp.py"
    p.write_text(FAKE_MCP_SCRIPT)
    return p


@pytest.mark.asyncio
async def test_manager_connect_and_list_tools(fake_mcp_path: Path):
    if not PYTHON:
        pytest.skip("no python interpreter")
    cfg = McpServerConfig(
        name="fake", transport="stdio",
        command=PYTHON, args=(str(fake_mcp_path),),
    )
    mgr = McpManager([cfg])
    await mgr.connect_all()
    try:
        tools = mgr.all_tools()
        names = {t.name for t in tools}
        assert any(n.startswith("fake__") for n in names)
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_manager_call_tool(fake_mcp_path: Path):
    if not PYTHON:
        pytest.skip("no python interpreter")
    cfg = McpServerConfig(
        name="fake", transport="stdio",
        command=PYTHON, args=(str(fake_mcp_path),),
    )
    mgr = McpManager([cfg])
    await mgr.connect_all()
    try:
        # 查找带前缀的echo工具
        tools = mgr.all_tools()
        echo_spec = next(t for t in tools if t.name.endswith("echo"))
        result = await mgr.call_tool(echo_spec.name, {"text": "hello"})
        assert "hello" in result
    finally:
        await mgr.shutdown()