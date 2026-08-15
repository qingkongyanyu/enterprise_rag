"""pytest 公共 fixtures。

测试策略：不依赖真实嵌入模型与真实 LLM，用确定性替身注入，
保证测试快速、可复现、无网络依赖。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试可以从 backend/ 下任意位置运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.deps import ServiceRegistry  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.services.knowledge import KnowledgeBase  # noqa: E402
from app.services.memory import MemoryStore  # noqa: E402
from app.services.pipeline import RAGPipeline  # noqa: E402


class FakeEmbedder:
    """基于字符哈希的确定性嵌入：共享字符越多，向量越相似。"""

    def __init__(self, dim: int = 8):
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for ch in (text or ""):
            if ch == " ":
                continue
            v[ord(ch) % self.dim] += 1.0
        norm = np.linalg.norm(v)
        return v / norm if norm else v

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._vec(t) for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._vec(text)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._vec(t) for t in texts])

    def count_cached(self, texts: list[str]) -> int:
        return 0  # 测试替身：无磁盘缓存


class FakeLLM:
    def __init__(self, answer: str = "这是模拟回答。"):
        self.answer = answer

    def chat(self, messages: list[dict], **kwargs) -> str:
        return self.answer

    def stream_chat(self, messages: list[dict], **kwargs):
        for ch in self.answer:
            yield ch


@pytest.fixture()
def tmp_dirs(tmp_path: Path) -> dict:
    dirs = {
        "docs": tmp_path / "knowledge_docs",
        "store": tmp_path / "vector_store",
        "memory": tmp_path / "chat_memory",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


@pytest.fixture()
def settings(tmp_dirs) -> Settings:
    return Settings(
        chunk_size=120,
        chunk_overlap=20,
        dense_top_k=3,
        sparse_top_k=3,
        final_top_k=2,
        max_history_turns=4,
        enable_rerank=False,
    )


@pytest.fixture()
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture()
def services(tmp_dirs, settings, fake_embedder) -> ServiceRegistry:
    knowledge = KnowledgeBase(
        settings,
        embedder=fake_embedder,
        docs_dir=tmp_dirs["docs"],
        store_dir=tmp_dirs["store"],
    )
    memory = MemoryStore(settings, directory=tmp_dirs["memory"])
    llm = FakeLLM()
    pipeline = RAGPipeline(knowledge, llm, memory, settings)
    return ServiceRegistry(
        settings=settings,
        knowledge=knowledge,
        memory=memory,
        llm=llm,
        pipeline=pipeline,
    )


@pytest.fixture()
def sample_docs(tmp_dirs) -> None:
    """写入三份不同主题的测试文档。"""
    (tmp_dirs["docs"] / "人事_01.txt").write_text(
        "员工请假制度：员工因私事可申请事假，须提前1个工作日提交请假申请单，"
        "由直属领导审批后交人力资源部备案。连续请假超过5个工作日需经总经理审批。",
        encoding="utf-8",
    )
    (tmp_dirs["docs"] / "财务_01.txt").write_text(
        "费用报销制度：差旅住宿标准为一线城市500元每晚，二线城市350元每晚。"
        "报销须填写费用报销单并附合规发票，财务部审核通过后3个工作日内完成付款。",
        encoding="utf-8",
    )
    (tmp_dirs["docs"] / "技术_01.txt").write_text(
        "开发规范：后端使用 Python 3.10+，代码命名采用驼峰命名法，"
        "禁止使用魔法数字，异常处理须捕获具体异常类型。",
        encoding="utf-8",
    )
