"""统一日志配置。

- 控制台输出彩色、带时间与模块名
- 避免 Windows 控制台 GBK 编码导致 emoji 报错：强制 UTF-8
"""
from __future__ import annotations

import logging
import sys

from app.core.config import settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str | None = None) -> None:
    """初始化根日志器。幂等：重复调用只重置 handler。"""
    # Windows 控制台默认 GBK，emoji / 中文可能触发 UnicodeEncodeError
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    level_name = (level or settings.log_level or "INFO").upper()
    root = logging.getLogger()
    root.setLevel(getattr(logging, level_name, logging.INFO))

    # 清空已有 handlers，避免重复打印
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(handler)

    # 抑制过吵的第三方库
    for noisy in ("httpx", "httpcore", "urllib3", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取带统一格式的日志器。"""
    return logging.getLogger(name)
