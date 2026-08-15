"""BM25 稀疏检索。

自实现经典 BM25（k1=1.5, b=0.75），配合 jieba 中文分词。
与稠密检索互补：擅长精确词/术语/编号/人名匹配，能显著提升 RAG 召回。
"""
from __future__ import annotations

import logging
import math
import re
from typing import Optional

import jieba

logger = logging.getLogger(__name__)

# 缓存 jieba 词典加载
_jieba_initialized = False


def _ensure_jieba():
    global _jieba_initialized
    if not _jieba_initialized:
        jieba.setLogLevel(logging.WARNING)
        _jieba_initialized = True


_CJK_PAT = re.compile(r"[一-鿿]")


def tokenize(text: str) -> list[str]:
    """中文分词：对含中文文本用 jieba；纯英文按空白/标点切分。"""
    _ensure_jieba()
    text = (text or "").strip()
    if not text:
        return []
    if _CJK_PAT.search(text):
        return [t for t in jieba.lcut(text) if len(t) > 1 or not _CJK_PAT.match(t) or _is_meaningful_ascii(t)]
    return [t.lower() for t in re.findall(r"[a-zA-Z0-9_]+", text)]


def _is_meaningful_ascii(tok: str) -> bool:
    """单个 ASCII 字符（如型号 'A'、'C'）可能重要，保留之。"""
    return bool(re.fullmatch(r"[A-Za-z0-9]", tok))


class BM25Index:
    """BM25 检索索引，与外部 chunk 列表一一对应。"""

    def __init__(self, corpus: Optional[list[list[str]]] = None):
        self.corpus = corpus or []
        self.doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_freq: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._doc_vectors: list[dict[str, int]] = []
        self.k1 = 1.5
        self.b = 0.75
        if self.corpus:
            self._build()

    @classmethod
    def from_texts(cls, texts: list[str]) -> "BM25Index":
        """从原始文本列表构建索引（内部完成分词）。"""
        corpus = [tokenize(t) for t in texts]
        return cls(corpus)

    def _build(self) -> None:
        self.doc_count = len(self.corpus)
        total_len = 0
        self._doc_vectors = []
        self.doc_freq = {}
        for tokens in self.corpus:
            total_len += len(tokens)
            vec: dict[str, int] = {}
            for tok in set(tokens):
                vec[tok] = tokens.count(tok)
                self.doc_freq[tok] = self.doc_freq.get(tok, 0) + 1
            self._doc_vectors.append(vec)
        self.avg_doc_len = total_len / self.doc_count if self.doc_count else 0.0
        self._idf = {
            term: math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
            for term, df in self.doc_freq.items()
        }
        logger.info("BM25 索引构建完成：%d 篇文档，词表 %d 词", self.doc_count, len(self._idf))

    # ---------- 查询 ----------
    def search(self, query: str, top_k: int = 8) -> list[tuple[int, float]]:
        """返回 [(doc_idx, score)] 按得分降序。"""
        if self.doc_count == 0:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = [self._score_doc(query_tokens, idx) for idx in range(self.doc_count)]
        ranked = sorted(range(self.doc_count), key=lambda i: scores[i], reverse=True)
        ranked = [i for i in ranked if scores[i] > 0][:top_k]
        return [(i, scores[i]) for i in ranked]

    def _score_doc(self, query_tokens: list[str], doc_idx: int) -> float:
        vec = self._doc_vectors[doc_idx]
        doc_len = len(self.corpus[doc_idx])
        if doc_len == 0:
            return 0.0
        score = 0.0
        dl = doc_len
        denom = self.k1 * (1 - self.b + self.b * dl / self.avg_doc_len) if self.avg_doc_len else 1.0
        for term in set(query_tokens):
            tf = vec.get(term, 0)
            if tf == 0:
                continue
            idf = self._idf.get(term, 0.0)
            score += idf * (tf * (self.k1 + 1)) / (tf + denom)
        return score

    def __len__(self) -> int:
        return self.doc_count
