"""知识库服务门面：索引构建、加载、检索器管理、统计。

负责把「文档 → 分块 → 嵌入 → FAISS+BM25 → 混合检索器」整个生命周期收拢起来，
并提供线程安全的引用切换（重建索引时旧检索器仍可继续服务）。
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from app.core.config import KNOWLEDGE_DOCS_DIR, VECTOR_STORE_DIR, Settings
from app.core.exceptions import DocumentNotFoundError, KnowledgeBaseNotReadyError
from app.models.domain import Chunk
from app.models.schemas import KnowledgeOverview, RebuildResult
from app.services import document_loader as docs
from app.services.bm25 import BM25Index
from app.services.chunking import chunk_documents
from app.services.embeddings import EmbeddingService
from app.services.reranker import Reranker
from app.services.retriever import HybridRetriever
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(
        self,
        settings: Settings,
        embedder: Optional[EmbeddingService] = None,
        *,
        docs_dir: Path = KNOWLEDGE_DOCS_DIR,
        store_dir: Path = VECTOR_STORE_DIR,
    ):
        self.settings = settings
        self.docs_dir = docs_dir
        self.store_dir = store_dir
        self.embedder = embedder or EmbeddingService(settings)
        self._lock = threading.RLock()
        self._retriever: Optional[HybridRetriever] = None
        self._reranker: Optional[Reranker] = None
        self._build_meta: dict = {}

    # ---------- 状态 ----------
    @property
    def is_ready(self) -> bool:
        return self._retriever is not None

    def get_retriever(self) -> HybridRetriever:
        with self._lock:
            if self._retriever is None:
                raise KnowledgeBaseNotReadyError(
                    "知识库索引未构建。请先到「知识库管理」页点击「构建索引」，"
                    "或执行 backend/scripts/init_knowledge.py"
                )
            return self._retriever

    # ---------- 加载（启动时） ----------
    def load_from_disk(self) -> bool:
        """尝试从磁盘加载已持久化的索引。成功返回 True。"""
        store = VectorStore.load(self.store_dir)
        if store is None or store.count == 0:
            return False
        bm25 = BM25Index.from_texts([c.content for c in store.chunks])
        with self._lock:
            self._retriever = HybridRetriever(
                store, bm25, self.embedder, rrf_k=self.settings.rrf_k
            )
        self._build_meta = {
            "doc_count": len({c.source for c in store.chunks}),
            "chunk_count": store.count,
            "loaded_from_disk": True,
        }
        logger.info("📂 已从磁盘加载知识库索引（%d 块）", store.count)
        return True

    # ---------- 构建 ----------
    def rebuild(self) -> RebuildResult:
        """全量重建索引：读文档 → 分块 → 嵌入（带缓存）→ 建库 → 持久化 → 热切换。"""
        t0 = time.monotonic()
        raw_docs = docs.read_all_docs(self.docs_dir)
        if not raw_docs:
            raise DocumentNotFoundError("知识库目录中没有可索引的文档")

        chunks = chunk_documents(
            raw_docs,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        if not chunks:
            raise DocumentNotFoundError("文档分块结果为空，请检查文档内容")

        # 嵌入（缓存命中的部分不重复计算）
        cached = self.embedder.count_cached([c.content for c in chunks])
        vectors = self.embedder.embed_documents([c.content for c in chunks])

        store = VectorStore(vectors.shape[1])
        store.add(vectors, chunks)
        bm25 = BM25Index.from_texts([c.content for c in chunks])
        retriever = HybridRetriever(store, bm25, self.embedder, rrf_k=self.settings.rrf_k)

        # 持久化
        store.persist(self.store_dir)

        # 热切换：先建好再原子替换引用
        with self._lock:
            self._retriever = retriever

        elapsed = int((time.monotonic() - t0) * 1000)
        self._build_meta = {
            "doc_count": len({c.source for c in chunks}),
            "chunk_count": len(chunks),
            "elapsed_ms": elapsed,
            "cached_chunks": cached,
            "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        logger.info("✅ 索引构建完成：%d 文档 → %d 块，耗时 %dms（缓存命中 %d）",
                    self._build_meta["doc_count"], len(chunks), elapsed, cached)
        return RebuildResult(
            doc_count=self._build_meta["doc_count"],
            chunk_count=len(chunks),
            elapsed_ms=elapsed,
            cached_chunks=cached,
        )

    # ---------- 文档管理 ----------
    def upload_document(self, filename: str, content: bytes | str) -> dict:
        path = docs.save_doc(self.docs_dir, filename, content)
        # 上传后增量重建索引（保持检索一致）
        self.rebuild()
        return {"name": path.name, "path": str(path)}

    def delete_document(self, filename: str) -> None:
        if not docs.delete_doc(self.docs_dir, filename):
            raise DocumentNotFoundError(f"文档不存在：{filename}")

        remaining = docs.read_all_docs(self.docs_dir)
        if remaining:
            self.rebuild()  # 删除后同步索引
        else:
            # 全部删空：清空检索器（不再尝试重建，避免报错）
            with self._lock:
                self._retriever = None
            self._build_meta = {}
        logger.info("🗑️ 已删除文档：%s", filename)

    # ---------- 统计 ----------
    def overview(self) -> KnowledgeOverview:
        doc_infos = docs.list_docs(self.docs_dir)
        chunk_count = 0
        categories: dict[str, int] = {}
        if self._retriever is not None:
            store = self._retriever.vector_store
            chunk_count = store.count
            for c in store.chunks:
                categories[c.category] = categories.get(c.category, 0) + 1
        else:
            for d in doc_infos:
                categories[d.category] = categories.get(d.category, 0) + 1
        return KnowledgeOverview(
            ready=self.is_ready,
            total_docs=len(doc_infos),
            total_chunks=chunk_count,
            categories=categories,
            docs=doc_infos,
        )

    def get_build_meta(self) -> dict:
        return dict(self._build_meta)

    def get_reranker(self) -> Optional[Reranker]:
        """惰性创建重排器（仅当配置开启）。加载失败会内部降级。"""
        if not self.settings.enable_rerank:
            return None
        if self._reranker is None:
            self._reranker = Reranker(
                self.settings.rerank_model,
                device=self.settings.embedding_device,
                top_n=self.settings.rerank_top_n,
            )
        return self._reranker

    # ---------- 调试辅助 ----------
    def search_debug(self, query: str, top_k: int = 5) -> list[Chunk]:
        """仅供调试/文档演示：返回命中的原始块。"""
        retriever = self.get_retriever()
        return [r.chunk for r in retriever.retrieve(
            query,
            dense_top_k=self.settings.dense_top_k,
            sparse_top_k=self.settings.sparse_top_k,
            final_top_k=top_k,
            reranker=self.get_reranker(),
        )]
