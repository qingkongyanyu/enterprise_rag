"""一键启动脚本。

用法：
    python run.py                 # 默认配置
    python run.py --port 9000     # 指定端口

等价于：
    uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import argparse

import uvicorn

from app.core.config import get_settings
from app.core.logging import setup_logging


def main() -> None:
    setup_logging()
    settings = get_settings()

    parser = argparse.ArgumentParser(description="启动企业 RAG 问答服务")
    parser.add_argument("--host", default=settings.host, help="监听地址")
    parser.add_argument("--port", type=int, default=settings.port, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    args = parser.parse_args()

    print("=" * 60)
    print("📘 企业私有知识库 RAG 智能问答系统")
    print("=" * 60)
    print(f"🌐 访问地址: http://{args.host}:{args.port}")
    print(f"📖 API 文档: http://{args.host}:{args.port}/api/docs")
    print("=" * 60)

    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
