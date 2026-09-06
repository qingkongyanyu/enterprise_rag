"""向量存储：原生 FAISS IndexFlatIP（内积 = 归一化后的余弦相似度）。

- 单例常驻内存，避免 LangChain 版"每次请求重新 load_local"的性能问题。
- 持久化：faiss 二进制索引 + chunks JSON 元数据。
- 检索返回余弦相似度（越高越相关）。
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from app.models.domain import Chunk

logger = logging.getLogger(__name__)

CHUNKS_FILENAME = "chunks.json"
INDEX_FILENAME = "index.faiss"


def _is_ascii(path: Path) -> bool:
    """路径是否全 ASCII（faiss 在 Windows 上仅能按 ANSI 编码打开文件）。"""
    try:
        str(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _faiss_read_index(index_path: Path):
    """faiss 在 Windows 上按 ANSI 编码打开文件，路径含中文等非 ASCII 字符会报
    "could not open ... for reading"。规避：临时把工作目录切到索引所在目录，
    用相对文件名调用（OS 按 UTF-16 正确解析 cwd），完成后恢复。"""
    if _is_ascii(index_path):
        return faiss.read_index(str(index_path))
    prev = os.getcwd()
    try:
        os.chdir(str(index_path.parent))
        return faiss.read_index(index_path.name)
    finally:
        os.chdir(prev)


def _faiss_write_index(index, index_path: Path) -> None:
    """同 _faiss_read_index：write_index 同样受非 ASCII 路径影响。"""
    if _is_ascii(index_path):
        faiss.write_index(index, str(index_path))
        return
    prev = os.getcwd()
    try:
        os.chdir(str(index_path.parent))
        faiss.write_index(index, index_path.name)
    finally:
        os.chdir(prev)


class VectorStore:
    """FAISS 向量库，chunk 与索引位置一一对应。"""

    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)  # 内积；向量已归一化故等价余弦
        self.chunks: list[Chunk] = []

    # ---------- 写入 ----------
    def add(self, vectors: np.ndarray, chunks: list[Chunk]) -> None:
        if len(vectors) != len(chunks):
            raise ValueError("向量与文档块数量不一致")
        if vectors.size == 0:
            return
        vectors = np.asarray(vectors, dtype=np.float32)
        self.index.add(vectors)
        self.chunks.extend(chunks)

    # ---------- 检索 ----------
    def search(self, query_vec: np.ndarray, top_k: int = 8) -> list[tuple[int, float]]:
        """返回 [(pos, cosine_score)]，按得分降序。"""
        if self.index.ntotal == 0:
            return []
        query_vec = np.asarray(query_vec, dtype=np.float32).reshape(1, -1)
        k = min(top_k, self.index.ntotal)
        scores, positions = self.index.search(query_vec, k)
        return [(int(pos), float(score)) for pos, score in zip(positions[0], scores[0])]

    # ---------- 统计 ----------
    @property
    def count(self) -> int:
        return self.index.ntotal

    def chunk_by_pos(self, pos: int) -> Optional[Chunk]:
        return self.chunks[pos] if 0 <= pos < len(self.chunks) else None

    # ---------- 持久化 ----------
    def persist(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        _faiss_write_index(self.index, directory / INDEX_FILENAME)
        with open(directory / CHUNKS_FILENAME, "w", encoding="utf-8") as f:
            json.dump([self._chunk_to_dict(c) for c in self.chunks], f, ensure_ascii=False)
        logger.info("💾 向量库已持久化：%s，共 %d 块", directory, self.count)

    @classmethod
    def load(cls, directory: Path) -> Optional["VectorStore"]:
        """从磁盘加载；缺失或损坏返回 None。"""
        index_file = directory / INDEX_FILENAME
        chunks_file = directory / CHUNKS_FILENAME
        if not index_file.exists() or not chunks_file.exists():
            return None
        try:
            index = _faiss_read_index(index_file)
            with open(chunks_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            store = cls(index.d)
            store.index = index
            store.chunks = [cls._chunk_from_dict(d) for d in raw]
            logger.info("📂 向量库加载成功：%d 块，维度 %d", store.count, store.dim)
            return store
        except Exception as e:
            logger.error("向量库加载失败（可重建）: %s", e)
            return None

    @staticmethod
    def _chunk_to_dict(c: Chunk) -> dict:
        return {"id": c.id, "content": c.content, "source": c.source,
                "category": c.category, "metadata": c.metadata}

    @staticmethod
    def _chunk_from_dict(d: dict) -> Chunk:
        return Chunk(
            id=d["id"], content=d["content"], source=d.get("source", ""),
            category=d.get("category", "未分类"), metadata=d.get("metadata", {}),
        )
