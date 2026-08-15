"""BM25 稀疏检索单元测试。"""
from app.services.bm25 import BM25Index, tokenize


def test_tokenize_chinese():
    toks = tokenize("请假流程是什么")
    assert toks, "中文应能被 jieba 分词"


def test_relevant_doc_ranked_first():
    idx = BM25Index.from_texts([
        "员工请假须提前提交请假申请单，由直属领导审批。",
        "公司年会定于下月举办，请各部门准备节目。",
        "报销发票须合规，财务部负责审核。",
    ])
    hits = idx.search("请假申请单审批", top_k=1)
    assert hits and hits[0][0] == 0, "最相关的文档应排第一"


def test_empty_query():
    idx = BM25Index.from_texts(["测试文档"])
    assert idx.search("", top_k=3) == []
    assert idx.search("   ", top_k=3) == []


def test_corpus_size_and_query_ranking():
    idx = BM25Index.from_texts([
        "员工请假须提交请假申请单",
        "员工请假须经直属领导审批",
        "报销发票须合规",
    ])
    assert len(idx) == 3
    # 与「请假」相关的文档都应被召回且得分 > 0
    hits = idx.search("请假", top_k=2)
    assert len(hits) == 2
    assert all(score > 0 for _, score in hits)
