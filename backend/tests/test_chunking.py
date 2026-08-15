"""分块逻辑单元测试。"""
from app.services.chunking import chunk_document, split_text


def test_empty_text():
    assert split_text("") == []
    assert split_text("   \n\n  ") == []


def test_short_text():
    # 长度达标的短文本保留
    text = "这是一个用于测试的短文本内容。"
    assert split_text(text) == [text]


def test_tiny_text_dropped():
    # 过短文本（低于 MIN_CHUNK_LEN=10）无检索价值，应被过滤
    assert split_text("短文本") == []


def test_no_chunk_exceeds_chunk_size():
    text = "一、请假制度。" * 200
    chunks = split_text(text, chunk_size=100, chunk_overlap=10)
    assert chunks
    assert all(len(c) <= 100 for c in chunks), "存在超过 chunk_size 的块"


def test_long_text_creates_multiple_chunks():
    text = "今天天气很好。我们一起吃火锅。然后去公园散步。最后回家休息。" * 20
    chunks = split_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2
    assert "".join(chunks).count("今天天气很好") >= 20, "内容不应丢失"


def test_overlap_between_adjacent_chunks():
    text = "第一句。第二句。第三句。第四句。第五句。第六句。" * 10
    chunks = split_text(text, chunk_size=50, chunk_overlap=15)
    if len(chunks) >= 2:
        # 相邻块之间应存在重叠尾巴
        assert chunks[1].startswith(chunks[0][-15:])


def test_metadata_attached():
    docs = chunk_document("人事_01.txt", "一、请假制度\n员工请假须提前申请。", 120, 20)
    assert docs
    first = docs[0]
    assert first.source == "人事_01.txt"
    assert first.category == "人事"
    assert first.id.startswith("人事_01.txt")
    assert first.metadata["file_name"] == "人事_01.txt"
