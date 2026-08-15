"""混合检索：稠密（FAISS 余弦） + 稀疏（BM25） → 倒数排名融合（RRF）。

单一检索方式的短板：
- 纯向量：对精确编号/人名/术语召回弱；
- 纯 BM25：对同义改写、语义相关召回弱。
RRF 将两者排名融合，取长补短，是轻量而有效的 RAG 召回优化。
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from app.models.domain import Chunk, RetrievedChunk
from app.services.bm25 import BM25Index
from app.services.embeddings import EmbeddingService
from app.services.reranker import Reranker
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        bm25: BM25Index,
        embedder: EmbeddingService,
        *,
        rrf_k: int = 60,
    ):
        self.vector_store = vector_store
        self.bm25 = bm25
        self.embedder = embedder
        self.rrf_k = rrf_k

    # ---------- 核心检索 ----------
    def retrieve(
        self,
        query: str,
        *,
        dense_top_k: int = 8,
        sparse_top_k: int = 8,
        final_top_k: int = 5,
        reranker: Optional[Reranker] = None,
    ) -> list[RetrievedChunk]:
        if self.vector_store.count == 0:
            return []

        # 1. 稠密检索
        query_vec = self.embedder.embed_query(query)
        dense_hits = self.vector_store.search(query_vec, top_k=dense_top_k)

        # 2. 稀疏检索
        sparse_hits = self.bm25.search(query, top_k=sparse_top_k)

        # 3. RRF 融合（1 基排名）
        fused: dict[int, float] = {}
        for pos, _ in dense_hits:
            fused[pos] = fused.get(pos, 0.0) + 1.0 / (self.rrf_k + 1)
        for pos, _ in sparse_hits:
            fused[pos] = fused.get(pos, 0.0) + 1.0 / (self.rrf_k + 1)

        # 4. 组装候选
        candidates: list[tuple[Chunk, float]] = []
        seen_ids: set[str] = set()
        for pos, score in sorted(fused.items(), key=lambda x: x[1], reverse=True):
            chunk = self.vector_store.chunk_by_pos(pos)
            if chunk is None or chunk.id in seen_ids:
                continue
            seen_ids.add(chunk.id)
            candidates.append((chunk, score))

        # 5. 可选重排
        if reranker is not None and len(candidates) > 1:
            candidates = reranker.rerank(query, candidates)

        # 6. 归一化得分并返回
        max_score = max((s for _, s in candidates), default=1.0) or 1.0
        results = [
            RetrievedChunk(chunk=c, score=round(s / max_score, 4), rank=i + 1)
            for i, (c, s) in enumerate(candidates[:final_top_k])
        ]
        logger.debug("检索完成：%d 候选 → 最终 %d 块", len(candidates), len(results))
        return results

    # ---------- 仅稠密（对比用 / 调试） ----------
    def dense_only(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        query_vec = self.embedder.embed_query(query)
        hits = self.vector_store.search(query_vec, top_k=top_k)
        results = []
        for pos, score in hits:
            chunk = self.vector_store.chunk_by_pos(pos)
            if chunk is None:
                continue
            results.append(RetrievedChunk(chunk=chunk, score=float(score), rank=len(results) + 1))
        return results
