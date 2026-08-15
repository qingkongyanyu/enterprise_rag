"""LLM 客户端：OpenAI 兼容接口抽象。

通过 base_url 一个参数即可对接任意 OpenAI 兼容服务：
  - 阿里云百炼（通义千问）  https://dashscope.aliyuncs.com/compatible-mode/v1
  - OpenAI                   https://api.openai.com/v1
  - 本地 Ollama              http://localhost:11434/v1
  - 火山方舟（豆包）         https://ark.cn-beijing.volces.com/api/v3

使用 openai SDK 统一调用；异常按类型映射为可读的业务异常。
"""
from __future__ import annotations

import logging
from typing import Iterator, Optional

from app.core.config import Settings
from app.core.exceptions import LLMNotConfiguredError, LLMRequestError

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = None

    # ---------- 客户端 ----------
    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self._settings.llm_configured:
            raise LLMNotConfiguredError(
                "大模型服务未配置：请复制 .env.example 为 backend/.env，并填写 LLM_API_KEY"
            )
        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self._settings.llm_base_url,
                api_key=self._settings.llm_api_key,
                timeout=self._settings.llm_timeout,
                max_retries=1,
            )
        except Exception as e:
            raise LLMRequestError(f"LLM 客户端初始化失败: {e}") from e
        return self._client

    # ---------- 非流式 ----------
    def chat(
        self,
        messages: list[dict],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        client = self._ensure_client()
        try:
            resp = client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,
                temperature=temperature if temperature is not None else self._settings.llm_temperature,
                max_tokens=max_tokens or self._settings.llm_max_tokens,
                stream=False,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            self._raise_mapped(e)

    # ---------- 流式 ----------
    def stream_chat(
        self,
        messages: list[dict],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """逐 token 产出文本片段。"""
        client = self._ensure_client()
        try:
            stream = client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,
                temperature=temperature if temperature is not None else self._settings.llm_temperature,
                max_tokens=max_tokens or self._settings.llm_max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as e:
            self._raise_mapped(e)

    # ---------- 异常映射 ----------
    def _raise_mapped(self, exc: Exception):
        logger.error("LLM 调用异常: %s", exc, exc_info=True)
        exc_name = type(exc).__name__.lower()
        if "authentication" in exc_name or "auth" in exc_name:
            raise LLMNotConfiguredError(
                f"LLM 鉴权失败（请检查 LLM_API_KEY）: {exc}"
            ) from exc
        if "timeout" in exc_name or "connection" in exc_name:
            raise LLMRequestError(f"LLM 连接超时或失败: {exc}") from exc
        # OpenAI SDK 的 APIStatusError 等
        status = getattr(exc, "status_code", None)
        if status:
            raise LLMRequestError(f"LLM 服务返回 {status}: {exc}") from exc
        raise LLMRequestError(f"LLM 调用失败: {exc}") from exc
