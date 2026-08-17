"""RAG 编排管道：检索 → 组装上下文 → 生成（支持流式）→ 记忆 → 缓存。

RAG 调优在本层的体现：
- 无命中短路：检索为空时不调用 LLM，直接返回兜底语（省钱省时）。
- 引用溯源：每个块带编号，Prompt 要求回答标注 [n]，前端可展示来源。
- 会话记忆：注入最近 N 轮历史，支持多轮追问。
- 响应缓存：相同问题（且无历史上下文）命中时直接返回，减少 LLM 调用。
"""
from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from app.core.config import Settings
from app.core.exceptions import EmptyQuestionError
from app.models.domain import RetrievedChunk
from app.models.schemas import ChatData, SourceDoc
from app.services.knowledge import KnowledgeBase
from app.services.llm import LLMClient
from app.services.memory import MemoryStore
from app.utils.cache import TTLCache
from app.utils.text import truncate_by_tokens

logger = logging.getLogger(__name__)

SYSTEM_TEMPLATE = """你是「知知」，一家企业的私有知识库智能问答助手，负责回答员工关于公司制度、流程、产品与业务的问题。

## 硬性规则
1. 只能依据下方【检索资料】作答，严禁使用资料之外的知识编造答案。
2. 资料足以回答时：直接、简洁、有条理地作答，并在关键结论句末标注引用编号，如 [1]、[2]。此时不要再提"未找到资料"之类的话。
3. 只有当资料确实不足以支撑问题时：明确回复「当前知识库中未找到与该问题直接相关的资料」，并附上最接近的资料提示，绝不强行编造。
4. 涉及流程/制度类问题：按「流程步骤 → 条件 → 注意事项」的结构作答，方便员工照做。
5. 全部使用中文。回答末尾用一句话给出核心结论。

## 检索资料
{context}

## 对话历史
{history}

## 作答
请开始回答用户的问题。"""

NO_GROUNDED_REPLY = "抱歉，当前知识库中未找到与该问题相关的资料。您可以换个表述方式，或先到「知识库管理」确认文档已构建索引。"


class RAGPipeline:
    def __init__(
        self,
        knowledge: KnowledgeBase,
        llm: LLMClient,
        memory: MemoryStore,
        settings: Settings,
    ):
        self.knowledge = knowledge
        self.llm = llm
        self.memory = memory
        self.settings = settings
        self._cache: TTLCache[ChatData] = TTLCache(
            max_size=settings.response_cache_size,
            ttl_seconds=settings.response_cache_ttl,
        )
        # 轻量指标（供 /system/stats 展示）
        self._metrics = {"chat_count": 0, "total_elapsed_ms": 0, "cache_hits": 0}

    # ================= 核心：非流式 =================
    def answer(self, question: str, session_id: Optional[str]) -> ChatData:
        question = (question or "").strip()
        if not question:
            raise EmptyQuestionError()

        session_id = session_id or self.memory.new_session_id()
        history_prompt = self.memory.build_history_prompt(session_id)

        # 无历史上下文时启用响应缓存（有历史则结果因人而异，不缓存）
        # 注意：命中缓存时用当前 session_id 重建返回对象，避免串号
        cache_key = f"{question}||{history_prompt == ''}"
        if not history_prompt:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._metrics["cache_hits"] += 1
                return cached.model_copy(update={"session_id": session_id})

        t0 = time.monotonic()
        retriever = self.knowledge.get_retriever()
        retrieved = retriever.retrieve(
            question,
            dense_top_k=self.settings.dense_top_k,
            sparse_top_k=self.settings.sparse_top_k,
            final_top_k=self.settings.final_top_k,
            reranker=self.knowledge.get_reranker(),
        )

        # 无命中短路（不调用 LLM）
        if not retrieved:
            answer_text = NO_GROUNDED_REPLY
            grounded = False
            sources: list[SourceDoc] = []
        else:
            context = self._format_context(retrieved)
            messages = self._build_messages(question, context, history_prompt)
            answer_text = self.llm.chat(messages)
            answer_text = (answer_text or "").strip()
            grounded = True
            sources = self._to_sources(retrieved)

        elapsed = int((time.monotonic() - t0) * 1000)
        data = ChatData(
            answer=answer_text or "（模型未返回有效内容）",
            session_id=session_id,
            sources=sources,
            elapsed_ms=elapsed,
            grounded=grounded,
        )

        # 记忆 + 缓存（仅 grounded 命中才缓存；无命中兜底语不缓存，
        # 否则后续上传文档后同问题仍会命中旧兜底）
        self.memory.add_turn(
            session_id, question, data.answer,
            sources=[s.model_dump() for s in sources],
        )
        if grounded and not history_prompt:
            self._cache.put(cache_key, data)

        self._metrics["chat_count"] += 1
        self._metrics["total_elapsed_ms"] += elapsed
        return data

    # ================= 核心：流式 =================
    def stream_answer(self, question: str, session_id: Optional[str]) -> Iterator[dict]:
        """SSE 事件生成器。事件结构：{"type": "meta"|"delta"|"sources"|"done"|"error", ...}"""
        question = (question or "").strip()
        if not question:
            yield {"type": "error", "message": "问题不能为空"}
            return

        session_id = session_id or self.memory.new_session_id()
        history_prompt = self.memory.build_history_prompt(session_id)
        yield {"type": "meta", "session_id": session_id}

        t0 = time.monotonic()
        try:
            retriever = self.knowledge.get_retriever()
            retrieved = retriever.retrieve(
                question,
                dense_top_k=self.settings.dense_top_k,
                sparse_top_k=self.settings.sparse_top_k,
                final_top_k=self.settings.final_top_k,
                reranker=self.knowledge.get_reranker(),
            )

            sources: list[SourceDoc] = []
            if not retrieved:
                yield {"type": "delta", "text": NO_GROUNDED_REPLY}
                yield {"type": "sources", "sources": []}
                answer_text = NO_GROUNDED_REPLY
                grounded = False
            else:
                context = self._format_context(retrieved)
                messages = self._build_messages(question, context, history_prompt)
                answer_parts: list[str] = []
                for text_chunk in self.llm.stream_chat(messages):
                    if text_chunk:
                        answer_parts.append(text_chunk)
                        yield {"type": "delta", "text": text_chunk}
                answer_text = "".join(answer_parts).strip()
                sources = self._to_sources(retrieved)
                yield {"type": "sources", "sources": [s.model_dump() for s in sources]}
                grounded = True

            elapsed = int((time.monotonic() - t0) * 1000)
            self.memory.add_turn(
                session_id, question,
                answer_text or "（模型未返回有效内容）",
                sources=[s.model_dump() for s in sources] if grounded else [],
            )
            self._metrics["chat_count"] += 1
            self._metrics["total_elapsed_ms"] += elapsed
            yield {"type": "done", "elapsed_ms": elapsed}

        except Exception as e:
            logger.exception("流式问答异常")
            yield {"type": "error", "message": str(e)}

    # ================= 辅助 =================
    def _format_context(self, retrieved: list[RetrievedChunk]) -> str:
        parts = []
        for r in retrieved:
            c = r.chunk
            title = c.metadata.get("title") or ""
            header = f"[{r.rank}] 来源：{c.source}" + (f"（{title}）" if title else "")
            parts.append(f"{header}\n{c.content}")
        context = "\n\n".join(parts)
        # 按 token 预算裁剪，防止超长
        return truncate_by_tokens(context, max_tokens=2800)

    def _build_messages(self, question: str, context: str, history_prompt: str) -> list[dict]:
        system = SYSTEM_TEMPLATE.format(
            context=context,
            history=history_prompt or "（无）",
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]

    @staticmethod
    def _to_sources(retrieved: list[RetrievedChunk]) -> list[SourceDoc]:
        return [
            SourceDoc(
                source=r.chunk.source,
                chunk_id=r.chunk.id,
                score=r.score,
                snippet=r.chunk.content[:120],
                rank=r.rank,
            )
            for r in retrieved
        ]

    def get_metrics(self) -> dict:
        m = dict(self._metrics)
        avg = int(m["total_elapsed_ms"] / m["chat_count"]) if m["chat_count"] else 0
        m["avg_elapsed_ms"] = avg
        return m
