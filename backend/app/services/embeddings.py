"""嵌入服务：sentence-transformers + 磁盘缓存。

要点：
- 模型懒加载、单例常驻，避免每次请求重复加载（性能关键）。
- 向量归一化，配合 FAISS IndexFlatIP 实现余弦相似度。
- bge 系列中文模型：查询侧加官方推荐指令前缀，提升检索效果。
- 嵌入结果按内容 hash 落盘缓存，重建索引时不重复计算。
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

from app.core.config import EMBEDDING_CACHE_DIR, Settings
from app.utils.cache import EmbeddingDiskCache
from app.utils.text import normalize_text

logger = logging.getLogger(__name__)

# bge 中文模型官方推荐：查询指令前缀（仅用于查询侧，不用于文档侧）
_BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


class EmbeddingService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = None
        self._lock = threading.Lock()
        self._cache = EmbeddingDiskCache(EMBEDDING_CACHE_DIR)

    # ---------- 模型加载（懒加载 + 单例） ----------
    def _ensure_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:  # double-checked
                return self._model
            from sentence_transformers import SentenceTransformer

            logger.info("🔄 正在加载嵌入模型: %s (device=%s)", self._settings.embedding_model,
                        self._settings.embedding_device)
            self._model = SentenceTransformer(
                self._settings.embedding_model,
                device=self._settings.embedding_device,
            )
            logger.info("✅ 嵌入模型加载完成: %s", self._settings.embedding_model)
            return self._model

    # ---------- 编码 ----------
    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """编码文档（批量、带磁盘缓存），返回归一化向量矩阵 (n, dim)。"""
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        normalized = [normalize_text(t) for t in texts]
        missing, _ = self._cache.batch_lookup(normalized)
        if missing:
            # 计算缺失部分（_encode_fresh 内部会写回磁盘缓存）
            self._encode_fresh(missing, is_query=False)

        # 全部命中缓存后，按输入顺序取回（保证返回顺序与 texts 一致）
        vectors = [self._cache.lookup(t) for t in normalized]
        vectors = [v for v in vectors if v is not None]  # 防御性：确保都有值
        return _normalize_rows(np.vstack(vectors).astype(np.float32))

    def embed_query(self, text: str) -> np.ndarray:
        """编码单条查询，返回 (dim,) 归一化向量。"""
        return self.embed_queries([text])[0]

    def count_cached(self, texts: list[str]) -> int:
        """统计有多少文本命中磁盘嵌入缓存（用于构建统计，不触发计算）。"""
        if not texts:
            return 0
        return sum(1 for t in texts if self._cache.lookup(normalize_text(t)) is not None)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        """编码查询（bge 模型加指令前缀，不做缓存，避免污染文档缓存）。"""
        prepared = []
        for t in texts:
            base = normalize_text(t)
            prepared.append(f"{_BGE_QUERY_PREFIX}{base}" if _uses_bge(self._settings.embedding_model) else base)
        return _normalize_rows(self._encode_fresh(prepared, is_query=True))

    def _encode_fresh(self, texts: list[str], is_query: bool) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        model = self._ensure_model()
        # 小批量，避免超长文本溢出（bge-small-zh 支持 512 token）
        all_vecs = []
        bs = self._settings.embedding_batch_size
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            vecs = model.encode(batch, convert_to_numpy=True, normalize_embeddings=True)
            all_vecs.append(np.asarray(vecs, dtype=np.float32))
        out = np.concatenate(all_vecs, axis=0)
        # 文档侧落盘缓存（查询侧不做，避免指令前缀垃圾缓存）
        if not is_query:
            for t, v in zip(texts, out):
                self._cache.store(t, v)
        return out


# -------------------- 辅助 --------------------
def _uses_bge(model_name: str) -> bool:
    return "bge" in model_name.lower()


def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)
