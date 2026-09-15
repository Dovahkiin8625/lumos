"""测试MCP传输（stdio用真子进程，SSE/HTTP用mock）。"""
from __future__ import annotations
import asyncio
import json
import pytest
from lumos.mcp.transports.stdio import StdioTransport
from lumos.mcp.transports.sse import SseTransport
from lumos.mcp.transports.streamable_http import StreamableHttpTransport


@pytest.mark.asyncio
async def test_stdio_transport_echo():
    """用python作为stdio MCP服务器做echo测试。"""
    transport = StdioTransport(
        command="python",
        args=["-c", (
            "import sys, json\n"
            "for line in sys.stdin:\n"
            "    msg = json.loads(line)\n"
            "    if msg.get('method') == 'ping':\n"
            "        resp = {'jsonrpc': '2.0', 'id': msg['id'], 'result': 'pong'}\n"
            "        print(json.dumps(resp), flush=True)\n"
        )],
        env={},
    )
    await transport.start()
    try:
        await transport.write_message({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        # 等待响应
        response = await asyncio.wait_for(transport.read_message(), timeout=5.0)
        assert response["result"] == "pong"
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_sse_transport_send_receive(respx_mock):
    """SSE transport: 客户端GET SSE流，POST发送消息。"""
    import respx
    import httpx

    sse_body = (
        "event: endpoint\ndata: /post_endpoint\n\n"
        "data: {\"jsonrpc\":\"2.0\",\"id\":1,\"result\":\"ok\"}\n\n"
    )

    async def sse_handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_body,
        )

    respx_mock.get("https://mcp.test/sse").mock(side_effect=sse_handler)

    transport = SseTransport(
        url="https://mcp.test/sse", headers={},
    )
    await transport.start()
    try:
        # 应能从SSE读到一个JSON-RPC响应
        msg = await asyncio.wait_for(transport.read_message(), timeout=5.0)
        assert msg["result"] == "ok"
    finally:
        await transport.close()