"""服务容器与依赖注入。

- `ServiceRegistry`：把所有单例服务收拢到一个对象，挂在 app.state.services 上。
- `build_services()`：应用生命周期内构建（含启动时尝试加载已持久化索引）。
- `get_services(request)`：路由内取用。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request

from app.core.config import Settings, ensure_data_directories, get_settings
from app.services.knowledge import KnowledgeBase
from app.services.llm import LLMClient
from app.services.memory import MemoryStore
from app.services.pipeline import RAGPipeline


@dataclass
class ServiceRegistry:
    settings: Settings
    knowledge: KnowledgeBase
    memory: MemoryStore
    llm: LLMClient
    pipeline: RAGPipeline


def build_services(settings: Optional[Settings] = None) -> ServiceRegistry:
    """构建完整的服务容器（含启动时加载索引）。"""
    settings = settings or get_settings()
    ensure_data_directories()

    knowledge = KnowledgeBase(settings)
    memory = MemoryStore(settings)
    llm = LLMClient(settings)
    pipeline = RAGPipeline(knowledge, llm, memory, settings)

    # 尝试加载磁盘上已有的索引（若不存在则等待前端触发构建）
    if not knowledge.load_from_disk():
        from app.core.logging import get_logger

        get_logger(__name__).warning(
            "未发现已持久化的向量索引，请通过前端「构建索引」或运行 "
            "backend/scripts/init_knowledge.py 初始化知识库"
        )

    return ServiceRegistry(
        settings=settings,
        knowledge=knowledge,
        memory=memory,
        llm=llm,
        pipeline=pipeline,
    )


def get_services(request: Request) -> ServiceRegistry:
    """从请求中取服务容器。"""
    return request.app.state.services
