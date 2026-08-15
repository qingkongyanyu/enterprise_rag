"""文档加载：读取、枚举、新增、删除知识库文档文件。

支持 txt / md；编码 utf-8 优先，失败回退 gbk。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from app.core.config import KNOWLEDGE_DOCS_DIR
from app.models.schemas import DocInfo

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = {".txt", ".md", ".markdown"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 单文件 5MB


def _read_with_fallback(path: Path) -> str:
    """优先 utf-8，失败回退 gbk。"""
    for enc in ("utf-8", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            logger.error("读取文件失败 %s: %s", path, e)
            raise
    # 全部失败：用 errors="replace" 兜底
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTS


def list_docs(directory: Path = KNOWLEDGE_DOCS_DIR) -> list[DocInfo]:
    """枚举目录下所有文档及其基础信息，按名称排序。"""
    if not directory.exists():
        return []
    docs: list[DocInfo] = []
    for f in sorted(directory.iterdir()):
        if not f.is_file() or f.suffix.lower() not in SUPPORTED_EXTS:
            continue
        stat = f.stat()
        docs.append(
            DocInfo(
                name=f.name,
                category=_category_of(f.name),
                size=stat.st_size,
                updated_at=_ts(stat.st_mtime),
            )
        )
    return docs


def read_doc(path: Path) -> str:
    return _read_with_fallback(path)


def read_all_docs(directory: Path = KNOWLEDGE_DOCS_DIR) -> list[tuple[str, str]]:
    """返回 [(文件名, 内容)]。"""
    result: list[tuple[str, str]] = []
    for f in sorted(directory.iterdir()):
        if not f.is_file() or f.suffix.lower() not in SUPPORTED_EXTS:
            continue
        try:
            result.append((f.name, _read_with_fallback(f)))
        except Exception as e:
            logger.error("跳过文档 %s: %s", f.name, e)
    return result


def save_doc(directory: Path, filename: str, content: bytes | str) -> Path:
    """保存上传文档，返回路径。同名文件将被覆盖。"""
    directory.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode("utf-8")
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("文件过大，单个文档不得超过 5MB")
    path = directory / filename
    with open(path, "wb") as f:
        f.write(content)
    return path


def delete_doc(directory: Path, filename: str) -> bool:
    """删除文档；防止路径穿越。"""
    # 仅允许文件名（不含路径分隔符）
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise ValueError("非法文件名")
    path = (directory / filename).resolve()
    if directory.resolve() not in path.parents:
        raise ValueError("非法路径")
    if path.exists() and path.is_file():
        path.unlink()
        return True
    return False


def _category_of(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_")
    return parts[0] if parts else "未分类"


def _ts(sec: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(sec).isoformat(timespec="seconds")
