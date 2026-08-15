"""轻量缓存工具。

1. `EmbeddingDiskCache`：基于内容 hash 的磁盘嵌入缓存，重建索引时避免重复计算。
2. `TTLCache`：进程内 LRU + TTL 缓存（用于响应命中缓存）。
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Generic, Iterable, Optional, TypeVar

import numpy as np

logger = logging.getLogger(__name__)

V = TypeVar("V")


class EmbeddingDiskCache:
    """把文本 -> 向量 以 md5(text) 为 key 落盘缓存（.npy 文件）。"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()

    def lookup(self, text: str) -> Optional[np.ndarray]:
        """返回缓存的向量；未命中返回 None。"""
        path = self.cache_dir / f"{self._key(text)}.npy"
        if not path.exists():
            return None
        try:
            with self._lock:
                return np.load(path)
        except Exception as e:  # 缓存损坏则重建
            logger.warning("嵌入缓存读取失败，将重新计算: %s", e)
            return None

    def store(self, text: str, vector: np.ndarray) -> None:
        path = self.cache_dir / f"{self._key(text)}.npy"
        try:
            with self._lock:
                np.save(path, vector)
        except Exception as e:
            logger.warning("嵌入缓存写入失败（不影响运行）: %s", e)

    def batch_lookup(self, texts: Iterable[str]):
        """对批量文本逐条命中缓存，返回 (缺失列表, 命中向量列表)。"""
        missing: list[str] = []
        hits: list[np.ndarray] = []
        for t in texts:
            v = self.lookup(t)
            if v is None:
                missing.append(t)
            else:
                hits.append(v)
        return missing, hits


class TTLCache(Generic[V]):
    """带 TTL 的 LRU 缓存，线程安全。"""

    def __init__(self, max_size: int = 128, ttl_seconds: float = 3600.0):
        self._store: "OrderedDict[str, tuple[float, V]]" = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[V]:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            ts, value = item
            if time.monotonic() - ts > self._ttl:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return value

    def put(self, key: str, value: V) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
