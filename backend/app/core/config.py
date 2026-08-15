"""全局配置。

使用 pydantic-settings 从环境变量 / .env 文件读取配置。
环境变量名与字段名不区分大小写（如 LLM_API_KEY 对应 llm_api_key）。

加载优先级：
    已导出的环境变量 > backend/.env > 项目根 .env > 内置默认值
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# 国内网络环境默认走 HuggingFace 镜像，避免模型下载失败（可在 .env 覆盖）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from pydantic_settings import BaseSettings, SettingsConfigDict  # noqa: E402

# -------------------- 路径常量 --------------------
# backend/app/core/config.py -> parents[0]=core [1]=app [2]=backend [3]=项目根
BACKEND_DIR: Path = Path(__file__).resolve().parents[2]
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

DATA_DIR: Path = PROJECT_ROOT / "data"
KNOWLEDGE_DOCS_DIR: Path = DATA_DIR / "knowledge_docs"
VECTOR_STORE_DIR: Path = DATA_DIR / "vector_store"
CHAT_MEMORY_DIR: Path = DATA_DIR / "chat_memory"
EMBEDDING_CACHE_DIR: Path = DATA_DIR / "embedding_cache"

# 前端构建产物目录（FastAPI 静态托管）
FRONTEND_DIST_DIR: Path = PROJECT_ROOT / "frontend" / "dist"


class Settings(BaseSettings):
    """应用配置，全部可通过环境变量或 .env 覆盖。"""

    model_config = SettingsConfigDict(
        env_file=(
            BACKEND_DIR / ".env",
            PROJECT_ROOT / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- LLM（OpenAI 兼容接口） ----------
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen-turbo"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_timeout: float = 120.0  # 单次生成超时（秒）

    # ---------- 嵌入模型 ----------
    embedding_model: str = "BAAI/bge-small-zh"
    embedding_device: str = "cpu"  # cpu / cuda
    embedding_batch_size: int = 32

    # ---------- 检索 ----------
    dense_top_k: int = 8          # 稠密检索召回
    sparse_top_k: int = 8         # 稀疏检索召回
    final_top_k: int = 5          # 最终送入 LLM 的块数
    enable_rerank: bool = False   # 是否启用交叉编码器重排
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_top_n: int = 4
    rrf_k: int = 60               # 倒数排名融合常数
    similarity_min_score: float = 0.0  # 融合后最低分（低于则视为无命中）

    # ---------- 分块 ----------
    chunk_size: int = 512
    chunk_overlap: int = 64

    # ---------- 会话记忆 ----------
    max_history_turns: int = 6

    # ---------- 缓存 ----------
    response_cache_ttl: int = 3600  # 命中相同问题的响应缓存秒数
    response_cache_size: int = 128

    # ---------- 服务 ----------
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # ---------- 派生属性 ----------
    @property
    def llm_configured(self) -> bool:
        """LLM 是否已配置有效的 API Key（用于前端状态展示与友好报错）。"""
        key = (self.llm_api_key or "").strip()
        return bool(key) and key not in {"your-api-key-here", "sk-123465789"}

    @property
    def is_dashscope(self) -> bool:
        return "dashscope" in self.llm_base_url.lower()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局唯一的配置实例（带缓存，避免重复读文件）。"""
    return Settings()


# 便捷引用
settings = get_settings()


def ensure_data_directories() -> None:
    """确保所有运行期目录存在。"""
    for d in (KNOWLEDGE_DOCS_DIR, VECTOR_STORE_DIR, CHAT_MEMORY_DIR, EMBEDDING_CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
