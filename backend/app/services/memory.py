"""会话记忆：按会话 ID 持久化对话历史（JSON 文件）。

设计：
- 一个会话一个 JSON 文件（data/chat_memory/{session_id}.json）
- 记录结构：{user, bot, sources, timestamp}
- 注入 LLM 时截取最近 N 轮，控制 token 预算。
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.core.config import CHAT_MEMORY_DIR, Settings
from app.utils.text import first_line_as_title

logger = logging.getLogger(__name__)

_SAFE_ID_RE = re.compile(r"[^0-9a-zA-Z_-]")


def _safe_filename(session_id: str) -> str:
    return _SAFE_ID_RE.sub("_", session_id)


class MemoryStore:
    def __init__(self, settings: Settings, directory: Optional[Path] = None):
        self._dir = directory or Path(CHAT_MEMORY_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)
        self.max_turns = settings.max_history_turns

    # ---------- 内部读写 ----------
    def _path(self, session_id: str) -> Path:
        return self._dir / f"{_safe_filename(session_id)}.json"

    def _load(self, session_id: str) -> list[dict]:
        path = self._path(session_id)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("会话历史读取失败: %s", e)
            return []

    def _save(self, session_id: str, history: list[dict]) -> None:
        try:
            with open(self._path(session_id), "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("会话历史保存失败: %s", e)

    # ---------- 对外 API ----------
    def add_turn(
        self,
        session_id: str,
        user: str,
        bot: str,
        sources: Optional[list[dict]] = None,
    ) -> None:
        history = self._load(session_id)
        history.append({
            "user": user,
            "bot": bot,
            "sources": sources or [],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
        # 只保留最近 max_turns*2 条，控制文件体积
        if len(history) > self.max_turns * 2:
            history = history[-self.max_turns * 2 :]
        self._save(session_id, history)

    def get_history(self, session_id: str) -> list[dict]:
        return self._load(session_id)

    def get_summary(self, session_id: str) -> dict[str, Any]:
        history = self._load(session_id)
        return {
            "session_id": session_id,
            "turn_count": len(history),
            "first_timestamp": history[0]["timestamp"] if history else None,
            "last_timestamp": history[-1]["timestamp"] if history else None,
            "title": first_line_as_title(history[0]["user"]) if history else "新会话",
        }

    def list_sessions(self) -> list[dict[str, Any]]:
        """列出所有会话摘要，按最后活跃时间倒序。"""
        summaries = []
        for f in self._dir.glob("*.json"):
            sid = f.stem
            summaries.append(self.get_summary(sid))
        summaries.sort(key=lambda s: s.get("last_timestamp") or "", reverse=True)
        return summaries

    def delete_session(self, session_id: str) -> bool:
        path = self._path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear_all(self) -> int:
        n = 0
        for f in self._dir.glob("*.json"):
            f.unlink()
            n += 1
        return n

    # ---------- Prompt 组装 ----------
    def build_history_prompt(self, session_id: str, max_turns: int | None = None) -> str:
        """把最近几轮对话格式化为字符串，注入 system prompt。"""
        limit = max_turns or self.max_turns
        history = self._load(session_id)[-limit * 2 :]  # 每轮 2 条
        if not history:
            return ""
        lines = []
        for record in history:
            lines.append(f"用户: {record['user']}")
            lines.append(f"助手: {record['bot']}")
        return "\n".join(lines)

    def new_session_id(self) -> str:
        return f"sess_{uuid.uuid4().hex[:12]}"
