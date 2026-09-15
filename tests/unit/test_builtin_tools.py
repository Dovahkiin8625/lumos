"""测试内置工具。"""
from __future__ import annotations
import pytest
from lumos.tools.builtin.datetime import DateTimeTool
from lumos.tools.builtin.calculator import CalculatorTool, _safe_eval
from lumos.tools.builtin.shell import ShellTool
from lumos.tools.builtin.file_ops import FileReadTool, FileWriteTool
from lumos.config import ToolsConfig


@pytest.mark.asyncio
async def test_datetime_default_utc():
    tool = DateTimeTool()
    result = await tool.execute()
    assert "UTC" in result


@pytest.mark.asyncio
async def test_datetime_shanghai():
    tool = DateTimeTool()
    result = await tool.execute(tz="Asia/Shanghai")
    assert "Shanghai" in result or "CST" in result or "+08" in result


def test_calculator_eval():
    assert _safe_eval("1 + 2") == 3
    assert _safe_eval("2 ** 10") == 1024
    assert _safe_eval("(1 + 2) * 3") == 9


def test_calculator_rejects_function_calls():
    with pytest.raises(ValueError):
        _safe_eval("__import__('os').system('rm -rf /')")


@pytest.mark.asyncio
async def test_calculator_tool():
    tool = CalculatorTool()
    result = await tool.execute(expression="(10 + 5) * 2")
    assert result == "30"


@pytest.mark.asyncio
async def test_shell_exec_success():
    tool = ShellTool()
    result = await tool.execute(command="echo hello")
    assert "hello" in result


@pytest.mark.asyncio
async def test_shell_exec_failure():
    from lumos.errors import ToolExecutionError
    tool = ShellTool()
    with pytest.raises(ToolExecutionError):
        await tool.execute(command="exit 1")


@pytest.mark.asyncio
async def test_file_write_and_read(tmp_path):
    cfg = ToolsConfig(allowed_paths=[str(tmp_path)])
    write_tool = FileWriteTool()
    write_tool.config = cfg
    target = tmp_path / "test.txt"
    await write_tool.execute(path=str(target), content="hello world")
    assert target.read_text() == "hello world"

    read_tool = FileReadTool()
    read_tool.config = cfg
    content = await read_tool.execute(path=str(target))
    assert content == "hello world"


@pytest.mark.asyncio
async def test_file_read_path_blocked(tmp_path):
    from lumos.errors import ToolExecutionError
    cfg = ToolsConfig(allowed_paths=[str(tmp_path)])
    tool = FileReadTool()
    tool.config = cfg
    with pytest.raises(ToolExecutionError, match="not allowed"):
        await tool.execute(path="/etc/passwd")


@pytest.mark.asyncio
async def test_http_request_real(respx_mock):
    import respx
    import httpx
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    from lumos.tools.builtin.http_request import HttpRequestTool
    tool = HttpRequestTool()
    result = await tool.execute(url="https://example.com/api", method="GET")
    assert "200" in result
    assert '"ok":true' in result