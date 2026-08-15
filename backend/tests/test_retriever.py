"""混合检索（稠密 + 稀疏 + RRF）单元测试。"""
import pytest

from app.models.domain import Chunk
from app.services.bm25 import BM25Index
from app.services.retriever import HybridRetriever
from app.services.vector_store import VectorStore


def _make_retriever(fake_embedder, corpus: list[str]):
    chunks = [
        Chunk(id=f"c{i}", content=t, source=f"doc{i}.txt", category="测试")
        for i, t in enumerate(corpus)
    ]
    vectors = fake_embedder.embed_documents([c.content for c in chunks])
    store = VectorStore(vectors.shape[1])
    store.add(vectors, chunks)
    bm25 = BM25Index.from_texts([c.content for c in chunks])
    return HybridRetriever(store, bm25, fake_embedder), chunks


def test_hybrid_retrieval_picks_relevant_first(fake_embedder):
    corpus = [
        "员工请假须提前提交请假申请单并经过直属领导审批，连续请假超过5天需总经理审批。",
        "公司车辆主要用于商务接待和公务出行，车辆实行定点维修。",
        "费用报销需要提供合规发票，差旅住宿一线城市每晚500元。",
    ]
    retriever, _ = _make_retriever(fake_embedder, corpus)
    results = retriever.retrieve("请假的流程是什么", dense_top_k=3, sparse_top_k=3, final_top_k=2)
    assert results, "应有检索结果"
    assert results[0].chunk.source == "doc0.txt", "最相关的文档应排第一"


def test_sparse_helps_exact_term(fake_embedder):
    """BM25 对精确术语有加成：即使向量相似度一般，融合后仍能排前。"""
    corpus = [
        "年度财务预算已经编制完成。",
        "报销单号：BX-2026-0042 的发票需要重新开具。",
        "关于员工通勤补助的说明。",
    ]
    retriever, _ = _make_retriever(fake_embedder, corpus)
    # 精确编号查询
    results = retriever.retrieve("BX-2026-0042", dense_top_k=3, sparse_top_k=3, final_top_k=1)
    assert results and results[0].chunk.source == "doc1.txt"


def test_empty_index(fake_embedder):
    store = VectorStore(8)
    bm25 = BM25Index([])
    retriever = HybridRetriever(store, bm25, fake_embedder)
    assert retriever.retrieve("任何问题", final_top_k=3) == []


def test_score_normalized_between_zero_one(fake_embedder):
    corpus = [
        "员工请假须提前提交请假申请单。",
        "公司车辆用于公务出行。",
        "报销需要合规发票。",
    ]
    retriever, _ = _make_retriever(fake_embedder, corpus)
    results = retriever.retrieve("请假", final_top_k=3)
    assert results
    for r in results:
        assert 0.0 <= r.score <= 1.0
        assert r.rank >= 1
