"""测试异常层级。"""
from __future__ import annotations
import pytest
from lumos.errors import (
    LumosError, ProviderError, ToolExecutionError,
    McpConnectionError, CancelledError, MaxStepsExceededError,
    ContextLengthExceededError,
)


def test_provider_error_retryable():
    e = ProviderError("rate limit", retryable=True)
    assert e.retryable is True
    assert isinstance(e, LumosError)


def test_context_length_exceeded_is_provider_error():
    e = ContextLengthExceededError("too long")
    assert isinstance(e, ProviderError)
    assert e.retryable is False


def test_tool_error_carries_name():
    e = ToolExecutionError("failed", tool_name="web_search")
    assert e.tool_name == "web_search"


def test_cancelled_error_inherits():
    e = CancelledError("user cancelled")
    assert isinstance(e, LumosError)