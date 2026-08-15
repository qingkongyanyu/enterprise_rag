"""业务异常定义。

约定：所有能被 HTTP 层直接映射为响应的异常，放在这里。
API 层通过统一的 exception handler 捕获并转成 {code, message, data} 结构。
"""
from __future__ import annotations


class AppError(Exception):
    """业务异常基类。"""

    status_code: int = 400
    code: str = "APP_ERROR"
    default_message: str = "请求处理失败"

    def __init__(self, message: str | None = None, *, status_code: int | None = None):
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    default_message = "资源不存在"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    default_message = "参数校验失败"


class KnowledgeBaseNotReadyError(AppError):
    """向量索引未构建。"""

    status_code = 503
    code = "KNOWLEDGE_NOT_READY"
    default_message = "知识库索引未初始化，请先构建向量索引"


class LLMNotConfiguredError(AppError):
    """LLM 配置缺失/无效。"""

    status_code = 503
    code = "LLM_NOT_CONFIGURED"
    default_message = "大模型服务未配置，请检查 .env 中的 LLM_API_KEY"


class LLMRequestError(AppError):
    """上游 LLM 调用失败。"""

    status_code = 502
    code = "LLM_REQUEST_FAILED"
    default_message = "大模型调用失败，请稍后重试"


class EmptyQuestionError(ValidationError):
    default_message = "问题不能为空"
    code = "EMPTY_QUESTION"


class DuplicateDocumentError(AppError):
    status_code = 409
    code = "DUPLICATE_DOCUMENT"
    default_message = "同名文档已存在"


class DocumentNotFoundError(NotFoundError):
    default_message = "文档不存在"
    code = "DOCUMENT_NOT_FOUND"
