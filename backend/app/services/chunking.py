"""文档分块：中文/句读边界感知的递归分块。

设计要点（RAG 召回质量的关键之一）：
1. 优先在段落（空行）边界切分，避免破坏语义完整性。
2. 超长段落再按句号/问号/叹号/分号等句读符切分。
3. 相邻块带 overlap，避免句意被切碎导致召回丢失。
4. 过短/空块直接丢弃，避免污染索引。
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Iterable

from app.models.domain import Chunk

logger = logging.getLogger(__name__)

# 句读分隔符：优先在句子完整边界切分
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;\n])")
# 中文序号小节，如 "一、" "1." "（1）"
_SECTION_RE = re.compile(r"^\s*(?:[一二三四五六七八九十百]+|[（(]?[0-9]+[）).、])\s*", re.MULTILINE)
_WS_RE = re.compile(r"[ \t]+")

MIN_CHUNK_LEN = 10


def _normalize(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    """按句读符切分，返回保留分隔符的句子列表。"""
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _hard_split(text: str, chunk_size: int) -> list[str]:
    """极端超长片段按字符硬切（兜底，保证不丢内容）。"""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def split_text(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> list[str]:
    """把一段文本切成若干块。纯逻辑函数，便于单测。"""
    text = _normalize(text)
    if not text:
        return []

    chunks: list[str] = []
    current: str = ""

    for sent in _split_sentences(text):
        if len(sent) > chunk_size:
            # 该句本身超长：先冲刷当前块，再硬切
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_hard_split(sent, chunk_size))
            continue

        if not current or len(current) + len(sent) + 1 <= chunk_size:
            current = f"{current}\n{sent}" if current else sent
        else:
            chunks.append(current)
            tail = current[-(chunk_overlap):] if chunk_overlap > 0 else ""
            current = f"{tail}\n{sent}" if tail else sent

    if current:
        chunks.append(current)

    # 过滤过短块
    return [c for c in chunks if len(c) >= MIN_CHUNK_LEN]


def _category_of(filename: str) -> str:
    """从文件名推导分类：如 '人事_01.txt' -> '人事'。"""
    stem = filename.rsplit(".", 1)[0]
    parts = stem.split("_")
    return parts[0] if parts else "未分类"


def chunk_document(
    filename: str,
    content: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """把一份文档切成分块，并携带完整元数据。"""
    category = _category_of(filename)
    texts = split_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for i, t in enumerate(texts):
        chunks.append(
            Chunk(
                id=f"{filename}::{i}",
                content=t,
                source=filename,
                category=category,
                metadata={
                    "source": filename,
                    "file_name": filename,
                    "category": category,
                    "chunk_index": i,
                    "title": _guess_title(content),
                },
            )
        )
    logger.debug("文档 %s 切成 %d 块", filename, len(chunks))
    return chunks


def chunk_documents(
    docs: Iterable[tuple[str, str]],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    """批量切分多份文档。docs: (文件名, 内容) 迭代器。"""
    all_chunks: list[Chunk] = []
    for filename, content in docs:
        all_chunks.extend(chunk_document(filename, content, chunk_size, chunk_overlap))
    logger.info("✅ 分块完成，共 %d 块", len(all_chunks))
    return all_chunks


def _guess_title(content: str) -> str:
    """启发式提取文档标题：首个非空短行。"""
    for line in (content or "").splitlines()[:5]:
        line = line.strip()
        if 2 <= len(line) <= 40:
            return line
    return ""


def make_chunk_id() -> str:
    return uuid.uuid4().hex[:12]
