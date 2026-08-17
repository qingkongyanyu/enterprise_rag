"""API 端到端测试（注入替身，无需网络）。"""
import json

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import FakeLLM


def _client(services):
    app = create_app(services=services)
    return TestClient(app)


class EmptyRetriever:
    """强制检索返回空（模拟知识库无相关内容）。"""

    def retrieve(self, *args, **kwargs):
        return []


def test_health(services):
    with _client(services) as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


def test_chat_before_index_returns_503(services):
    with _client(services) as c:
        r = c.post("/api/v1/chat", json={"question": "你好"})
        assert r.status_code == 503
        assert r.json()["code"] == 503


def test_empty_question_returns_422(services):
    with _client(services) as c:
        r = c.post("/api/v1/chat", json={"question": "   "})
        assert r.status_code == 422


def test_rebuild_then_chat_flow(services, sample_docs):
    with _client(services) as c:
        # 1. 构建索引
        r = c.post("/api/v1/knowledge/rebuild")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["doc_count"] == 3
        assert data["chunk_count"] >= 3

        # 2. 概览
        r = c.get("/api/v1/knowledge/documents")
        ov = r.json()["data"]
        assert ov["ready"] is True
        assert ov["total_docs"] == 3

        # 3. 问答
        r = c.post("/api/v1/chat", json={"question": "请假需要什么流程"})
        assert r.status_code == 200
        chat = r.json()["data"]
        assert chat["answer"] == "这是模拟回答。"
        assert chat["session_id"].startswith("sess_")
        assert chat["grounded"] is True
        assert chat["sources"], "应返回来源引用"
        assert chat["sources"][0]["source"] == "人事_01.txt"

        # 4. 会话历史持久化
        sid = chat["session_id"]
        r = c.get(f"/api/v1/sessions/{sid}/history")
        assert r.status_code == 200
        assert len(r.json()["data"]["history"]) == 1

        # 5. 会话列表
        r = c.get("/api/v1/sessions")
        assert len(r.json()["data"]) == 1


def test_stream_chat(services, sample_docs):
    with _client(services) as c:
        c.post("/api/v1/knowledge/rebuild")
        r = c.post("/api/v1/chat/stream", json={"question": "报销标准是什么"})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

        types = []
        text_parts = []
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: "):])
            types.append(event["type"])
            if event["type"] == "delta":
                text_parts.append(event["text"])
        assert "meta" in types and "delta" in types and "sources" in types and "done" in types
        assert "".join(text_parts) == "这是模拟回答。"


def test_no_hit_short_circuits_without_llm(services, sample_docs, monkeypatch):
    """知识库无命中时直接返回兜底语，且不调用 LLM。"""
    with _client(services) as c:
        c.post("/api/v1/knowledge/rebuild")

    # 强制检索返回空（模拟"知识库确实没有相关内容"）
    monkeypatch.setattr(services.knowledge, "_retriever", EmptyRetriever())
    # 若 LLM 被误调用，answer 会是这个哨兵值
    services.pipeline.llm = FakeLLM(answer="不应被调用")

    with _client(services) as c:
        r = c.post("/api/v1/chat", json={"question": "完全无关的问题"})
        assert r.status_code == 200
        chat = r.json()["data"]
        assert chat["grounded"] is False
        assert chat["answer"] != "不应被调用", "无命中时不应调用 LLM"
        assert chat["answer"].startswith("抱歉")
        assert chat["sources"] == []


def test_upload_and_delete_document(services, tmp_dirs):
    with _client(services) as c:
        # 上传
        files = {"file": ("行政_01.txt", "会议室预约：大会议室可容纳30-50人。", "text/plain")}
        r = c.post("/api/v1/knowledge/upload", files=files)
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "行政_01.txt"

        r = c.get("/api/v1/knowledge/documents")
        names = [d["name"] for d in r.json()["data"]["docs"]]
        assert "行政_01.txt" in names

        # 删除
        r = c.delete("/api/v1/knowledge/documents/行政_01.txt")
        assert r.status_code == 200

        r = c.get("/api/v1/knowledge/documents")
        names = [d["name"] for d in r.json()["data"]["docs"]]
        assert "行政_01.txt" not in names


def test_delete_session(services, sample_docs):
    with _client(services) as c:
        c.post("/api/v1/knowledge/rebuild")
        sid = c.post("/api/v1/chat", json={"question": "请假"}).json()["data"]["session_id"]
        r = c.delete(f"/api/v1/sessions/{sid}")
        assert r.status_code == 200
        assert r.json()["data"]["deleted"] is True


def test_cache_hit_returns_current_session_id(services, sample_docs):
    """回归：无历史时同问题命中缓存，返回的 session_id 必须是当前会话而非缓存旧值。"""
    with _client(services) as c:
        c.post("/api/v1/knowledge/rebuild")
        first = c.post("/api/v1/chat", json={"question": "报销标准"}).json()["data"]
        second = c.post("/api/v1/chat", json={"question": "报销标准"}).json()["data"]
        assert second["session_id"] != first["session_id"]


def test_no_hit_reply_not_cached(services, sample_docs, monkeypatch):
    """回归：无命中兜底语不写入缓存，后续（模拟索引就绪）同问题应重新检索。"""
    with _client(services) as c:
        c.post("/api/v1/knowledge/rebuild")

    real_retriever = services.knowledge._retriever
    monkeypatch.setattr(services.knowledge, "_retriever", EmptyRetriever())
    with _client(services) as c:
        r = c.post("/api/v1/chat", json={"question": "绝无此内容"})
        assert r.json()["data"]["grounded"] is False

    # 恢复真实检索器后，同问题必须重新检索并 grounded=True（而非命中旧缓存）
    monkeypatch.setattr(services.knowledge, "_retriever", real_retriever)
    with _client(services) as c:
        r = c.post("/api/v1/chat", json={"question": "绝无此内容"})
        assert r.json()["data"]["grounded"] is True


def test_upload_path_traversal_rejected(services):
    """回归：上传文件名含路径分隔符必须被拒绝（防路径穿越）。"""
    with _client(services) as c:
        for bad in ("../evil.txt", "..\\evil.txt", "a/b.txt"):
            files = {"file": (bad, "内容", "text/plain")}
            r = c.post("/api/v1/knowledge/upload", files=files)
            assert r.status_code == 422, f"{bad} 应返回 422"


def test_memory_keeps_only_max_turns(services, sample_docs):
    """回归：历史只保留 max_turns 轮，注入 prompt 不超量。"""
    with _client(services) as c:
        c.post("/api/v1/knowledge/rebuild")
        # 同一会话连问 10 轮
        sid = c.post("/api/v1/chat", json={"question": "第0个问题"}).json()["data"]["session_id"]
        for i in range(1, 10):
            c.post("/api/v1/chat", json={"question": f"第{i}个问题", "session_id": sid})
        sessions = c.get("/api/v1/sessions").json()["data"]
        assert len(sessions) == 1
        history = c.get(f"/api/v1/sessions/{sid}/history").json()["data"]["history"]
        # max_history_turns=4 → 最多 4 条记录
        assert len(history) <= 4
        prompt = services.memory.build_history_prompt(sid)
        assert prompt.count("用户: ") <= 4
