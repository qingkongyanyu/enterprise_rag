"""文本处理工具：规范化、token 估算、裁剪。"""
from __future__ import annotations

import re

_CJK_RE = re.compile(r"[一-鿿]")
_WS_RE = re.compile(r"[ \t]+")


def normalize_text(text: str) -> str:
    """清洗文本：去除首尾空白、压缩连续空格、规整空行。"""
    text = (text or "").strip()
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文 1 字≈1 token，ASCII ≈1/4 token）。

    用于上下文预算裁剪，无需引入 tokenizer 依赖。
    """
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))
    ascii_count = len(text) - cjk
    return cjk + ascii_count // 4 + 1


def truncate_by_tokens(text: str, max_tokens: int) -> str:
    """按估算 token 预算截断文本，尽量保留开头（标题/要点）。"""
    if estimate_tokens(text) <= max_tokens:
        return text
    # 逐字符累加至预算，保留整段可读性
    budget = 0
    for i, ch in enumerate(text):
        budget += 1 if _CJK_RE.match(ch) else (1 if ch.isspace() else 0.25)
        if budget >= max_tokens:
            return text[: i + 1] + "…"
    return text


def first_line_as_title(text: str, max_len: int = 24) -> str:
    """从文档/对话中提取简短标题。"""
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    line = line.strip(" #\t")
    if not line:
        return "未命名"
    return line if len(line) <= max_len else line[: max_len] + "…"
