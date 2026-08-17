"""一键启动脚本。

用法：
    python run.py                 # 默认配置
    python run.py --port 9000     # 指定端口

等价于：
    uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8001
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
    parser.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    args = parser.parse_args()

    # 浏览器可访问地址：0.0.0.0 仅用于监听，浏览器需用 127.0.0.1
    display_host = "127.0.0.1" if args.host in ("0.0.0.0", "::", "") else args.host
    url = f"http://{display_host}:{args.port}"

    print("=" * 60)
    print("📘 企业私有知识库 RAG 智能问答系统")
    print("=" * 60)
    print(f"🌐 访问地址: {url}")
    print(f"📖 API 文档: {url}/api/docs")
    print("=" * 60)

    if not args.no_browser:
        import threading
        import webbrowser

        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

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
