"""交叉编码器重排器（可选）。

用 bge-reranker 对"查询×候选块"做精细相关度打分，可显著提升 Top-N 精度。
CPU 环境下较慢，故默认关闭（由配置 ENABLE_RERANK 控制）。加载失败时优雅降级为不重排。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.models.domain import Chunk

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model_name: str, device: str = "cpu", top_n: int = 4):
        self.model_name = model_name
        self.device = device
        self.top_n = top_n
        self._model = None
        self._failed = False

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        if self._failed:
            return None
        try:
            from sentence_transformers import CrossEncoder

            logger.info("🔄 正在加载重排模型: %s", self.model_name)
            self._model = CrossEncoder(self.model_name, device=self.device)
            logger.info("✅ 重排模型加载完成")
        except Exception as e:
            self._failed = True
            logger.warning("⚠️ 重排模型加载失败，将跳过重排（不影响主流程）: %s", e)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[tuple[Chunk, float]],
    ) -> list[tuple[Chunk, float]]:
        """返回按交叉编码器得分降序的 Top-N 候选。"""
        model = self._ensure_model()
        if model is None or not candidates:
            return candidates

        try:
            pairs = [(query, c.content[:1500]) for c, _ in candidates]
            scores = model.predict(pairs)
            scored = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)
            return [(c, float(s)) for (c, _), s in scored[: self.top_n]]
        except Exception as e:
            logger.warning("重排执行失败，跳过: %s", e)
            return candidates
