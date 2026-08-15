"""一键初始化知识库：确保文档存在 → 构建向量索引。

用法：
    python scripts/init_knowledge.py                 # 直接构建（依赖已有文档）
    python scripts/init_knowledge.py --generate      # 先生成 20 篇示例文档再构建

本脚本会在启动服务前把索引建好，之后 `python run.py` 启动即可直接问答。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import KNOWLEDGE_DOCS_DIR, get_settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.services.knowledge import KnowledgeBase  # noqa: E402


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="初始化知识库索引")
    parser.add_argument(
        "--generate", "-g", action="store_true",
        help="先生成示例文档（默认文档已存在时跳过）",
    )
    parser.add_argument("--count", "-n", type=int, default=20, help="--generate 时生成的文档数")
    args = parser.parse_args()

    if args.generate:
        from scripts.generate_sample_docs import generate

        print("📝 正在生成示例文档...")
        generate(args.count)
        print(f"📁 文档目录: {KNOWLEDGE_DOCS_DIR}")

    kb = KnowledgeBase(get_settings())
    if not any(KNOWLEDGE_DOCS_DIR.iterdir()):
        print("❌ 知识库目录为空。请先运行: python scripts/init_knowledge.py --generate")
        sys.exit(1)

    print("🚀 开始构建向量索引（首次运行需下载嵌入模型，可能耗时较长）...")
    t0 = time.monotonic()
    result = kb.rebuild()
    elapsed = int((time.monotonic() - t0) * 1000)

    print("=" * 56)
    print("✅ 知识库初始化完成！")
    print(f"   文档数 : {result.doc_count}")
    print(f"   分块数 : {result.chunk_count}")
    print(f"   耗时   : {elapsed}ms（索引构建）/ 缓存命中 {result.cached_chunks} 块")
    print(f"   索引   : {kb.store_dir}")
    print("=" * 56)
    print("👉 现在可以启动服务:  python run.py")


if __name__ == "__main__":
    main()
