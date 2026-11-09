"""Lumos异常层级。"""
from __future__ import annotations


class LumosError(Exception):
    """所有Lumos异常的基类。"""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ProviderError(LumosError):
    """LLM Provider错误。"""
    retryable: bool = False

    def __init__(
        self,
        message: str = "",
        *,
        retryable: bool = False,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.retryable = retryable


class ToolExecutionError(LumosError):
    """工具执行失败。"""

    def __init__(
        self,
        message: str = "",
        *,
        tool_name: str = "",
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.tool_name = tool_name


class McpConnectionError(LumosError):
    """MCP连接错误。"""


class CancelledError(LumosError):
    """用户取消。"""


class MaxStepsExceededError(LumosError):
    """Agent超过最大步数。"""


class ContextLengthExceededError(ProviderError):
    """上下文超限。"""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message, retryable=False, cause=cause)


class KnowledgeBaseError(LumosError):
    """知识库相关错误的基类。"""


class KnowledgeBaseNotFoundError(KnowledgeBaseError):
    """知识库不存在。"""


class KnowledgeBaseAlreadyExistsError(KnowledgeBaseError):
    """同名知识库已存在。"""


class KnowledgeDocumentNotFoundError(KnowledgeBaseError):
    """文档不存在。"""


class DocumentParseError(KnowledgeBaseError):
    """文档解析失败。"""


class DocumentTooLargeError(KnowledgeBaseError):
    """文档超过大小限制。"""


class UnsupportedMimeTypeError(KnowledgeBaseError):
    """不支持的 MIME 类型。"""


class VectorServiceUnavailableError(KnowledgeBaseError):
    """vector-service 不可用。"""


class IndexingJobError(KnowledgeBaseError):
    """索引任务执行失败。"""